"""Optional isolated-save playground for an owner-controlled Azeroth Survivors copy.

Only copies/backs up save data. Never edits or runs a game automatically.
`launch --yes` is an explicit user action, Windows only, using the game's
own WOW_ROGUE_SAVE environment variable to redirect its *primary* save.
Additional game settings/cloud/network behavior are not sandboxed.
"""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import uuid

CLIENT_SHAS = {
    "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8": "original-windows-0.137.0",
    "eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c": "original-windows-0.136.0-backup",
    "2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a": "original-windows-older-snapshot",
}
MAX_SAVE_BYTES = 32 * 1024 * 1024
MAX_GAME_BYTES = 1024 * 1024 * 1024
MANIFEST = "solo-lab.json"
SAVE = "characters.txt"
BASELINE = "baseline.characters.txt"


class LabError(ValueError):
    """Refused to touch files because an integrity check failed."""


def file_hash(path):
    hasher = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            hasher.update(block)
    return hasher.hexdigest()


def safe_file(path, max_bytes=MAX_SAVE_BYTES):
    p = Path(path)
    if p.is_symlink() or not p.is_file():
        raise LabError("Expected a regular, non-symlink file")
    if not 0 < p.stat().st_size <= max_bytes:
        raise LabError("File exceeds the permitted size or is empty")
    return p.resolve(strict=True)


def safe_dir(path, must_exist=True):
    p = Path(path)
    for parent in (p, *p.parents):
        if parent.is_symlink():
            raise LabError("Symlinked directory path refused")
    if must_exist and not p.is_dir():
        raise LabError("Expected existing directory")
    if p.exists() and not p.is_dir():
        raise LabError("Directory path is not a directory")
    return p.resolve(strict=must_exist)


def game_identity(path):
    p = safe_file(path, MAX_GAME_BYTES)
    if p.name.lower() != "azerothsurvivors.exe":
        raise LabError("Choose the original AzerothSurvivors.exe")
    with p.open("rb") as stream:
        if stream.read(2) != b"MZ":
            raise LabError("Missing Windows executable signature")
    digest = file_hash(p)
    if digest not in CLIENT_SHAS:
        raise LabError("Unknown EXE SHA256; review this game update before creating or launching a sandbox")
    return {"path": str(p), "sha256": digest, "profile": CLIENT_SHAS[digest]}


def default_save_path():
    folder = os.environ.get("APPDATA")
    if not folder:
        raise LabError("No APPDATA environment variable: specify --save-source")
    return Path(folder) / "wenilla-rogue" / "characters.txt"


def inspect(game_exe, save_source):
    game = game_identity(game_exe)
    save = safe_file(save_source)
    return {"game_profile": game["profile"], "game_sha256": game["sha256"],
            "save_size_bytes": save.stat().st_size, "save_sha256": file_hash(save),
            "read_only": True, "gameplay_verified": False}


