import copy
import hashlib
import json
import unittest
from unittest.mock import patch
from tools.release_intelligence import (
    ReleaseError, compare, parse_manifest, markdown, load_state, patch_state,
    run, stable_hash, parts_summary, clean_note, get_official, NoRedirect,
)


def example(version='0.138.0', patches=None, sha='a' * 64):
    return {
        'exe': {'version':version,'size':147995648,'sha256':sha,
                'notes':'UI improvements and bug fixes.',
                'parts':[{'url':version+'/part-000.bin','size':20971520},
                         {'url':version+'/part-001.bin','size':20971520},
                         {'url':version+'/part-002.bin','size':7939657}]},
        'mpq': {'patches': patches if patches is not None else [
            {'name':'patch-B.MPQ','size':2935,'sha256':'b'*64,
             'parts':[{'url':'patch-B/part-000.bin','size':1394}]}]}}


def snap(**kw):
    z=example(**kw)
    return parse_manifest(z['exe'],z['mpq'])


class FakeGitHub:
    def __init__(self, state=None):
        self.body = 'Release ledger\n<!-- AZSE_RELEASE_INTEL_V1:{} -->'
        if state is not None: self.body = patch_state(self.body, state)
        self.calls=[]
        self.issues=[]
    def __call__(self, method, route, token, body=None):
        self.calls.append((method,route,body))
        if route == '/issues/20' and method == 'GET': return {'body':self.body}
        if route == '/issues/20' and method == 'PATCH':
            self.body = body['body'];return {'ok':True}
        if route == '/issues?state=all&per_page=100':return self.issues[:]
        if route == '/issues' and method == 'POST':
            self.issues.append(body); return {'number':100+len(self.issues)}
        if route == '/issues/20/comments' and method == 'POST':return {'id':1}
        raise AssertionError((method,route))


