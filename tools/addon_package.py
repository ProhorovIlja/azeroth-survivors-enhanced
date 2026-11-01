"""Offline, addon-only installer for self-authored AZSEnhancedAdvisor.

Never executes the client or edits EXE, MPQ or save files. Exact owner-client
checksum is required by default; an explicit override is available.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

ADDON = "AZSEnhancedAdvisor"
OWNER_SHA = "2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a"
KNOWN_OWNER_SHAS = {OWNER_SHA, "aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8", "eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c"}
SOURCE = Path(__file__).resolve().parents[1] / "addons" / ADDON
STATE = ".azse-enhanced"
MAX_BYTES = 10 * 1024 * 1024
MAX_FILES = 50
ALLOWED = {".toc", ".lua", ".xml"}


class SafetyError(ValueError):
    pass


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def valid_root(value):
    p = Path(value)
    if p.is_symlink() or not p.is_dir():
        raise SafetyError("Game root missing or symlinked")
    root = p.resolve(strict=True)
    exe, data = root / "AzerothSurvivors.exe", root / "Data"
    if exe.is_symlink() or not exe.is_file() or data.is_symlink() or not data.is_dir():
        raise SafetyError("Original game EXE and Data directory required, no symlinks")
    for part in (root / "benilla-config", root / "benilla-config" / "AddOns", root / STATE):
        if part.is_symlink() or (part.exists() and not part.is_dir()):
            raise SafetyError("Configuration/state path is symlinked or not a directory")
    return root


def manifest(folder, *, strict=False):
    folder = Path(folder)
    if not folder.is_dir() or folder.is_symlink():
        raise SafetyError("Addon source/target must be a normal directory")
    files, total = {}, 0
    for path in sorted(folder.rglob("*")):
        if path.is_symlink() or not (path.is_dir() or path.is_file()):
            raise SafetyError("Symlinks and special files are forbidden")
        if path.is_dir():
            continue
        name = path.relative_to(folder).as_posix()
        if strict and ("/" in name or path.suffix.lower() not in ALLOWED):
            raise SafetyError("Only direct .lua, .toc, .xml source files allowed")
        total += path.stat().st_size
        if total > MAX_BYTES or len(files) >= MAX_FILES:
            raise SafetyError("Addon exceeds size/file limits")
        files[name] = sha256(path)
    if strict:
        toc = ADDON + ".toc"
        if toc not in files or not any(f.endswith(".lua") for f in files):
            raise SafetyError("Missing matching TOC or Lua source")
        text = (folder / toc).read_text(encoding="utf-8")
        if "## Interface: 11200" not in text:
            raise SafetyError("Expected WoW 1.12 addon TOC")
        for line in text.splitlines():
            line = line.strip()
            if line and not line.startswith("#") and line.replace("\\", "/") not in files:
                raise SafetyError("TOC references a missing or outside file")
    return files


def paths(root):
    addon_dir = root / "benilla-config" / "AddOns" / ADDON
    state = root / STATE
    return addon_dir, state


def read_receipt(root):
    receipt = root / STATE / "receipt.json"
    if not receipt.exists():
        return None
    if not receipt.is_file() or receipt.is_symlink():
        raise SafetyError("Invalid receipt")
    try:
        info = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SafetyError("Cannot decode installer receipt") from exc
    if (not isinstance(info, dict) or info.get("schema") != 1 or info.get("addon") != ADDON
            or not isinstance(info.get("installed"), dict)
            or not isinstance(info.get("previously_present"), bool)):
        raise SafetyError("Unknown installer receipt schema")
    return info


def plan(game, source=SOURCE):
    root = valid_root(game)
    target, state = paths(root)
    if target.is_symlink():
        raise SafetyError("Target addon is symlinked")
    files = manifest(source, strict=True)
    current = sha256(root / "AzerothSurvivors.exe")
    return {
        "mode": "read_only_plan",
        "client_sha256": current,
        "known_owner_client": current in KNOWN_OWNER_SHAS,
        "relative_destination": "benilla-config/AddOns/" + ADDON,
        "source_file_count": len(files),
        "existing_target": target.exists(),
        "managed_receipt": read_receipt(root) is not None,
        "unmanaged_state_exists": state.exists() and read_receipt(root) is None,
        "game_exe_mpqs_saves_modified": False,
    }


def install(game, source=SOURCE, *, yes=False, replace_existing=False, allow_unknown_client=False):
    if not yes:
        raise SafetyError("Install requires --yes; call plan first")
    root = valid_root(game)
    target, state = paths(root)
    files = manifest(source, strict=True)
    client_hash = sha256(root / "AzerothSurvivors.exe")
    if client_hash not in KNOWN_OWNER_SHAS and not allow_unknown_client:
        raise SafetyError("Unknown game EXE SHA-256, installation refused")
    if state.exists():
        raise SafetyError("Installer state already exists; inspect/rollback before another install")
    if target.is_symlink():
        raise SafetyError("Refusing symlinked destination")
    prior = target.exists()
    if prior and not replace_existing:
        raise SafetyError("Addon exists: explicit --replace-existing required")
    original_files = manifest(target) if prior else None
    target.parent.mkdir(parents=True, exist_ok=True)
    state.mkdir()
    stage, backup, moved = state / "staging", state / "backup", state / "prior-live"
    published = False
    prior_moved = False
    receipt_written = False
    try:
        shutil.copytree(source, stage)
        if manifest(stage, strict=True) != files:
            raise SafetyError("Staging integrity check failed")
        if prior:
            shutil.copytree(target, backup)
            if manifest(backup) != original_files:
                raise SafetyError("Backup integrity check failed")
            target.rename(moved)
            prior_moved = True
        stage.rename(target)
        published = True
        receipt = {
            "schema": 1, "addon": ADDON,
            "client_sha256": client_hash, "runtime_verified": False,
            "installed": files, "previously_present": prior,
            "previous_files": original_files,
        }
        pending = state / "receipt.pending"
        pending.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        pending.replace(state / "receipt.json")
        receipt_written = True
    except Exception:
        if published and target.exists():
            shutil.rmtree(target)
        if prior_moved and moved.exists():
            moved.rename(target)
        for p in (stage, backup):
            if p.exists():
                shutil.rmtree(p)
        pending = state / "receipt.pending"
        if pending.exists():
            pending.unlink()
        if state.exists() and not any(state.iterdir()):
            state.rmdir()
        raise
    if receipt_written and moved.exists():
        shutil.rmtree(moved)
    return {"status": "installed", "files": len(files), "backup": prior,
            "game_files_modified": False}


def rollback(game, *, yes=False):
    if not yes:
        raise SafetyError("Rollback requires --yes")
    root = valid_root(game)
    target, state = paths(root)
    receipt = read_receipt(root)
    if receipt is None:
        raise SafetyError("No managed receipt: refusing deletion")
    if not target.is_dir() or target.is_symlink() or manifest(target) != receipt["installed"]:
        raise SafetyError("Installed addon changed since installation; refusing rollback")
    backup, prior_live, staged = state / "backup", state / "installed-live", state / "restore-stage"
    previous = receipt["previously_present"]
    if prior_live.exists() or staged.exists():
        raise SafetyError("Interrupted rollback state detected")
    if previous:
        if (not backup.is_dir() or backup.is_symlink()
                or manifest(backup) != receipt["previous_files"]):
            raise SafetyError("Original backup missing or modified")
        shutil.copytree(backup, staged)
        if manifest(staged) != receipt["previous_files"]:
            shutil.rmtree(staged)
            raise SafetyError("Cannot verify restored backup")
    target.rename(prior_live)
    try:
        if previous:
            staged.rename(target)
    except Exception:
        if prior_live.exists() and not target.exists():
            prior_live.rename(target)
        raise
    shutil.rmtree(prior_live)
    if previous:
        shutil.rmtree(backup)
    (state / "receipt.json").unlink()
    if not any(state.iterdir()):
        state.rmdir()
    return {"status": "rolled_back", "previous_addon_restored": previous,
            "game_files_modified": False}


def status(game):
    root = valid_root(game)
    target, state = paths(root)
    info = read_receipt(root)
    if info is None:
        return {"status": "unmanaged", "target_exists": target.exists(),
                "interrupted_state": state.exists()}
    try:
        intact = target.is_dir() and not target.is_symlink() and manifest(target) == info["installed"]
    except SafetyError:
        intact = False
    return {"status": "managed", "files_unchanged": intact,
            "backup": info["previously_present"]}


def main(argv=None):
    ap = argparse.ArgumentParser(description="Offline addon-only transaction, no game binary edits")
    ap.add_argument("action", choices=("plan", "install", "status", "rollback"))
    ap.add_argument("--game-root", required=True)
    ap.add_argument("--source", default=str(SOURCE))
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--replace-existing", action="store_true")
    ap.add_argument("--allow-unknown-client", action="store_true")
    args = ap.parse_args(argv)
    try:
        if args.action == "plan":
            output = plan(args.game_root, args.source)
        elif args.action == "status":
            output = status(args.game_root)
        elif args.action == "install":
            output = install(args.game_root, args.source, yes=args.yes,
                             replace_existing=args.replace_existing,
                             allow_unknown_client=args.allow_unknown_client)
        else:
            output = rollback(args.game_root, yes=args.yes)
    except (SafetyError, OSError) as exc:
        print("REFUSED: " + str(exc), file=sys.stderr)
        return 2
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
