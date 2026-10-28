import base64, copy, importlib.util, json, unittest
from pathlib import Path
import sys
spec=importlib.util.spec_from_file_location('pbp_demo_gateway',Path(__file__).with_name('server.py'));m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
A='a'*64;B='b'*64;OTHER='c'*64
class Contract(unittest.TestCase):
 def setUp(self):
  self.c=m.Config('judge','test-only-not-a-real-password-value-0000',('demo:public',),'https://demo.example')
  self.headers={'Authorization':'Basic '+base64.b64encode((self.c.username+':'+self.c.password).encode()).decode()}
  self.calls=[];self.doc={'ok':True,'case':{'case_id':'demo:public','status':'closed','input':{'environment':'sandbox'}},'decision':{'source':'model','model':{'mode':'recorded'}},'seals':[{'commitment':A},{'commitment':B}],'receipt':{'status':'effected','verification':'intact'}}
  def fetch(path,method='GET',body=None):
   self.calls.append((method,path,body))
   if path.startswith('/pbp/api/cases/'):raw=json.dumps(self.doc).encode();kind='application/json'
   elif path=='/pbp/ui/':raw=b'<html><body>native UI</body></html>';kind='text/html'
   elif path=='/pbp/api/health':raw=json.dumps({'ok':True,'production_running':True,'mode':'recorded','spec':'pbp.seal/1','time':'now','key_variable':'NOT_PUBLIC'}).encode();kind='application/json'
   else:raw=b'{"ok":true}';kind='application/json'
   return 200,kind,raw
  self.g=m.Gateway(self.c,fetch)
 def call(self,method,path,headers=None,body=b''):return self.g.dispatch(method,path,self.headers if headers is None else headers,body)
 def test_auth_precedes_upstream_for_every_route(self):
  for method in ['GET','POST','HEAD','PUT','DELETE','OPTIONS']:
   self.assertEqual(self.call(method,'/pbp/api/cases',{})[0],401)
  self.assertEqual(self.calls,[])
 def test_review_intake_and_unknown_secrets_are_never_forwarded(self):
  for method,path in [('POST','/pbp/api/review/demo:public'),('POST','/pbp/api/cases'),('GET','/private/providers.env'),('GET','/csp/sys/'),('DELETE','/pbp/api/cases/demo:public')]:
   self.assertIn(self.call(method,path)[0],[403,404,405])
  self.assertEqual(self.calls,[])
 def test_case_allowlist_cannot_be_bypassed_with_encoding_or_traversal(self):
  for path in ['/pbp/api/cases/other','/pbp/api/cases/%64emo%253Apublic','/pbp/api/cases/demo:public/../other','https://elsewhere/pbp/api/cases','/pbp/api/cases/demo:public%00']:
   self.assertEqual(self.call('GET',path)[0],404)
  self.assertEqual(self.calls,[])
 def test_subset_counts_use_only_actual_allowed_case(self):
  status,_,raw=self.call('GET','/pbp/api/stats');d=json.loads(raw)
  self.assertEqual((status,d['cases_by_status'],d['seals'],d['effects']),(200,{'closed':1},2,1))
  self.assertEqual(d['model_decisions_by_mode']['live']['decisions'],0)
  self.assertEqual([x[1] for x in self.calls],['/pbp/api/cases/demo%3Apublic'])
 def test_changed_identity_environment_or_mode_fails_closed(self):
  for doc in [dict(self.doc,case={'case_id':'wrong','input':{'environment':'sandbox'}}),dict(self.doc,case={'case_id':'demo:public','input':{'environment':'production'}}),dict(self.doc,decision={'model':{'mode':'live'}})]:
   self.doc=doc;self.assertEqual(self.call('GET','/pbp/api/cases/demo:public')[0],502)
 def test_unlisted_seal_cannot_be_read_or_verified(self):
  self.assertEqual(self.call('GET','/pbp/api/seals/'+OTHER)[0],404)
  self.assertFalse(any('/seals/' in x[1] for x in self.calls))
 def test_verify_requires_same_origin_JSON_and_header(self):
  path='/pbp/api/seals/'+A+'/verify';body=b'{"record":{}}'
  self.assertEqual(self.call('POST',path,body=body)[0],403)
  h={**self.headers,'Origin':self.c.origin,'Content-Type':'application/json','X-PBP-Request':'1'}
  self.assertEqual(self.call('POST',path,{**h,'Origin':'https://evil.example'},body)[0],403)
  self.assertEqual(self.call('POST',path,h,b'x'*(m.MAX_BODY+1))[0],413)
  self.assertEqual(self.call('POST',path,h,body)[0],200)
  self.assertEqual(self.calls[-1],('POST',path,body))
 def test_viewer_cannot_claim_reviewer_capability(self):
  status,_,raw=self.call('GET','/pbp/api/whoami');self.assertEqual(status,200);self.assertIs(json.loads(raw)['can_review'],False);self.assertEqual(self.calls,[])
 def test_HTML_is_actual_upstream_with_scope_banner(self):
  status,_,raw=self.call('GET','/pbp/ui/');self.assertEqual(status,200);self.assertIn(b'native UI',raw);self.assertIn(b'Review disabled',raw)
 def test_health_never_exposes_provider_key_metadata(self):
  status,_,raw=self.call('GET','/pbp/api/health');self.assertEqual(status,200);self.assertNotIn(b'NOT_PUBLIC',raw);self.assertNotIn(b'key_variable',raw)
 def test_valid_upstream_copy_error_is_preserved(self):
  original=self.g.fetch
  def fetch(path,method='GET',body=None):
   if method=='POST':return 400,'application/json',b'{"ok":false,"reason":"body_must_contain_record"}'
   return original(path,method,body)
  self.g.fetch=fetch;h={**self.headers,'Origin':self.c.origin,'Content-Type':'application/json','X-PBP-Request':'1'}
  status,_,raw=self.call('POST','/pbp/api/seals/'+A+'/verify',h,b'{}');self.assertEqual(status,400);self.assertEqual(json.loads(raw)['reason'],'body_must_contain_record')
 def test_config_rejects_external_backend_and_nonHTTPS_origin(self):
  with self.assertRaises(ValueError):m.Config(self.c.username,self.c.password,self.c.case_ids,self.c.origin,'https://external.example')
  with self.assertRaises(ValueError):m.Config(self.c.username,self.c.password,self.c.case_ids,'http://demo.example')
 def login(self,origin=None,body=None):
  import urllib.parse
  h={'Origin':self.c.origin if origin is None else origin,'Content-Type':'application/x-www-form-urlencoded'}
  return self.call('POST','/pbp/login',h,body if body is not None else urllib.parse.urlencode({'username':self.c.username,'password':self.c.password}).encode())
 def test_browser_gets_login_form_without_access_to_IRIS(self):
  status,h,body=self.call('GET','/pbp/ui/',{});self.assertEqual((status,h['Location']),(303,'/pbp/login'))
  status,h,body=self.call('GET','/pbp/login',{});self.assertEqual(status,200);self.assertIn(b'type="password"',body);self.assertNotIn(self.c.password.encode(),body);self.assertEqual(self.calls,[])
 def test_login_cookie_is_secure_scoped_expiring_and_authorizes_only_viewer(self):
  status,h,_=self.login();self.assertEqual(status,303);self.assertIn('HttpOnly; Secure; SameSite=Strict; Max-Age=3600',h['Set-Cookie'])
  cookie=h['Set-Cookie'].split(';')[0];headers={'Cookie':cookie};status,_,raw=self.call('GET','/pbp/api/whoami',headers);self.assertEqual(status,200);self.assertFalse(json.loads(raw)['can_review'])
  self.assertEqual(self.call('POST','/pbp/api/review/demo:public',headers,b'{}')[0],403)
  token=cookie.split('=',1)[1];self.g.sessions[token]=0;self.assertEqual(self.call('GET','/pbp/api/whoami',headers)[0],401)
 def test_login_rejects_forgery_bad_forms_bad_credentials_and_rate_limits(self):
  self.assertEqual(self.login('https://evil.example')[0],403);self.assertEqual(self.login(body=b'username=a&username=b&password=c')[0],400)
  self.assertEqual(self.login(body=b'x'*1025)[0],413)
  for _ in range(20):self.assertEqual(self.login(body=b'username=judge&password=wrong')[1]['Location'],'/pbp/login?error=credentials')
  self.assertEqual(self.login()[1]['Location'],'/pbp/login?error=limited');self.assertEqual(self.g.sessions,{});self.assertEqual(self.calls,[])
 def test_forged_cookie_does_not_authorize(self):
  self.assertEqual(self.call('GET','/pbp/api/cases',{'Cookie':'pbp49_viewer=forged'})[0],401);self.assertEqual(self.calls,[])
 def test_expired_or_missing_session_never_sends_native_auth_challenge(self):
  for headers in [{},{'Cookie':'pbp49_viewer=expired'},{'Authorization':'Basic wrong'}]:
   for method,path in [('GET','/pbp/api/health'),('GET','/pbp/api/cases'),('POST','/pbp/api/cases'),('HEAD','/favicon.ico')]:
    status,h,_=self.call(method,path,headers);self.assertEqual(status,401);self.assertNotIn('WWW-Authenticate',h)
  self.assertEqual(self.calls,[])
 def test_login_errors_stay_inside_form_without_dialog_or_credential_echo(self):
  status,h,_=self.login(body=b'username=judge&password=wrong');self.assertEqual(status,303);self.assertEqual(h['Location'],'/pbp/login?error=credentials')
  status,h,body=self.call('GET',h['Location'],{});self.assertEqual(status,200);self.assertIn('text/html',h['Content-Type']);self.assertNotIn('WWW-Authenticate',h);self.assertIn(b'role="status"',body);self.assertIn(b'<form',body);self.assertNotIn(b'value="wrong"',body)
 def test_session_expired_message_is_on_login_page(self):
  status,h,body=self.call('GET','/pbp/login?expired=1',{});self.assertEqual(status,200);self.assertIn(b'Your session ended',body);self.assertNotIn('WWW-Authenticate',h)
 def test_live_UI_injects_same_origin_401_return_before_application_script(self):
  self.g.fetch=lambda *a:(200,'text/html',b'<html><body><script>APP()</script></body></html>')
  status,_,body=self.call('GET','/pbp/ui/');self.assertEqual(status,200);self.assertLess(body.index(b'originalFetch'),body.index(b'APP()'));self.assertIn(b"target.origin===location.origin",body);self.assertIn(b"location.replace('/pbp/login?expired=1')",body);self.assertNotIn(b'alert(',body);self.assertNotIn(b'prompt(',body);self.assertNotIn(b'confirm(',body)
 def test_sign_out_revokes_only_current_session_and_clears_private_cookie(self):
  _,one,_=self.login();_,two,_=self.login();a=one['Set-Cookie'].split(';')[0];b=two['Set-Cookie'].split(';')[0]
  status,h,_=self.call('POST','/pbp/logout',{'Origin':self.c.origin,'Cookie':a});self.assertEqual(status,303);self.assertIn('HttpOnly; Secure; SameSite=Strict; Max-Age=0',h['Set-Cookie']);self.assertEqual(self.call('GET','/pbp/api/whoami',{'Cookie':a})[0],401);self.assertEqual(self.call('GET','/pbp/api/whoami',{'Cookie':b})[0],200)
 def test_cross_origin_or_GET_cannot_end_a_session(self):
  _,h,_=self.login();cookie=h['Set-Cookie'].split(';')[0]
  for method,origin in [('GET',self.c.origin),('POST','https://evil.example')]:self.assertEqual(self.call(method,'/pbp/logout',{'Origin':origin,'Cookie':cookie})[0],403)
  self.assertEqual(self.call('GET','/pbp/api/whoami',{'Cookie':cookie})[0],200)
 def test_auth_page_has_recovery_navigation_and_no_native_dialog_calls(self):
  _,headers,body=self.call('GET','/pbp/login',{});self.assertIn(b'href="/pbp/recover"',body);self.assertIn("script-src 'sha256-",headers['Content-Security-Policy'])
  self.assertNotIn(b'{{',body)
  for forbidden in [b'alert(',b'prompt(',b'confirm(']:self.assertNotIn(forbidden,body)
 def test_recovery_uses_single_use_code_for_viewer_and_never_changes_password(self):
  import tempfile
  from access_recovery import RecoveryStore
  with tempfile.TemporaryDirectory() as tmp:
   p=Path(tmp);p.chmod(0o700);self.c.recovery_state=p/'recovery.json';store=RecoveryStore(self.c.recovery_state);code,_=store.issue();before=self.c.password
   import urllib.parse
   headers={'Origin':self.c.origin,'Content-Type':'application/x-www-form-urlencoded'};body=urllib.parse.urlencode({'code':code}).encode()
   status,h,_=self.call('POST','/pbp/recover',headers,body);self.assertEqual(status,303);self.assertEqual(h['Location'],'/pbp/ui/');cookie=h['Set-Cookie'].split(';')[0]
   _,_,who=self.call('GET','/pbp/api/whoami',{'Cookie':cookie});self.assertFalse(json.loads(who)['can_review']);self.assertEqual(before,self.c.password)
   self.assertEqual(self.call('POST','/pbp/recover',headers,body)[1]['Location'],'/pbp/recover?error=code')
 def test_recovery_cannot_be_cross_origin_or_disclose_code_in_redirect(self):
  headers={'Origin':'https://evil.example','Content-Type':'application/x-www-form-urlencoded'}
  self.assertEqual(self.call('POST','/pbp/recover',headers,b'code=test')[0],403)
  status,h,_=self.call('POST','/pbp/recover',{**headers,'Origin':self.c.origin},b'code=test');self.assertEqual(status,303);self.assertEqual(h['Location'],'/pbp/recover?error=unavailable');self.assertNotIn('Set-Cookie',h)
 def test_rate_limit_for_one_client_does_not_lock_out_another_client(self):
  import urllib.parse
  h={'Origin':self.c.origin,'Content-Type':'application/x-www-form-urlencoded'}
  for _ in range(20):self.g.dispatch('POST','/pbp/login',h,b'username=judge&password=wrong',client_id='clientA')
  good=urllib.parse.urlencode({'username':self.c.username,'password':self.c.password}).encode()
  self.assertEqual(self.g.dispatch('POST','/pbp/login',h,good,client_id='clientA')[1]['Location'],'/pbp/login?error=limited')
  self.assertEqual(self.g.dispatch('POST','/pbp/login',h,good,client_id='clientB')[1]['Location'],'/pbp/ui/')
 def test_forwarded_client_identity_is_only_accepted_from_loopback_proxy(self):
  self.assertEqual(m.client_key('127.0.0.1',{'X-Forwarded-For':'untrusted, 192.0.2.9'}),'192.0.2.9')
  self.assertEqual(m.client_key('192.0.2.3',{'X-Forwarded-For':'192.0.2.9'}),'192.0.2.3')
  self.assertEqual(m.client_key('127.0.0.1',{'X-Forwarded-For':'not-an-IP'}),'127.0.0.1')
if __name__=='__main__':unittest.main()
