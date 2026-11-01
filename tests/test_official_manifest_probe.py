import io
import unittest
from tools.official_manifest_probe import URLS,shape,retrieve,ProbeError

class Response:
    status=200
    def __init__(self,body):self.file=io.BytesIO(body)
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def read(self,n):return self.file.read(n)

class Opener:
    def __init__(self,content):self.content=content
    def open(self,req,timeout):
        self.last_url=req.full_url
        return Response(self.content)

class Tests(unittest.TestCase):
    def test_only_fixed_hosts(self):
        self.assertEqual(set(URLS),{'exe','patches'})
        self.assertTrue(all(x.startswith('https://wow.aethus.pl/') for x in URLS.values()))
        with self.assertRaises(ProbeError):retrieve('http://other.example')
    def test_schema_with_release_parts(self):
        o=Opener(b'{"version":"0.138.0","parts":[{"name":"piece-1","size":16,"sha256":"abc"}]}')
        summary=shape(retrieve('exe',o))
        self.assertEqual('object',summary['type'])
        self.assertEqual('0.138.0',summary['fields']['version'])
        self.assertEqual(1,summary['fields']['parts']['length'])
        self.assertEqual(URLS['exe'],o.last_url)
    def test_bad_content(self):
        with self.assertRaises(ProbeError):retrieve('exe',Opener(b'<html>not json</html>'))
    def test_refuses_large_json(self):
        with self.assertRaises(ProbeError):retrieve('exe',Opener(b' '* (1024*1024+1)))
    def test_hidden_values(self):
        s=shape({'secret':'not a token to publish','notes':'a'*200,'url':'https://example.org/path/to/a'})
        self.assertNotIn('not a token',str(s))
        self.assertEqual('example.org',s['fields']['url']['host'])
        self.assertEqual(200,s['fields']['notes']['length'])
if __name__=='__main__':unittest.main()
