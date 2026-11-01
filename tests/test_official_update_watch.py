import hashlib
import io
import json
import unittest
from unittest.mock import patch
from tools.official_update_watch import (
    OFFICIAL, WatchError, changes, fetch_manifest, load_state,
    update_body, run, STATE_PREFIX,
)


def rec(s, version=None):
    return {"sha256": hashlib.sha256(s.encode()).hexdigest(), "bytes":len(s),
            "version":version, "observed_utc":"2026-11-01T00:00:00Z"}


class FakeResponse:
    status = 200
    def __init__(self, data):
        self.payload = io.BytesIO(data)
    def read(self, count):
        return self.payload.read(count)
    def __enter__(self): return self
    def __exit__(self, *args): return False


class OfficialUpdateWatchTests(unittest.TestCase):
    def test_sources_exactly_allowlisted(self):
        self.assertEqual(set(OFFICIAL), {"exe", "mpq"})
        self.assertTrue(all(x.startswith("https://wow.aethus.pl/") for x in OFFICIAL.values()))
        with self.assertRaises(WatchError):
            fetch_manifest("https://evil.example/json")

    def test_valid_json_produces_hash(self):
        class Opener:
            def open(self, request, timeout):
                self.request = request
                return FakeResponse(b'{"version":"0.137.0","parts":[]}')
        opener = Opener()
        x = fetch_manifest("exe", opener=opener)
        self.assertEqual("0.137.0", x["version"])
        self.assertEqual(32, len(bytes.fromhex(x["sha256"])))
        self.assertEqual(OFFICIAL["exe"], opener.request.full_url)

    def test_reject_nonjson(self):
        class Opener:
            def open(self, request, timeout):
                return FakeResponse(b"NOT JSON")
        with self.assertRaises(WatchError):
            fetch_manifest("exe", opener=Opener())

    def test_issue_marker_required(self):
        self.assertEqual({}, load_state("hello\n" + STATE_PREFIX + "{} -->"))
        with self.assertRaises(WatchError):
            load_state("no marker")
        with self.assertRaises(WatchError):
            load_state(STATE_PREFIX + "{} -->" + STATE_PREFIX + "{} -->")

    def test_baseline_no_alert(self):
        issue = "Watch\n" + STATE_PREFIX + "{} -->"
        calls=[]
        def api(method,route,token,payload=None):
            calls.append((method,route,payload))
            return {"body":issue} if method=="GET" else {}
        result=run(token="synthetic",fetch=lambda name:rec(name),api=api)
        self.assertEqual([],result["changed"])
        self.assertEqual(["exe","mpq"],sorted(result["baseline_created"]))
        self.assertTrue(any(x[0]=="PATCH" for x in calls))
        self.assertFalse(any(x[0]=="POST" for x in calls))

    def test_real_change_posts_once(self):
        state={"exe":rec("old"),"mpq":rec("mpq")}
        issue=update_body("Watch\n"+STATE_PREFIX+"{} -->",state)
        calls=[]
        def api(method,route,token,payload=None):
            calls.append((method,route,payload))
            return {"body":issue} if method=="GET" else {}
        result=run(token="synthetic",fetch=lambda name:rec("new") if name=="exe" else rec("mpq"),api=api)
        self.assertEqual(["exe"],result["changed"])
        self.assertEqual(1,len([x for x in calls if x[0]=="POST"]))
        self.assertIn("human",calls[-1][2]["body"].lower())

    def test_one_failed_fetch_preserves_other_state(self):
        state={"exe":rec("a"),"mpq":rec("b")}
        issue=update_body("Watch\n"+STATE_PREFIX+"{} -->",state)
        calls=[]
        def api(method,route,token,payload=None):
            calls.append((method,route,payload))
            return {"body":issue} if method=="GET" else {}
        def fetch(name):
            if name=="exe":raise WatchError("timeout")
            return rec("b")
        result=run(token="synthetic",fetch=fetch,api=api)
        self.assertEqual([],result["changed"])
        self.assertEqual({"exe":"timeout"},result["unavailable"])
        self.assertFalse(any(x[0]=="PATCH" for x in calls))

    def test_complete_network_outage_fails_closed(self):
        def api(method,route,token,payload=None):
            return {"body":STATE_PREFIX+"{} -->"}
        def fetch(name):raise WatchError("unavailable")
        with self.assertRaises(WatchError):
            run(token="synthetic",api=api,fetch=fetch)

    def test_same_digest_does_not_alert(self):
        before={"exe":rec("same"),"mpq":rec("also same")}
        after={"exe":rec("same"),"mpq":rec("also same")}
        self.assertEqual({},changes(before,after))

    def test_private_or_binary_content_not_persisted(self):
        baseline=STATE_PREFIX+"{} -->"
        state={"exe":rec("test",version="0.137.0")}
        result=update_body(baseline,state)
        self.assertIn("sha256",result)
        self.assertNotIn("observed_utc",result)
        self.assertEqual(state["exe"]["sha256"],load_state(result)["exe"]["sha256"])

if __name__ == "__main__":
    unittest.main()
