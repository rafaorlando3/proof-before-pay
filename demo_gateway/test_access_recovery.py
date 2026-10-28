from pathlib import Path
import concurrent.futures,json,tempfile,unittest
from access_recovery import RecoveryStore
class RecoveryCodes(unittest.TestCase):
 def setUp(self):self.tmp=tempfile.TemporaryDirectory();self.root=Path(self.tmp.name);self.root.chmod(0o700);self.now=1000;self.store=RecoveryStore(self.root/'codes.json',lambda:self.now)
 def tearDown(self):self.tmp.cleanup()
 def test_only_digest_is_stored_and_code_is_single_use(self):
  code,expires=self.store.issue();self.assertEqual(expires,1900);self.assertNotIn(code,self.store.path.read_text());self.assertEqual(self.store.path.stat().st_mode&0o777,0o600);self.assertTrue(self.store.consume(code));self.assertFalse(self.store.consume(code))
 def test_expired_and_wrong_codes_do_not_consume_valid_code(self):
  code,_=self.store.issue();self.assertFalse(self.store.consume('PBP-'+'x'*32));self.assertIsNone(json.loads(self.store.path.read_text())['codes'][0]['used_at']);self.now=1900;self.assertFalse(self.store.consume(code))
 def test_only_one_of_concurrent_consumers_succeeds_and_result_survives_reload(self):
  code,_=self.store.issue()
  with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:results=list(pool.map(lambda _:RecoveryStore(self.store.path,lambda:1000).consume(code),range(8)))
  self.assertEqual(results.count(True),1);self.assertFalse(RecoveryStore(self.store.path,lambda:1000).consume(code))
 def test_unsafe_directory_state_or_corrupt_state_fails_closed(self):
  self.root.chmod(0o755)
  with self.assertRaises(ValueError):self.store.issue()
  self.root.chmod(0o700);code,_=self.store.issue();self.store.path.chmod(0o644)
  with self.assertRaises(ValueError):self.store.consume(code)
  self.store.path.chmod(0o600);self.store.path.write_text('{"version":1,"codes":[{"digest":"invalid"}]}')
  with self.assertRaises(ValueError):self.store.consume(code)
 def test_symlink_state_is_refused_and_records_are_not_silently_pruned(self):
  actual=self.root/'actual.json';actual.write_text('{}');actual.chmod(0o600);self.store.path.symlink_to(actual)
  with self.assertRaises(ValueError):self.store.issue()
  self.store.path.unlink()
  for _ in range(64):self.store.issue()
  with self.assertRaises(ValueError):self.store.issue()
  self.assertEqual(len(json.loads(self.store.path.read_text())['codes']),64)
 def test_operator_CLI_works_under_isolated_Python_and_never_prints_the_secret(self):
  import subprocess,sys
  invitation=self.root/'invitation.json';cmd=[sys.executable,'-I','-B',str(Path(__file__).with_name('access_recovery.py')),'issue',str(self.store.path),str(invitation)]
  result=subprocess.run(cmd,capture_output=True,text=True,check=True);d=json.loads(invitation.read_text());self.assertNotIn(d['code'],result.stdout+result.stderr);self.assertEqual(invitation.stat().st_mode&0o777,0o600)
  again=subprocess.run(cmd,capture_output=True,text=True);self.assertNotEqual(again.returncode,0);self.assertEqual(json.loads(invitation.read_text()),d)
 def test_server_imports_owned_helper_with_isolated_Python(self):
  import subprocess,sys
  p=Path(__file__).with_name('server.py').resolve();result=subprocess.run([sys.executable,'-I','-B','-c',"import runpy,sys; assert 'RecoveryStore' in runpy.run_path(sys.argv[1],run_name='isolated_gateway_test')",str(p)],capture_output=True,text=True);self.assertEqual(result.returncode,0,result.stderr)
if __name__=='__main__':unittest.main()
