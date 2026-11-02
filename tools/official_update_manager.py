"""Official, opt-in AZSE updater for the original Windows game.

Source-only: no game EXE/MPQ is bundled. The author's JSON provides GZIP
parts + WHOLE-FILE SHA256; every staged file is verified before application.
This is NOT a Bevy/native in-game menu and is never run without a user action.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
from urllib.parse import urljoin, urlsplit
import zlib

from tools.official_manifest_probe import retrieve, URLS, NoRedirect

SCHEMA = 1
MAX_TARGET_BYTES = 3 * 1024 ** 3
MAX_PART_BYTES = 64 * 1024 ** 2
MAX_PARTS = 160
SHA = re.compile(r'[0-9a-f]{64}\Z')
PART_PATH = re.compile(r'[A-Za-z0-9._/-]{1,180}\Z')
MPQ_NAME = re.compile(r'patch-(?:[2-9]|[A-Z]|[1-9][0-9])\.MPQ\Z')
KNOWN_EXE = {
    '2c2f3926e1f8f8092809f5de0624ac8f2197bb341a2870d408ce0250f13f094a',
    'eb744751b4e17ec1397b0cdc85a22af63b6af63c1da1d9c2861762c3c4d8947c',
    'aa6b254f905e2f7a4cbc7c2c8f11af822ec362e3d2b8e84cabd8c38893a10dc8',
    'eb5fd1c1b96e6180fcf5f3d685d90a61471af28d22e5f060c02b7b7663fbf79e',
    '0e8e314df4d78ab211b1bef5c48d78d713ed64260894af342f998d298d74d274',  # original 0.139.0
}

class UpdateError(ValueError):
    pass


def digest(file):
    h = hashlib.sha256()
    with Path(file).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            h.update(chunk)
    return h.hexdigest()


def game_root(value):
    p = Path(value)
    if not p.is_dir() or p.is_symlink():
        raise UpdateError('Game root missing or symlinked')
    root = p.resolve()
    exe, data = root / 'AzerothSurvivors.exe', root / 'Data'
    if exe.is_symlink() or not exe.is_file() or data.is_symlink() or not data.is_dir():
        raise UpdateError('Expected original AzerothSurvivors.exe and Data/ folder')
    return root


def target_path(root, name):
    if name == 'AzerothSurvivors.exe':
        dest = root / name
    elif MPQ_NAME.fullmatch(name):
        dest = root / 'Data' / name
    else:
        raise UpdateError('Unrecognized game file name')
    if dest.is_symlink() or (dest.exists() and not dest.is_file()):
        raise UpdateError('Game target is symlinked or not an ordinary file')
    return dest


def part_url(kind, relative):
    if (not isinstance(relative, str) or not PART_PATH.fullmatch(relative)
        or relative.startswith(('/', '.')) or '\\' in relative or
        any(bit in ('', '.', '..') for bit in relative.split('/'))):
        raise UpdateError('Invalid remote part path')
    final = urljoin(URLS[kind], relative)
    parsed = urlsplit(final)
    expected = '/exe/data/' if kind == 'patches' else '/exe/'
    if parsed.scheme != 'https' or parsed.netloc != 'wow.aethus.pl' or not parsed.path.startswith(expected):
        raise UpdateError('Part escapes creator download origin')
    return final


def validate_entry(name, value, kind):
    if not isinstance(value, dict):
        raise UpdateError('Invalid target entry')
    if kind == 'exe':
        if name != 'AzerothSurvivors.exe': raise UpdateError('Wrong EXE target')
    elif not MPQ_NAME.fullmatch(name):
        raise UpdateError('Unexpected MPQ filename')
    size, hash_, parts = value.get('size'), value.get('sha256'), value.get('parts')
    if type(size) is not int or not 1 <= size <= MAX_TARGET_BYTES:
        raise UpdateError('Invalid finished-file size')
    if not isinstance(hash_, str) or not SHA.fullmatch(hash_):
        raise UpdateError('Missing/invalid finished SHA256')
    if not isinstance(parts, list) or not 1 <= len(parts) <= MAX_PARTS:
        raise UpdateError('No valid compressed parts')
    out=[]
    total=0
    for part in parts:
        if not isinstance(part,dict) or type(part.get('size')) is not int:
            raise UpdateError('Malformed part')
        amount = part['size']
        if not 1 <= amount <= MAX_PART_BYTES: raise UpdateError('Part exceeds download limit')
        url = part_url(kind, part.get('url'))
        out.append({'url':url,'size':amount})
        total += amount
    if total > MAX_TARGET_BYTES: raise UpdateError('Total compressed download too large')
    return {'name':name,'size':size,'sha256':hash_,'parts':out,'compressed_bytes':total}


def release_records(exe_manifest, patch_manifest):
    if not isinstance(exe_manifest,dict) or not isinstance(patch_manifest,dict):
        raise UpdateError('Unexpected official manifest')
    version=exe_manifest.get('version')
    if not isinstance(version,str) or not re.fullmatch(r'[0-9]{1,4}\.[0-9]{1,4}\.[0-9]{1,4}',version):
        raise UpdateError('Unexpected official version string')
    records=[validate_entry('AzerothSurvivors.exe',exe_manifest,'exe')]
    patches=patch_manifest.get('patches')
    if not isinstance(patches,list) or len(patches)>30:
        raise UpdateError('Malformed official MPQ list')
    seen=set()
    for p in patches:
        if not isinstance(p,dict) or not isinstance(p.get('name'),str):raise UpdateError('Invalid patch name')
        name=p['name']
        if name in seen: raise UpdateError('Duplicate MPQ')
        seen.add(name)
        records.append(validate_entry(name,p,'patches'))
    return version,records


def fetch_records(fetch=retrieve):
    return release_records(fetch('exe'),fetch('patches'))


def plan(root, version, records, *, allow_unknown_client=False):
    root=game_root(root)
    if not records or records[0]['name']!='AzerothSurvivors.exe':
        raise UpdateError('No original EXE entry')
    current_exe=digest(root/'AzerothSurvivors.exe')
    if (current_exe not in KNOWN_EXE and current_exe!=records[0]['sha256']
        and not allow_unknown_client):
        raise UpdateError('Unknown local EXE fingerprint: explicit --allow-unknown-client required')
    changed=[]
    installed=[]
    for rec in records:
        path=target_path(root,rec['name'])
        found=digest(path) if path.is_file() else None
        row={'name':rec['name'],'destination':str(path.relative_to(root)),
             'expected_sha256':rec['sha256'],'expected_bytes':rec['size'],
             'current_sha256':found, 'action':'current' if found==rec['sha256'] else 'download',
             'compressed_bytes':rec['compressed_bytes']}
        installed.append(row)
        if row['action']!='current':
            changed.append(rec)
    return {'game_root':str(root),'official_version':version,'targets':installed,
            'changed_names':[r['name'] for r in changed],
            'download_bytes':sum(r['compressed_bytes'] for r in changed),
            'files_to_stage':changed,
            'base_patch_mpq_untouched':True}


def fetch_parts(opener, parts, stream, max_output):
    """Restore either a gzip stream split across parts or separate members.

    Official 20-MiB EXE chunks can be *fragments of one gzip stream*.
    They must be decoded in strict order, without assuming gzip EOF at each
    HTTP part boundary. Per-part byte counts and total output are bounded.
    """
    decoder = None
    expanded = 0
    for index, part in enumerate(parts):
        url, compressed_size = part['url'], part['size']
        if decoder is None or decoder.eof:
            decoder = zlib.decompressobj(16 + zlib.MAX_WBITS)
        request = urllib.request.Request(url, method='GET', headers={
            'Accept-Encoding': 'identity',
            'User-Agent': 'AZSE-Verified-Update-Manager/1.1'})
        received = 0
        try:
            with opener.open(request, timeout=30) as response:
                if response.status != 200:
                    raise UpdateError('Official compressed part HTTP status ' + str(response.status))
                while True:
                    block = response.read(min(1024*1024, compressed_size-received+1))
                    if not block:
                        break
                    received += len(block)
                    if received > compressed_size:
                        raise UpdateError('Compressed part larger than declared')
                    data = block
                    while data:
                        room = max_output - expanded
                        if room < 0:
                            raise UpdateError('Expanded file exceeded manifest size')
                        decoded = decoder.decompress(data, min(1024*1024, room+1))
                        if len(decoded) > room:
                            raise UpdateError('Expanded file exceeded manifest size')
                        stream.write(decoded)
                        expanded += len(decoded)
                        data = decoder.unconsumed_tail
                        if decoder.eof:
                            if data or decoder.unused_data:
                                raise UpdateError('Unexpected trailing GZIP member bytes')
                            break
        except (OSError, TimeoutError, urllib.error.URLError, zlib.error) as exc:
            raise UpdateError('Official part download/decode failed: ' + type(exc).__name__) from None
        if received != compressed_size:
            raise UpdateError('Compressed part ' + str(index) + ' incomplete')
    if decoder is None or not decoder.eof:
        raise UpdateError('GZIP stream has no completed trailer after final part')
    tail = decoder.flush()
    if expanded + len(tail) > max_output:
        raise UpdateError('Decompressed trailer exceeded limit')
    stream.write(tail)
    return expanded


def stage(root, staging, version, records, *, yes=False, allow_unknown_client=False, opener=None):
    if not yes:raise UpdateError('Staging requires explicit --yes')
    p=plan(root,version,records,allow_unknown_client=allow_unknown_client)
    root=game_root(root)
    dest=Path(staging)
    if dest.exists() or dest.is_symlink():raise UpdateError('Staging target already exists')
    if not dest.parent.is_dir() or dest.parent.is_symlink():raise UpdateError('Create a normal staging parent directory')
    if dest.resolve().is_relative_to(root):raise UpdateError('Stage outside game directory')
    opener=opener or urllib.request.build_opener(NoRedirect())
    changes=p['files_to_stage']
    if not changes:return {'status':'up_to_date','official_version':version,'changed_names':[]}
    dest.mkdir()
    try:
        for rec in changes:
            relative=Path('AzerothSurvivors.exe') if rec['name']=='AzerothSurvivors.exe' else Path('Data')/rec['name']
            file=dest/'payload'/relative
            file.parent.mkdir(parents=True,exist_ok=True)
            with file.open('xb') as writer:
                expanded=fetch_parts(opener,rec['parts'],writer,rec['size'])
            if expanded!=rec['size'] or file.stat().st_size!=rec['size'] or digest(file)!=rec['sha256']:
                raise UpdateError('Finished-file SHA256/size verification failed: '+rec['name'])
        receipt={'schema':SCHEMA,'game_root':str(root),'version':version,
                 'status':'ready','changes':[],
                 'base_patch_mpq_untouched':True}
        for rec in changes:
            target=target_path(root,rec['name'])
            receipt['changes'].append({'name':rec['name'],'sha256':rec['sha256'],'size':rec['size'],
                                       'previous_sha256':digest(target) if target.is_file() else None})
        _state_write(dest,receipt)
        return {'status':'ready','version':version,'stage_dir':str(dest),'changed_names':[r['name'] for r in changes]}
    except Exception:
        shutil.rmtree(dest)
        raise


def _state_write(stage_dir,state):
    pending=stage_dir/'state.pending'
    pending.write_text(json.dumps(state,indent=2)+'\n',encoding='utf-8')
    pending.replace(stage_dir/'state.json')


def _state_load(stage_dir,root):
    dir=Path(stage_dir)
    if not dir.is_dir() or dir.is_symlink():raise UpdateError('Invalid staging folder')
    file=dir/'state.json'
    if file.is_symlink() or not file.is_file() or file.stat().st_size>100000:
        raise UpdateError('Missing or unsafe stage receipt')
    try:state=json.loads(file.read_text('utf-8'))
    except (ValueError,UnicodeError):raise UpdateError('Invalid stage receipt') from None
    if (not isinstance(state,dict) or state.get('schema')!=SCHEMA or
        state.get('game_root')!=str(root) or state.get('status') not in ('ready','applying','applied')):
        raise UpdateError('Stage belongs to a different game or schema')
    changes=state.get('changes')
    if not isinstance(changes,list) or not 1<=len(changes)<=31:
        raise UpdateError('Invalid staged change count')
    names=set()
    for rec in changes:
        if not isinstance(rec,dict) or rec.get('name') in names:
            raise UpdateError('Invalid or repeated staged item')
        name=rec['name'];names.add(name)
        target_path(root,name)
        if not isinstance(rec.get('sha256'),str) or not SHA.fullmatch(rec['sha256']):
            raise UpdateError('Invalid staged hash')
        if rec.get('previous_sha256') is not None and not SHA.fullmatch(str(rec['previous_sha256'])):
            raise UpdateError('Invalid previous hash')
        if type(rec.get('size')) is not int or not 1<=rec['size']<=MAX_TARGET_BYTES:
            raise UpdateError('Invalid size in stage')
    return state


def _payload(stage_dir,name):
    return Path(stage_dir)/'payload'/('AzerothSurvivors.exe' if name=='AzerothSurvivors.exe' else 'Data/'+name)


def game_running():
    if os.name!='nt':return False
    try:
        p=subprocess.run(['tasklist','/FO','CSV','/NH'],capture_output=True,text=True,timeout=7)
        if p.returncode!=0:raise UpdateError('Could not check if game is running')
        return any(x.lower().startswith('"azerothsurvivors.exe",') for x in p.stdout.splitlines())
    except (OSError,subprocess.TimeoutExpired):
        raise UpdateError('Cannot confirm game is closed') from None


def apply(root,stage_dir,*,yes=False):
    if not yes:raise UpdateError('Applying updates requires --yes')
    root=game_root(root)
    if game_running():raise UpdateError('Close AzerothSurvivors.exe before installing')
    stage_dir=Path(stage_dir)
    if stage_dir.resolve().is_relative_to(root):raise UpdateError('Stage must be outside the game')
    state=_state_load(stage_dir,root)
    if state['status']!='ready':raise UpdateError('Stage already applied or interrupted; rollback first')
    for rec in state['changes']:
        current=target_path(root,rec['name'])
        original=digest(current) if current.is_file() else None
        if original!=rec['previous_sha256']:
            raise UpdateError('Game file changed after staging; refusing installation')
        image=_payload(stage_dir,rec['name'])
        if image.is_symlink() or not image.is_file() or image.stat().st_size!=rec['size'] or digest(image)!=rec['sha256']:
            raise UpdateError('Staged file altered/missing; refusing installation')
    backup_dir=stage_dir/'backup'
    if backup_dir.exists():raise UpdateError('Existing backup state; refusing')
    for rec in state['changes']:
        source=target_path(root,rec['name'])
        if source.exists():
            backup=backup_dir/('AzerothSurvivors.exe' if rec['name']=='AzerothSurvivors.exe' else 'Data/'+rec['name'])
            backup.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source,backup)
            if digest(backup)!=rec['previous_sha256']:
                raise UpdateError('Backup integrity mismatch; original game untouched')
    state['status']='applying'
    _state_write(stage_dir,state)
    try:
        for rec in state['changes']:
            image=_payload(stage_dir,rec['name'])
            target=target_path(root,rec['name'])
            pending=target.with_name(target.name+'.azse-installing')
            if pending.exists() or pending.is_symlink():raise UpdateError('Unexpected pending file in original game')
            shutil.copy2(image,pending)
            if digest(pending)!=rec['sha256']:raise UpdateError('Pending install checksum mismatch')
            pending.replace(target)
        state['status']='applied'
        _state_write(stage_dir,state)
        return {'status':'applied','version':state['version'], 'changed_names':[r['name'] for r in state['changes']],
                'backup_dir':str(backup_dir),'rollback_available':True}
    except Exception as exc:
        raise UpdateError('Update interrupted; original backups preserved. Use rollback. '+str(exc)) from None


def rollback(root,stage_dir,*,yes=False):
    if not yes:raise UpdateError('Rollback requires --yes')
    root=game_root(root)
    if game_running():raise UpdateError('Close game before rollback')
    stage_dir=Path(stage_dir)
    state=_state_load(stage_dir,root)
    if state['status'] not in ('applying','applied'):
        raise UpdateError('This stage was not applied')
    backups=stage_dir/'backup'
    for rec in state['changes']:
        target=target_path(root,rec['name'])
        actual=digest(target) if target.is_file() else None
        if actual not in (rec['sha256'],rec['previous_sha256']):
            raise UpdateError('Game target modified since update; refusing destructive rollback')
        orig=rec['previous_sha256']
        if orig:
            backup=backups/('AzerothSurvivors.exe' if rec['name']=='AzerothSurvivors.exe' else 'Data/'+rec['name'])
            if backup.is_symlink() or not backup.is_file() or digest(backup)!=orig:
                raise UpdateError('Backup missing or changed')
    for rec in state['changes']:
        target=target_path(root,rec['name'])
        if rec['previous_sha256']:
            backup=backups/('AzerothSurvivors.exe' if rec['name']=='AzerothSurvivors.exe' else 'Data/'+rec['name'])
            candidate=target.with_name(target.name+'.azse-restore')
            if candidate.exists() or candidate.is_symlink():raise UpdateError('Unexpected restore file')
            shutil.copy2(backup,candidate)
            candidate.replace(target)
        elif target.exists():target.unlink()
    state['status']='ready'
    _state_write(stage_dir,state)
    return {'status':'rolled_back','names':[r['name'] for r in state['changes']]}


def main(argv=None):
    parser=argparse.ArgumentParser(description='Verified official GZIP chunk updater, opt-in only')
    parser.add_argument('action',choices=['check','stage','apply','rollback'])
    parser.add_argument('--game-root',required=True)
    parser.add_argument('--stage-dir')
    parser.add_argument('--yes',action='store_true')
    parser.add_argument('--allow-unknown-client',action='store_true')
    args=parser.parse_args(argv)
    try:
        root=game_root(args.game_root)
        if args.action in ('stage','apply','rollback') and not args.stage_dir:
            raise UpdateError('--stage-dir required for stage/apply/rollback')
        if args.action in ('check','stage'):
            version, records=fetch_records()
            output=(plan(root,version,records,allow_unknown_client=args.allow_unknown_client)
                    if args.action=='check' else
                    stage(root,args.stage_dir,version,records,yes=args.yes,
                          allow_unknown_client=args.allow_unknown_client))
            if args.action=='check':
                output.pop('files_to_stage',None)
        elif args.action=='apply':output=apply(root,args.stage_dir,yes=args.yes)
        else:output=rollback(root,args.stage_dir,yes=args.yes)
        print(json.dumps(output,indent=2,ensure_ascii=False))
        return 0
    except (OSError,UpdateError) as exc:
        print('REFUSED: '+str(exc),file=sys.stderr)
        return 2

if __name__=='__main__':raise SystemExit(main())
