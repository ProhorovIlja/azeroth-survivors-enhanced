"""Read-only Aethus official update JSON schema probe (no game binaries downloaded)."""
import json
import urllib.error
import urllib.request
from urllib.parse import urlparse

URLS = {'exe':'https://wow.aethus.pl/exe/latest.json',
        'patches':'https://wow.aethus.pl/exe/data/patches.json'}
MAX = 1024 * 1024

class ProbeError(ValueError):
    pass

class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise ProbeError('Official manifest redirect refused')


def retrieve(kind, opener=None):
    if kind not in URLS:
        raise ProbeError('Unknown manifest name')
    opener = opener or urllib.request.build_opener(NoRedirect())
    req = urllib.request.Request(URLS[kind], method='GET',
                                 headers={'Accept':'application/json', 'User-Agent':'AZSE-Manifest-Schema-Audit/1.0'})
    try:
        with opener.open(req,timeout=15) as response:
            if response.status != 200:
                raise ProbeError('Bad HTTP status: '+str(response.status))
            payload = response.read(MAX+1)
    except (TimeoutError, OSError, urllib.error.URLError) as exc:
        raise ProbeError('Fetch failed: '+type(exc).__name__) from None
    if len(payload)>MAX:
        raise ProbeError('Oversized JSON')
    try:
        obj=json.loads(payload.decode('utf-8'))
    except (ValueError,UnicodeError):
        raise ProbeError('Invalid UTF-8 JSON') from None
    if not isinstance(obj,(dict,list)):
        raise ProbeError('Unexpected JSON root type')
    return obj


def shape(obj,depth=0):
    if depth>=4:return type(obj).__name__
    if isinstance(obj,dict):
        fields={}
        for k,v in list(obj.items())[:25]:
            if isinstance(v,str):
                if k.lower()=='url':
                    p=urlparse(v)
                    fields[k]={'type':'url','scheme':p.scheme,'host':p.hostname,'path':p.path[:100]}
                elif k.lower() in ('version','sha256','size','path','name','file','filename'):
                    fields[k]=v[:120]
                else:fields[k]={'type':'str','length':len(v)}
            else:fields[k]=shape(v,depth+1)
        return {'type':'object','keys':list(obj)[:25],'fields':fields}
    if isinstance(obj,list):
        return {'type':'array','length':len(obj),'first':shape(obj[0],depth+1) if obj else None,
                'second':shape(obj[1],depth+1) if len(obj)>1 else None}
    return obj if isinstance(obj,(int,float,bool)) else type(obj).__name__


def main():
    results,errors={},{}
    for name in URLS:
        try:results[name]=shape(retrieve(name))
        except ProbeError as exc:errors[name]=str(exc)
    print(json.dumps({'manifests':results,'errors':errors},indent=2,ensure_ascii=False))
    return 0 if results else 2

if __name__=='__main__':
    raise SystemExit(main())
