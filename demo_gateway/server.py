"""Authenticated, case-scoped viewer for a live IRIS demo. No intake or review route.
Run behind HTTPS; the upstream is an existing private authenticated loopback relay.
The only permitted POST verifies an editable copy, without changing stored data.
"""
from dataclasses import dataclass, field
from pathlib import Path
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import base64, hmac, json, re, sys, threading, time, secrets, urllib.request, urllib.parse, urllib.error
from http.cookies import SimpleCookie, CookieError

MAX_BODY = 32000
@dataclass
class Config:
    username: str
    password: str = field(repr=False)
    case_ids: tuple[str, ...] = ()
    origin: str = ''
    backend: str = 'http://127.0.0.1:18878'
    def __post_init__(self):
        if not self.username or ':' in self.username or len(self.password) < 32 or self.password.startswith('GENERATE_'):
            raise ValueError('dedicated_random_demo_credentials_required')
        if not self.case_ids or len(set(self.case_ids)) != len(self.case_ids):
            raise ValueError('explicit_unique_case_allowlist_required')
        u = urllib.parse.urlsplit(self.backend)
        if u.scheme != 'http' or u.hostname not in {'127.0.0.1', 'localhost'} or u.username or u.password or u.path or u.query or u.fragment:
            raise ValueError('loopback_relay_required')
        u = urllib.parse.urlsplit(self.origin)
        if u.scheme != 'https' or not u.netloc or u.path or u.username or u.password or u.query or u.fragment:
            raise ValueError('public_HTTPS_origin_required')
    @classmethod
    def load(cls, path):
        p = Path(path)
        if p.stat().st_mode & 0o077:
            raise ValueError('private_config_must_be_0600')
        d = json.loads(p.read_text())
        return cls(d['username'], d['password'], tuple(d['case_ids']), d['origin'], d.get('backend', 'http://127.0.0.1:18878'))

