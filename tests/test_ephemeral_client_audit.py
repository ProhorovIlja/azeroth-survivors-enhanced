"""Synthetic release and gzip tests; no original game assets."""
import gzip, hashlib, io, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
from tools import ephemeral_client_audit as a

class Reply:
    status=200
    def __init__(self,b): self.f=io.BytesIO(b)
    def read(self,n): return self.f.read(n)
    def __enter__(self): return self
    def __exit__(self,*args): return False
class Client:
    def __init__(self,items): self.items=items
    def open(self,req,timeout=0): return Reply(self.items[req.full_url])
def manifest(part=None):
    return {"version":a.VERSION,"sha256":a.SHA,"size":a.SIZE,
            "parts":[part or {"url":"0.139.0/part-000.bin","size":2}]}

class Tests(unittest.TestCase):
    def test_exact_manifest(self):
        self.assertEqual([(a.ORIGIN+"0.139.0/part-000.bin",2)],a.validate(manifest()))
    def test_wrong_release_fails(self):
        m=manifest();m["version"]="0.140.0"
        with self.assertRaises(a.AuditError):a.validate(m)
    def test_wrong_sha_fails(self):
        m=manifest();m["sha256"]="0"*64
        with self.assertRaises(a.AuditError):a.validate(m)
    def test_traversal_fails(self):
        with self.assertRaises(a.AuditError):a.validate(manifest({"url":"../bad","size":2}))
    def test_reordered_parts_fail(self):
        with self.assertRaises(a.AuditError):a.validate(manifest({"url":"0.139.0/part-010.bin","size":2}))
    def test_part_size_bounds(self):
        with self.assertRaises(a.AuditError):a.validate(manifest({"url":"0.139.0/part-000.bin","size":2**30}))
    def test_boolean_size_fails(self):
        with self.assertRaises(a.AuditError):a.validate(manifest({"url":"0.139.0/part-000.bin","size":True}))
    def test_multiple_gzip_parts_verified(self):
        raw=b"MZ"+b"A"*80
        c=[gzip.compress(raw[:42]),gzip.compress(raw[42:])]
        parts=[(a.ORIGIN+f"0.139.0/part-{i:03d}.bin",len(b)) for i,b in enumerate(c)]
        with patch.object(a,"SIZE",len(raw)),patch.object(a,"SHA",hashlib.sha256(raw).hexdigest()):
            with tempfile.TemporaryDirectory() as folder:
                target=Path(folder)/"original.exe"
                r=a.download_verified(parts,target,Client(dict(zip((u for u,_ in parts),c))))
                self.assertEqual(r["sha256"],hashlib.sha256(raw).hexdigest())
                self.assertEqual(target.read_bytes(),raw)
    def test_corrupt_part_unlinks_private_file(self):
        raw=b"MZ"+b"X"*20
        gz=gzip.compress(raw)
        url=a.ORIGIN+"0.139.0/part-000.bin"
        with patch.object(a,"SIZE",len(raw)),patch.object(a,"SHA",hashlib.sha256(raw).hexdigest()):
            with tempfile.TemporaryDirectory() as folder:
                dest=Path(folder)/"private.exe"
                with self.assertRaises(Exception):
                    a.download_verified([(url,len(gz))],dest,Client({url:gz[:-1]+b"\x00"}))
                self.assertFalse(dest.exists())
    def test_bad_sha_unlinks_file(self):
        raw=b"MZ"+b"X"*20;gz=gzip.compress(raw)
        url=a.ORIGIN+"0.139.0/part-000.bin"
        with patch.object(a,"SIZE",len(raw)),patch.object(a,"SHA","0"*64):
            with tempfile.TemporaryDirectory() as folder:
                dest=Path(folder)/"private.exe"
                with self.assertRaises(a.AuditError):a.download_verified([(url,len(gz))],dest,Client({url:gz}))
                self.assertFalse(dest.exists())
    def test_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            dest=Path(folder)/"important";dest.write_bytes(b"safe")
            with self.assertRaises(a.AuditError):a.download_verified([],dest,Client({}))
            self.assertEqual(dest.read_bytes(),b"safe")
    def test_unchanged_status_never_assumed(self):
        self.assertEqual(a.PRIOR["options_page_controls"],"0x3f74c0")
        self.assertNotEqual(a.PRIOR["options_page_controls"],None)

if __name__=="__main__":unittest.main()
