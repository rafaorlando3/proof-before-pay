import copy,unittest
from restore_route import reconcile
class RouteRecovery(unittest.TestCase):
 def setUp(self):
  self.own={'@id':'pbp49-demo36','match':[{'host':['demo.example']}],'handle':[{'handler':'reverse_proxy','upstreams':[{'dial':'127.0.0.1:18879'}]}],'terminal':True};self.routes=[{'match':[{'host':['other.example']}],'terminal':True}];self.posts=[]
 def get(self):return copy.deepcopy(self.routes),'known-etag'
 def append(self,route,etag):self.assertEqual(etag,'known-etag');self.posts.append(route);self.routes.append(copy.deepcopy(route))
 def test_missing_route_is_appended_with_ETag_and_all_old_routes_retained(self):
  before=copy.deepcopy(self.routes);self.assertEqual(reconcile(self.own,self.get,self.append),'restored_one_route');self.assertEqual(self.routes[:-1],before);self.assertEqual(len(self.posts),1)
 def test_already_present_causes_no_mutation(self):
  self.routes.append(copy.deepcopy(self.own));self.assertEqual(reconcile(self.own,self.get,self.append),'already_present');self.assertEqual(self.posts,[])
 def test_conflicting_id_or_host_is_never_overwritten(self):
  for conflicting in [dict(self.own,terminal=False),{'match':self.own['match'],'terminal':True}]:
   self.routes=[conflicting]
   with self.assertRaises(ValueError):reconcile(self.own,self.get,self.append)
  self.assertEqual(self.posts,[])
 def test_unknown_POST_outcome_is_recovered_by_GET_without_resend(self):
  def append(route,etag):self.append(route,etag);raise TimeoutError()
  self.assertEqual(reconcile(self.own,self.get,append),'present_after_uncertain_response');self.assertEqual(len(self.posts),1)
 def test_failed_conditional_POST_does_not_retry_or_load_full_config(self):
  def append(route,etag):self.posts.append(route);raise RuntimeError('412')
  with self.assertRaises(RuntimeError):reconcile(self.own,self.get,append)
  self.assertEqual(len(self.posts),1);self.assertEqual(len(self.routes),1)
 def test_nonloopback_or_broader_route_is_refused_before_any_call(self):
  for route in [dict(self.own,handle=[{'handler':'reverse_proxy','upstreams':[{'dial':'external.example:443'}]}]),dict(self.own,terminal=False),dict(self.own,match=[{'host':['one','two']}])]:
   with self.assertRaises(ValueError):reconcile(route,self.get,self.append)
  self.assertEqual(self.posts,[])
if __name__=='__main__':unittest.main()