class Gateway:
    def __init__(self, config, fetch=None):
        self.config = config
        self.fetch = fetch or self._fetch
        self.sessions = {}
        self.failed_logins = []
        self.session_lock = threading.Lock()
    def _fetch(self, path, method='GET', body=None):
        req = urllib.request.Request(self.config.backend + path, data=body, method=method,
              headers={'Content-Type':'application/json', 'X-PBP-Request':'1'})
        try:response=urllib.request.urlopen(req,timeout=12)
        except urllib.error.HTTPError as exc:
            if exc.code not in {400,403,404,405,409,413,422}:raise
            response=exc
        with response as r:
            raw = r.read(2_000_001)
            if len(raw)>2_000_000: raise ValueError('upstream_response_too_large')
            return r.status, r.headers.get('Content-Type','application/json'), raw
    def authorized(self, headers):
        expected = 'Basic ' + base64.b64encode((self.config.username+':'+self.config.password).encode()).decode()
        if hmac.compare_digest(headers.get('Authorization','').encode(), expected.encode()):return True
        try:
            cookie=SimpleCookie();cookie.load(headers.get('Cookie',''));token=cookie['pbp49_viewer'].value
        except (KeyError,ValueError,CookieError):return False
        with self.session_lock:return self.sessions.get(token,0)>time.monotonic()
    def login(self, method, headers, body):
        if method=='GET':
            page='''<!doctype html><html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Proof Before Pay | Demo access</title><style>body{margin:0;background:#09111e;color:#dfebf7;font:16px system-ui;display:grid;min-height:100vh;place-items:center}main{max-width:420px;padding:36px;border:1px solid #284153;border-radius:22px;background:#101e2e}small{color:#60dec6;letter-spacing:.1em}h1{font-size:34px;margin-bottom:12px}p{color:#aebfd0;line-height:1.6}label{display:block;margin-top:20px}input,button{box-sizing:border-box;width:100%;padding:13px;margin-top:8px;border-radius:10px;border:1px solid #33516b;background:#091523;color:#fff;font:inherit}button{margin-top:26px;background:#62ddc8;color:#06211e;font-weight:700;cursor:pointer}footer{font-size:12px;color:#91aabd;margin-top:24px}</style><main><small>INTERSYSTEMS IRIS / WORKING DEMO</small><h1>Proof Before Pay</h1><p>Inspect real evidence, sealed decisions and a synthetic receipt on the running IRIS backend.</p><form method="post" action="/pbp/login"><label>Viewer name<input name="username" autocomplete="username" required maxlength="100"></label><label>Access password<input name="password" type="password" autocomplete="current-password" required maxlength="200"></label><button type="submit">Open the demo</button></form><footer>Recorded agent responses. Synthetic funds. Consultation only; approval and model calls are disabled.</footer></main></html>'''
            return 200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store','Content-Security-Policy':"default-src 'none'; style-src 'unsafe-inline'; form-action 'self'; base-uri 'none'; frame-ancestors 'none'"},page.encode()
        if method!='POST':return self.fail('method_not_allowed',405)
        if headers.get('Origin')!=self.config.origin or headers.get('Content-Type','').split(';')[0]!='application/x-www-form-urlencoded':return self.fail('same_origin_form_required',403)
        if len(body)>1024:return self.fail('input_too_large',413)
        try:
            fields=urllib.parse.parse_qs(body.decode('utf-8'),strict_parsing=True,max_num_fields=2)
            user,=fields['username'];password,=fields['password']
        except (ValueError,KeyError,UnicodeError):return self.fail('invalid_login_form',400)
        now=time.monotonic()
        with self.session_lock:
            self.failed_logins[:]=[t for t in self.failed_logins if now-t<60]
            if len(self.failed_logins)>=20:return self.fail('login_rate_limited_try_later',429)
            if not (hmac.compare_digest(user.encode(),self.config.username.encode()) and hmac.compare_digest(password.encode(),self.config.password.encode())):
                self.failed_logins.append(now);return self.fail('viewer_credentials_not_accepted',401)
            self.sessions={k:v for k,v in self.sessions.items() if v>now}
            if len(self.sessions)>=32:return self.fail('viewer_session_limit_try_later',429)
            token=secrets.token_urlsafe(32);self.sessions[token]=now+3600
        return 303,{'Location':'/pbp/ui/','Cache-Control':'no-store','Set-Cookie':'pbp49_viewer='+token+'; Path=/; HttpOnly; Secure; SameSite=Strict; Max-Age=3600'},b''
    @staticmethod
    def response(obj, status=200):
        return status, {'Content-Type':'application/json; charset=utf-8','Cache-Control':'no-store'}, json.dumps(obj,ensure_ascii=False).encode()
    def fail(self, reason, status): return self.response({'ok':False,'reason':reason},status)
    def document(self, path):
        status,kind,raw=self.fetch(path)
        if status!=200: raise ValueError('upstream_rejected')
        obj=json.loads(raw)
        if obj.get('ok') is not True: raise ValueError('upstream_not_ok')
        return obj
    def one_case(self,cid):
        d=self.document('/pbp/api/cases/'+urllib.parse.quote(cid,safe=''))
        if d['case']['case_id']!=cid or d['case'].get('input',{}).get('environment')!='sandbox':
            raise ValueError('public_case_identity_or_environment_mismatch')
        if d['decision'].get('model',{}).get('mode')!='recorded':
            raise ValueError('public_case_must_be_recorded')
        return d
    def details(self):return [self.one_case(cid) for cid in self.config.case_ids]
    def dispatch(self, method, target, headers, body=b''):
        if target=='/pbp/login':return self.login(method,headers,body)
        if not self.authorized(headers):
            if method=='GET' and target in {'/','/pbp/ui/','/pbp/ui/index.html'}:return 303,{'Location':'/pbp/login','Cache-Control':'no-store'},b''
            status,h,b=self.fail('demo_authentication_required',401);h['WWW-Authenticate']='Basic realm="Proof Before Pay demo", charset="UTF-8"';return status,h,b
        p=urllib.parse.urlsplit(target)
        if p.scheme or p.netloc or p.fragment or len(target)>2048: return self.fail('route_not_available',404)
        path=urllib.parse.unquote(p.path)
        if '%' in path or '..' in path.split('/') or '\\' in path or '\x00' in path: return self.fail('route_not_available',404)
        if method not in {'GET','POST'}: return self.fail('read_only_demo',405)
        if method=='POST':
            if len(body)>MAX_BODY: return self.fail('input_too_large',413)
            if headers.get('Origin')!=self.config.origin or headers.get('X-PBP-Request')!='1' or headers.get('Content-Type','').split(';')[0]!='application/json':
                return self.fail('same_origin_JSON_required',403)
            if not re.fullmatch(r'/pbp/api/seals/[0-9a-f]{64}/verify',path): return self.fail('read_only_demo',405)
        elif path=='/': return 302,{'Location':'/pbp/ui/','Cache-Control':'no-store'},b''
        try:
            if method=='GET' and path in {'/pbp/ui/','/pbp/ui/index.html'}:
                status,kind,raw=self.fetch('/pbp/ui/')
                if status!=200 or 'text/html' not in kind: return self.fail('upstream_unavailable',502)
                banner='<aside style="position:fixed;bottom:0;left:0;right:0;z-index:25;padding:8px 16px;background:#111b2b;color:#dce8f5;font:12px system-ui;text-align:center">Authenticated demo. Live IRIS backend. Recorded responses. Synthetic funds. Review disabled. Counters cover only the selected demo cases.</aside>'
                return 200,{'Content-Type':'text/html; charset=utf-8','Cache-Control':'no-store'},raw.replace(b'</body>',banner.encode()+b'</body>')
            if method=='GET' and path=='/pbp/api/health':
                d=self.document('/pbp/api/health')
                if d.get('mode')!='recorded':return self.fail('demo_configuration_mismatch',503)
                return self.response({k:d[k] for k in ['ok','production_running','mode','spec','time'] if k in d})
            if method=='GET' and path=='/pbp/api/whoami':return self.response({'ok':True,'user':'Demo viewer','can_review':False})
            if method=='GET' and path=='/pbp/api/review':return self.response({'ok':True,'user':'Demo viewer','can_review':False,'pending':[]})
            if method=='GET' and path in {'/pbp/api/cases','/pbp/api/stats'}:
                docs=self.details()
                if path.endswith('/cases'):return self.response({'ok':True,'cases':[d['case'] for d in docs],'scope':'selected_public_demo_cases'})
                status_counts={};seals=effects=0;recorded=0
                for d in docs:
                    st=d['case']['status'];status_counts[st]=status_counts.get(st,0)+1;seals+=len(d.get('seals',[]));recorded+=d['decision'].get('source')=='model';rc=d.get('receipt');effects+=bool(isinstance(rc,dict) and rc.get('status')=='effected' and rc.get('verification')=='intact')
                return self.response({'ok':True,'cases_by_status':status_counts,'seals':seals,'effects':effects,'model_decisions_by_mode':{'live':{'decisions':0},'recorded':{'decisions':recorded},'unknown':{'decisions':0}},'scope':'selected_public_demo_cases','usage_cost_basis':'recorded_demo_no_new_model_calls'})
            if path.startswith('/pbp/api/cases/'):
                suffix=path.removeprefix('/pbp/api/cases/');cid=suffix.removesuffix('/replay')
                if method!='GET' or cid not in self.config.case_ids:return self.fail('case_not_in_demo',404)
                d=self.one_case(cid)
                if suffix.endswith('/replay'):return self.fetch_response('/pbp/api/cases/'+urllib.parse.quote(cid,safe='')+'/replay')
                return self.response(d)
            match=re.fullmatch(r'/pbp/api/(seals|ledger)/([0-9a-f]{64})(/verify)?',path)
            if match:
                kind,commitment,verify=match.groups();allowed={s['commitment'] for d in self.details() for s in d.get('seals',[])}
                if commitment not in allowed:return self.fail('seal_not_in_demo',404)
                if method=='POST' and (kind!='seals' or verify!='/verify'):return self.fail('read_only_demo',405)
                if method=='GET' and verify:return self.fail('method_not_allowed',405)
                return self.fetch_response(path,method,body if method=='POST' else None)
            return self.fail('route_not_available',404)
        except Exception:return self.fail('upstream_unavailable',502)
    def fetch_response(self,path,method='GET',body=None):
        status,kind,raw=self.fetch(path,method,body)
        return status,{'Content-Type':kind,'Cache-Control':'no-store'},raw