def prepare(game_exe, source, sandbox, confirmed=False):
    if not confirmed:
        raise LabError("Creating a sandbox requires explicit --yes")
    game = game_identity(game_exe)
    save = safe_file(source)
    target = Path(sandbox)
    safe_dir(target.parent)
    if target.exists() or target.is_symlink():
        raise LabError("Sandbox already exists, refusing overwrite")
    real_target = target.resolve(strict=False)
    game_root = Path(game["path"]).parent
    if real_target == game_root or game_root in real_target.parents:
        raise LabError("Sandbox cannot be inside the original game folder")
    if real_target == save or save in real_target.parents or real_target in save.parents:
        raise LabError("Sandbox cannot overlap original save location")
    # The two copies preserve a baseline even after the game changes its sandbox save.
    target.mkdir(mode=0o700)
    try:
        shutil.copyfile(save, target / SAVE)
        shutil.copyfile(save, target / BASELINE)
        digest = file_hash(save)
        if file_hash(target / SAVE) != digest or file_hash(target / BASELINE) != digest:
            raise LabError("Copied save hashes differ from original")
        record = {
            "schema_version": 1, "purpose": "solo_cheat_lab_test_save",
            "game": game, "original_save_sha256": digest,
            "baseline_sha256": digest, "original_save_size": save.stat().st_size,
            "network_isolated": False, "main_save_modified": False,
            "WARNING": "Only primary save path is redirected; game settings, multiplayer and any other storage are NOT isolated",
        }
        (target / MANIFEST).write_text(json.dumps(record, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        return {"status": "created", "sandbox": str(real_target),
                "profile": game["profile"], "save_sha256": digest,
                "main_save_modified": False, "game_started": False}
    except Exception:
        # This folder was just created by us and never existed beforehand.
        shutil.rmtree(target)
        raise


def opened(sandbox):
    target = safe_dir(sandbox)
    path = target / MANIFEST
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 16384:
        raise LabError("Missing or unsafe Solo Lab manifest")
    try:
        record = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError, UnicodeError) as exc:
        raise LabError("Corrupt Solo Lab manifest") from exc
    if not isinstance(record, dict) or record.get("schema_version") != 1:
        raise LabError("Unknown Solo Lab manifest")
    game = record.get("game")
    if not isinstance(game, dict) or game.get("sha256") not in CLIENT_SHAS:
        raise LabError("Unrecognized sandbox game identity")
    base = safe_file(target / BASELINE)
    if file_hash(base) != record.get("baseline_sha256"):
        raise LabError("Baseline backup changed; refusing destructive operation")
    if record.get("original_save_sha256") != record.get("baseline_sha256"):
        raise LabError("Baseline provenance mismatch")
    own = safe_file(target / SAVE)
    return target, record, own


def status(sandbox):
    target, record, save = opened(sandbox)
    current = file_hash(save)
    return {"sandbox": str(target), "profile": record["game"]["profile"],
            "sandbox_save_sha256": current, "baseline_sha256": record["baseline_sha256"],
            "changed_from_baseline": current != record["baseline_sha256"],
            "main_save_modified_by_tool": False}


def snapshot(sandbox):
    target, _, save = opened(sandbox)
    folder = target / "snapshots"
    if folder.is_symlink() or (folder.exists() and not folder.is_dir()):
        raise LabError("Unsafe snapshot directory")
    folder.mkdir(exist_ok=True)
    name = datetime.datetime.now(datetime.timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8] + ".txt"
    dest = folder / name
    with dest.open("xb") as output, save.open("rb") as source:
        shutil.copyfileobj(source, output)
    if file_hash(dest) != file_hash(save):
        dest.unlink()
        raise LabError("Snapshot failed checksum")
    return {"snapshot_name": name, "sha256": file_hash(dest), "original_unchanged": True}


def restore(sandbox, confirmed=False):
    if not confirmed:
        raise LabError("Sandbox restore requires --yes")
    target, record, save = opened(sandbox)
    recovery = snapshot(target)
    staging = target / ("restore-" + uuid.uuid4().hex + ".tmp")
    try:
        shutil.copyfile(target / BASELINE, staging)
        if file_hash(staging) != record["baseline_sha256"]:
            raise LabError("Restored save did not match baseline")
        staging.replace(save)
        return {"status": "restored_sandbox_only", "preserved_previous": recovery["snapshot_name"],
                "main_save_modified": False}
    finally:
        if staging.exists():
            staging.unlink()


def launch(sandbox, confirmed=False, platform=None, spawn=subprocess.Popen):
    if not confirmed:
        raise LabError("Launching the sandbox game requires --yes")
    if (platform or sys.platform) != "win32":
        raise LabError("This launch operation is available on Windows only")
    target, record, save = opened(sandbox)
    game = game_identity(record["game"]["path"])
    if game["sha256"] != record["game"]["sha256"]:
        raise LabError("EXE changed since sandbox preparation; refuse launch")
    env = dict(os.environ)
    env["WOW_ROGUE_SAVE"] = str(save)
    # Explicit user opt-in; no shell and no third-party executable involved.
    proc = spawn([game["path"]], env=env, cwd=str(Path(game["path"]).parent))
    return {"launched": True, "pid": getattr(proc, "pid", None),
            "primary_save_redirected": True, "other_game_settings_isolated": False}


def main(argv=None):
    p = argparse.ArgumentParser(description="Azeroth Survivors solo save playground (no cheats injected)")
    sp = p.add_subparsers(dest="command", required=True)
    for command in ("inspect", "prepare"):
        q = sp.add_parser(command)
        q.add_argument("--game-exe", required=True)
        q.add_argument("--save-source", help="Default is %%APPDATA%%/wenilla-rogue/characters.txt")
        if command == "prepare":
            q.add_argument("--sandbox-dir", required=True)
            q.add_argument("--yes", action="store_true")
    for command in ("status", "snapshot", "restore", "launch"):
        q = sp.add_parser(command)
        q.add_argument("--sandbox-dir", required=True)
        if command in ("restore", "launch"):
            q.add_argument("--yes", action="store_true")
    args = p.parse_args(argv)
    try:
        if args.command in ("inspect", "prepare"):
            source = args.save_source or default_save_path()
            result = (inspect(args.game_exe, source) if args.command == "inspect"
                      else prepare(args.game_exe, source, args.sandbox_dir, args.yes))
        elif args.command == "status":
            result = status(args.sandbox_dir)
        elif args.command == "snapshot":
            result = snapshot(args.sandbox_dir)
        elif args.command == "restore":
            result = restore(args.sandbox_dir, args.yes)
        else:
            result = launch(args.sandbox_dir, args.yes)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0
    except (LabError, OSError) as exc:
        print("REFUSED:", str(exc), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
