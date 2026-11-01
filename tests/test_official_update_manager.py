"""Complete synthetic GZIP release tests. No private game EXE or network."""
import gzip
import hashlib
import io
from pathlib import Path
import tempfile
import unittest

from tools.official_update_manager import (KNOWN_EXE, UpdateError, digest,
    part_url,validate_entry,release_records,plan,stage,apply,rollback)


def sha(raw):return hashlib.sha256(raw).hexdigest()

class Response:
    status=200
    def __init__(self,data):self.f=io.BytesIO(data)
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.f.read(n)

class StubOpener:
    def __init__(self,data):self.data=data
    def open(self,request,timeout):return Response(self.data[request.full_url])

class TestUpdates(unittest.TestCase):
    def setUp(self):
        t=tempfile.TemporaryDirectory()
        self.addCleanup(t.cleanup)
        self.root=Path(t.name)
        self.game=self.root/'OriginalGame'
        (self.game/'Data').mkdir(parents=True)
        self.original_exe=b'MZ-not-a-real-executable-STILL-ORIGINAL'
        self.original_base=b'PRIVATE-BASE-MPQ-STAYS-UNCHANGED'
        (self.game/'AzerothSurvivors.exe').write_bytes(self.original_exe)
        (self.game/'Data'/'patch.MPQ').write_bytes(self.original_base)
        (self.game/'keep.sav').write_bytes(b'KEEP THIS SAVE')
        KNOWN_EXE.add(sha(self.original_exe))
        self.addCleanup(lambda:KNOWN_EXE.discard(sha(self.original_exe)))
        self.new_exe=b'MZ'+b'EXE-NEW-v0.138.0\0'*200
        self.new_mpq=b'MPQ\x1a'+b'EXAMPLE MPQ '*100
        self.manifest_data={}
        self.exe=self._entry('0.138.0','AzerothSurvivors.exe',self.new_exe,'exe',2)
        self.mpq=self._entry('patch-B','patch-B.MPQ',self.new_mpq,'patches',1)
        self.version,self.records=release_records(self.exe,{'patches':[self.mpq]})
        self.opener=StubOpener(self.manifest_data)
        self.stage_dir=self.root/'test-stage'

    def _entry(self,dirname,name,raw,kind,parts):
        uncompressed = [raw[i*len(raw)//parts:(i+1)*len(raw)//parts] for i in range(parts)]
        entries=[]
        for i,piece in enumerate(uncompressed):
            relative=f'{dirname}/part-{i:03d}.bin'
            compressed=gzip.compress(piece,mtime=0)
            url=part_url(kind,relative)
            self.manifest_data[url]=compressed
            entries.append({'url':relative,'size':len(compressed)})
        result={'size':len(raw),'sha256':sha(raw),'parts':entries}
        if kind=='exe':result['version']='0.138.0'
        else:result['name']=name
        return result

    def test_same_file_plan(self):
        (self.game/'AzerothSurvivors.exe').write_bytes(self.new_exe)
        (self.game/'Data'/'patch-B.MPQ').write_bytes(self.new_mpq)
        report=plan(self.game,self.version,self.records)
        self.assertEqual([],report['changed_names'])
        self.assertEqual(0,report['download_bytes'])

    def test_staging_then_apply_then_rollback(self):
        report=stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        self.assertEqual('ready',report['status'])
        self.assertEqual(self.new_exe,(self.stage_dir/'payload'/'AzerothSurvivors.exe').read_bytes())
        self.assertEqual(self.new_mpq,(self.stage_dir/'payload'/'Data'/'patch-B.MPQ').read_bytes())
        self.assertEqual(self.original_exe,(self.game/'AzerothSurvivors.exe').read_bytes())
        apply_result=apply(self.game,self.stage_dir,yes=True)
        self.assertEqual('applied',apply_result['status'])
        self.assertEqual(self.new_exe,(self.game/'AzerothSurvivors.exe').read_bytes())
        self.assertEqual(self.new_mpq,(self.game/'Data'/'patch-B.MPQ').read_bytes())
        self.assertEqual(self.original_base,(self.game/'Data'/'patch.MPQ').read_bytes())
        self.assertEqual(b'KEEP THIS SAVE',(self.game/'keep.sav').read_bytes())
        undone=rollback(self.game,self.stage_dir,yes=True)
        self.assertEqual('rolled_back',undone['status'])
        self.assertEqual(self.original_exe,(self.game/'AzerothSurvivors.exe').read_bytes())
        self.assertFalse((self.game/'Data'/'patch-B.MPQ').exists())

    def test_staging_explicit_confirmation(self):
        with self.assertRaises(UpdateError):stage(self.game,self.stage_dir,self.version,self.records,opener=self.opener)
        self.assertFalse(self.stage_dir.exists())

    def test_install_explicit_confirmation(self):
        stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        with self.assertRaises(UpdateError):apply(self.game,self.stage_dir)
        self.assertEqual(self.original_exe,(self.game/'AzerothSurvivors.exe').read_bytes())

    def test_refuse_modified_game_after_staging(self):
        stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        (self.game/'AzerothSurvivors.exe').write_bytes(b'manual modification')
        with self.assertRaises(UpdateError):apply(self.game,self.stage_dir,yes=True)
        self.assertEqual(b'manual modification',(self.game/'AzerothSurvivors.exe').read_bytes())

    def test_refuse_corrupted_payload(self):
        stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        (self.stage_dir/'payload'/'AzerothSurvivors.exe').write_bytes(b'invalid')
        with self.assertRaises(UpdateError):apply(self.game,self.stage_dir,yes=True)
        self.assertEqual(self.original_exe,(self.game/'AzerothSurvivors.exe').read_bytes())

    def test_refuse_corrupt_download(self):
        for key in list(self.manifest_data):
            self.manifest_data[key]=b'not a gzip stream'
            break
        with self.assertRaises(UpdateError):stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        self.assertEqual(self.original_exe,(self.game/'AzerothSurvivors.exe').read_bytes())
        self.assertFalse(self.stage_dir.exists())

    def test_refuse_incomplete_part(self):
        key=next(iter(self.manifest_data))
        self.manifest_data[key]=self.manifest_data[key][:-1]
        with self.assertRaises(UpdateError):stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)

    def test_no_cross_domain_or_parent_paths(self):
        for evil in ['../evil','/absolute','//evil.site/payload','https://evil.site/file','v/../../bin','v\\file','v/%2e%2e/file']:
            with self.subTest(evil=evil):
                with self.assertRaises(UpdateError):part_url('exe',evil)

    def test_bad_mpq_file_names(self):
        for name in ['patch.MPQ','other.exe','../patch-B.MPQ','patch-B.mpq','patch-2.MPQ.exe']:
            with self.subTest(name=name):
                with self.assertRaises(UpdateError):validate_entry(name,self.mpq,'patches')

    def test_preserve_modifications_on_rollback(self):
        stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        apply(self.game,self.stage_dir,yes=True)
        (self.game/'AzerothSurvivors.exe').write_bytes(b'user changed after installing')
        with self.assertRaises(UpdateError):rollback(self.game,self.stage_dir,yes=True)
        self.assertEqual(b'user changed after installing',(self.game/'AzerothSurvivors.exe').read_bytes())

    def test_rollback_requires_yes(self):
        stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        apply(self.game,self.stage_dir,yes=True)
        with self.assertRaises(UpdateError):rollback(self.game,self.stage_dir)

    def test_refuse_stage_inside_game(self):
        with self.assertRaises(UpdateError):stage(self.game,self.game/'stage',self.version,self.records,yes=True,opener=self.opener)

    def test_interrupted_multi_file_apply_recovers_all_originals(self):
        from unittest.mock import patch
        import shutil
        stage(self.game,self.stage_dir,self.version,self.records,yes=True,opener=self.opener)
        original_copy = shutil.copy2
        def fail_second_install(src,dst,*args,**kwargs):
            if str(dst).endswith('patch-B.MPQ.azse-installing'):
                raise OSError('simulated disk write failure halfway through')
            return original_copy(src,dst,*args,**kwargs)
        with patch('tools.official_update_manager.shutil.copy2',side_effect=fail_second_install):
            with self.assertRaises(UpdateError):
                apply(self.game,self.stage_dir,yes=True)
        self.assertEqual(self.new_exe,(self.game/'AzerothSurvivors.exe').read_bytes())
        self.assertFalse((self.game/'Data'/'patch-B.MPQ').exists())
        result=rollback(self.game,self.stage_dir,yes=True)
        self.assertEqual('rolled_back',result['status'])
        self.assertEqual(self.original_exe,(self.game/'AzerothSurvivors.exe').read_bytes())
        self.assertFalse((self.game/'Data'/'patch-B.MPQ').exists())

    def test_unknown_client_fails(self):
        (self.game/'AzerothSurvivors.exe').write_bytes(b'unknown local client')
        with self.assertRaises(UpdateError):plan(self.game,self.version,self.records)

    def test_duplicate_mpq_rejected(self):
        with self.assertRaises(UpdateError):release_records(self.exe,{'patches':[self.mpq,self.mpq]})

if __name__=='__main__':unittest.main()