def serve(config, port=18879):
    gateway=Gateway(config)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):pass
        def handle_request(self):
            body=b''
            if self.command=='POST':
                if self.path!='/pbp/login' and not gateway.authorized(self.headers):result=gateway.dispatch(self.command,self.path,self.headers);return self.finish_response(result)
                if self.headers.get('Transfer-Encoding'):return self.finish_response(gateway.fail('transfer_encoding_not_supported',400))
                try:n=int(self.headers.get('Content-Length','-1'))
                except ValueError:return self.finish_response(gateway.fail('invalid_length',400))
                if n<0 or n>MAX_BODY:return self.finish_response(gateway.fail('input_too_large',413))
                self.connection.settimeout(10);body=self.rfile.read(n)
                if len(body)!=n:return self.finish_response(gateway.fail('incomplete_body',400))
            self.finish_response(gateway.dispatch(self.command,self.path,self.headers,body))
        def finish_response(self,result):
            status,headers,raw=result;self.send_response(status)
            for k,v in headers.items():self.send_header(k,v)
            # same-origin retains Origin on ordinary login forms while never
            # sending a Referer to another origin. no-referrer makes form Origin null.
            self.send_header('X-Content-Type-Options','nosniff');self.send_header('Referrer-Policy','same-origin');self.send_header('X-Frame-Options','DENY');self.send_header('Content-Length',str(len(raw)));self.end_headers()
            if self.command!='HEAD':self.wfile.write(raw)
        do_GET=do_POST=do_HEAD=do_PUT=do_DELETE=do_PATCH=do_OPTIONS=do_TRACE=do_CONNECT=handle_request
    class BoundedServer(ThreadingHTTPServer):
        daemon_threads=True
        slots=threading.BoundedSemaphore(12)
        def process_request(self,request,address):
            if not self.slots.acquire(blocking=False):request.close();return
            try:super().process_request(request,address)
            except BaseException:self.slots.release();raise
        def process_request_thread(self,request,address):
            try:super().process_request_thread(request,address)
            finally:self.slots.release()
    BoundedServer(('127.0.0.1',port),Handler).serve_forever()
if __name__=='__main__':serve(Config.load(sys.argv[1]))
