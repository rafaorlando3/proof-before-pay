"""Restore one explicit demo route after a shared Caddy reload. Never load full config.

Run locally against Caddy's private admin endpoint. A supervisor/timer may retry
after failure, but every execution first reads state and never blindly resends POST.
"""
import json,re,sys,urllib.request
from pathlib import Path
ADMIN='http://127.0.0.1:2019/config/apps/http/servers/srv0/routes'
def validate(route):
    if set(route)!={'@id','match','handle','terminal'} or not re.fullmatch(r'pbp49-[a-z0-9-]+',route.get('@id','')):raise ValueError('explicit_demo_route_required')
    hosts=route.get('match')
    if not isinstance(hosts,list) or len(hosts)!=1 or set(hosts[0])!={'host'} or len(hosts[0]['host'])!=1 or not re.fullmatch(r'[A-Za-z0-9.-]+',hosts[0]['host'][0]):raise ValueError('single_explicit_host_required')
    if route['terminal'] is not True or route['handle']!=[{'handler':'reverse_proxy','upstreams':[{'dial':'127.0.0.1:18879'}]}]:raise ValueError('viewer_loopback_upstream_only')
def present(routes,desired):
    own=[x for x in routes if x.get('@id')==desired['@id']]
    if own:
        if own!=[desired]:raise ValueError('existing_demo_route_conflicts_do_not_overwrite')
        return True
    host=desired['match'][0]['host'][0]
    if any(host in m.get('host',[]) for x in routes for m in x.get('match',[])):raise ValueError('host_owned_by_another_route_do_not_overwrite')
    return False
def reconcile(desired,get,append):
    validate(desired);before,etag=get()
    if not isinstance(before,list):raise ValueError('existing_route_array_required')
    if present(before,desired):return 'already_present'
    if not etag:raise ValueError('ETag_required')
    try:append(desired,etag)
    except Exception:
        after,_=get()
        if present(after,desired):return 'present_after_uncertain_response'
        raise
    after,_=get()
    if not present(after,desired) or [x for x in after if x.get('@id')!=desired['@id']]!=before:raise ValueError('post_readback_or_original_route_guard_failed')
    return 'restored_one_route'
def main():
    desired=json.loads(Path(sys.argv[1]).read_text())
    def get():
        with urllib.request.urlopen(ADMIN,timeout=8) as r:return json.load(r),r.headers.get('ETag')
    def append(route,etag):
        q=urllib.request.Request(ADMIN,method='POST',data=json.dumps(route).encode(),headers={'Content-Type':'application/json','If-Match':etag})
        with urllib.request.urlopen(q,timeout=15) as r:
            if r.status!=200:raise ValueError('route_append_failed')
    print(reconcile(desired,get,append))
if __name__=='__main__':main()
