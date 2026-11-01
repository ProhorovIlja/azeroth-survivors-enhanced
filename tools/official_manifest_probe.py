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


def details(kind, obj):
    """Summary of all named patch files and relative part paths, no binary GET."""
    if kind == 'exe':
        values = [dict(name='AzerothSurvivors.exe', size=obj.get('size'), sha256=obj.get('sha256'), parts=obj.get('parts', []))] if isinstance(obj,dict) else []
    else:
        values = obj.get('patches', []) if isinstance(obj,dict) else []
    out=[]
    for value in values[:30]:
        if not isinstance(value,dict):continue
        parts=value.get('parts')
        if not isinstance(parts,list):continue
        listed=[]
        for part in parts[:24]:
            if not isinstance(part,dict):continue
            listed.append({'url':str(part.get('url',''))[:110], 'size':part.get('size'), 'sha256':part.get('sha256')})
        out.append({'name':value.get('name','AzerothSurvivors.exe') if kind=='patches' else 'AzerothSurvivors.exe',
                    'size':value.get('size'), 'sha256':value.get('sha256'), 'parts':listed})
    return out


def main():
    results,errors={},{}
    records={}
    for name in URLS:
        try:
            obj=retrieve(name)
            results[name]=shape(obj)
            records[name]=details(name,obj)
        except ProbeError as exc:errors[name]=str(exc)
    print(json.dumps({'manifests':results,'records':records,'errors':errors},indent=2,ensure_ascii=False))
    return 0 if results else 2

if __name__=='__main__':
    raise SystemExit(main())

# Function deliberately not called from main; CI invokes this in the read-only
# "part headers" probe after the manifest shape is independently inspected.
def sample_headers():
    """Only read the first 32 bytes of two strictly confined official parts."""
    import re
    from urllib.parse import urljoin, urlsplit
    result={}
    opener=urllib.request.build_opener(NoRedirect())
    for kind in URLS:
        data=retrieve(kind,opener=opener)
        entries=[data] if kind=='exe' else data.get('patches', [])
        if not entries:continue
        part=entries[0]['parts'][0]
        relative=part['url']
        if not isinstance(relative,str) or not re.fullmatch(r'[A-Za-z0-9._/-]{1,200}',relative) or '..' in relative.split('/') or relative.startswith('/'):
            raise ProbeError('Unsafe official part path')
        url=urljoin(URLS[kind],relative)
        p=urlsplit(url)
        if p.scheme!='https' or p.hostname!='wow.aethus.pl' or not p.path.startswith('/exe/'):
            raise ProbeError('Part outside author domain')
        req=urllib.request.Request(url,headers={'Range':'bytes=0-31','User-Agent':'AZSE-Header-Only-Check/1.0'},method='GET')
        try:
            with opener.open(req,timeout=15) as response:
                head=response.read(32)
                result[kind]={'relative':relative,'status':response.status,
                    'content_type':response.headers.get('Content-Type'),
                    'encoding':response.headers.get('Content-Encoding'),
                    'hex_first_32_bytes':head.hex()}
        except (OSError,urllib.error.URLError,TimeoutError) as e:
            result[kind]={'error':type(e).__name__}
    print(json.dumps(result,indent=2))
    return 0 if result else 2