class ReleaseIntelTests(unittest.TestCase):
    def test_valid_official_manifest_shape(self):
        data=snap()
        self.assertEqual('0.138.0',data['exe']['version'])
        self.assertEqual(3,data['exe']['parts']['count'])
        self.assertEqual(1,data['mpq']['patch-B.MPQ']['parts']['count'])
        self.assertNotIn('url',str(data))

    def test_first_snapshot_is_baseline_not_change(self):
        d=compare(None,snap())
        self.assertTrue(d['first_baseline'])
        self.assertFalse(d['changed'])

    def test_new_exe_with_same_mpq_hash(self):
        old=snap()
        newer=snap(version='0.139.0',sha='c'*64)
        d=compare(old,newer)
        self.assertTrue(d['changed'])
        self.assertIsNotNone(d['exe'])
        self.assertEqual([],d['modified'])

    def test_mpq_change_without_version_bump(self):
        before=snap()
        after=copy.deepcopy(before)
        after['mpq']['patch-B.MPQ']['sha256']='c'*64
        d=compare(before,after)
        self.assertTrue(d['changed'])
        self.assertIsNone(d['exe'])
        self.assertEqual(['patch-B.MPQ'],d['modified'])

    def test_add_remove_are_not_install_instructions(self):
        old=snap()
        new=copy.deepcopy(old)
        new['mpq'].pop('patch-B.MPQ')
        new['mpq']['patch-C.MPQ']={'size':1,'sha256':'d'*64,'parts':{'count':1,'compressed_bytes':1}}
        d=compare(old,new)
        self.assertEqual(['patch-C.MPQ'],d['added'])
        self.assertEqual(['patch-B.MPQ'],d['removed'])
        self.assertIn('not a deletion instruction', markdown(new,d))

    def test_stable_hash_independent_dict_order(self):
        s=snap()
        reloaded=json.loads(json.dumps(s,sort_keys=True))
        self.assertEqual(stable_hash(s),stable_hash(reloaded))

    def test_manifest_rejects_host_and_parent_traversal(self):
        bad=example();bad['exe']['parts'][0]['url']='https://evil.test/mal.exe'
        with self.assertRaises(ReleaseError):parse_manifest(bad['exe'],bad['mpq'])
        bad=example();bad['exe']['parts'][0]['url']='../part-000.bin'
        with self.assertRaises(ReleaseError):parse_manifest(bad['exe'],bad['mpq'])

    def test_manifest_rejects_duplicate_patch_name(self):
        item=example()['mpq']['patches'][0]
        with self.assertRaises(ReleaseError):parse_manifest(example()['exe'],{'patches':[item,item]})

    def test_manifest_rejects_missing_sha_or_wrong_size(self):
        bad=example();bad['exe']['sha256']='x'*64
        with self.assertRaises(ReleaseError):parse_manifest(bad['exe'],bad['mpq'])
        bad=example();bad['exe']['size']=True
        with self.assertRaises(ReleaseError):parse_manifest(bad['exe'],bad['mpq'])
        bad=example();bad['exe']['parts'][0]['size']=2**31
        with self.assertRaises(ReleaseError):parse_manifest(bad['exe'],bad['mpq'])

    def test_reject_manifest_binary_as_text(self):
        bad=example();bad['exe']['notes']='\r\n!----<script>evil</script>'
        s=parse_manifest(bad['exe'],bad['mpq'])
        self.assertNotIn('\n',s['exe']['release_notes'])
        self.assertTrue(len(s['exe']['release_notes'])<=500)

    def test_exact_one_marker_required(self):
        self.assertIsNone(load_state('Test\n<!-- AZSE_RELEASE_INTEL_V1:{} -->'))
        with self.assertRaises(ReleaseError):load_state('not a marker')
        with self.assertRaises(ReleaseError):load_state('<!-- AZSE_RELEASE_INTEL_V1:{} -->' * 2)

    def test_state_roundtrip(self):
        base='Title\n<!-- AZSE_RELEASE_INTEL_V1:{} -->'
        cur=snap()
        result=patch_state(base,cur)
        self.assertEqual(cur,load_state(result))

    def test_first_run_writes_baseline_and_no_update_ticket(self):
        api=FakeGitHub(); data=example()
        result=run(token='test',fetch=lambda name:data[name],request=api)
        self.assertEqual('baseline',result['status'])
        self.assertEqual([],api.issues)
        self.assertEqual(data['exe']['version'],load_state(api.body)['exe']['version'])

    def test_new_release_creates_ticket_and_advances(self):
        api=FakeGitHub(snap()); data=example(version='0.139.0',sha='c'*64)
        result=run(token='test',fetch=lambda name:data[name],request=api)
        self.assertEqual('changed',result['status'])
        self.assertEqual(1,len(api.issues))
        self.assertIn('0.139.0',api.issues[0]['title'])
        self.assertIn('Bevy Options',api.issues[0]['body'])
        self.assertEqual('0.139.0',load_state(api.body)['exe']['version'])

    def test_identical_second_run_makes_no_api_writes(self):
        api=FakeGitHub(snap());data=example()
        result=run(token='test',fetch=lambda name:data[name],request=api)
        self.assertEqual('unchanged',result['status'])
        self.assertEqual(['GET'],[call[0] for call in api.calls])

    def test_duplicate_ticket_recovery_after_partial_failure(self):
        api=FakeGitHub(snap());data=example(version='0.139.0',sha='c'*64)
        title='AZSE compatibility audit: 0.139.0 ['+stable_hash(snap(version='0.139.0',sha='c'*64))[:12]+']'
        api.issues.append({'title':title})
        result=run(token='test',fetch=lambda name:data[name],request=api)
        self.assertEqual('changed',result['status'])
        self.assertEqual(1,len(api.issues))
        self.assertFalse(any(method=='POST' for method,route,_ in api.calls))

    def test_failed_source_does_not_advance_baseline(self):
        api=FakeGitHub(snap())
        def fetch(name):
            if name=='mpq':raise ReleaseError('server error')
            return example()['exe']
        with self.assertRaises(ReleaseError):run(token='test',fetch=fetch,request=api)
        self.assertEqual([],api.calls)

    def test_different_note_triggers_review_without_file_patch(self):
        old=snap();new=copy.deepcopy(old)
        new['exe']['release_notes']='new description'
        diff=compare(old,new)
        self.assertTrue(diff['notes_changed'])
        self.assertTrue(diff['changed'])
        self.assertIsNone(diff['exe'])

if __name__ == '__main__':unittest.main()
