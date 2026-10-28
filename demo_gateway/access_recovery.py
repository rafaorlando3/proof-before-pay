"""Operator-issued, short-lived, single-use VIEWER access recovery. No email or reset.

Secrets are written only to a private invitation file, never printed or placed in URLs.
The state holds digests; consumption is locked and atomically persisted before login.
"""
from pathlib import Path
from contextlib import contextmanager
import fcntl,hashlib,hmac,json,os,re,secrets,sys,time

class RecoveryStore:
    def __init__(self,path,clock=time.time):self.path=Path(path);self.clock=clock
    def secure_parent(self):
        p=self.path.parent
        if p.is_symlink() or not p.is_dir() or p.stat().st_mode&0o077 or p.stat().st_uid!=os.geteuid():raise ValueError('private_recovery_directory_required')
    @contextmanager
    def locked(self,create=False):
        self.secure_parent();lock=self.path.with_suffix('.lock')
        fd=os.open(lock,os.O_RDWR|os.O_NOFOLLOW|(os.O_CREAT if create else 0),0o600)
        try:
            if os.fstat(fd).st_mode&0o077 or os.fstat(fd).st_uid!=os.geteuid():raise ValueError('private_recovery_lock_required')
            fcntl.flock(fd,fcntl.LOCK_EX);yield
        finally:os.close(fd)
    def read(self,create=False):
        if not self.path.exists():
            if create:return {'version':1,'codes':[]}
            raise ValueError('recovery_not_provisioned')
        if self.path.is_symlink() or self.path.stat().st_mode&0o077 or self.path.stat().st_uid!=os.geteuid():raise ValueError('private_recovery_state_required')
        d=json.loads(self.path.read_text())
        if type(d.get('version')) is not int or d.get('version')!=1 or not isinstance(d.get('codes'),list) or len(d['codes'])>64:raise ValueError('invalid_recovery_state')
        for r in d['codes']:
            if set(r)!={'digest','expires_at','used_at'} or not isinstance(r['digest'],str) or not re.fullmatch('[0-9a-f]{64}',r['digest']) or type(r['expires_at']) is not int or (r['used_at'] is not None and type(r['used_at']) is not int):raise ValueError('invalid_recovery_record')
        return d
    def write(self,d):
        tmp=self.path.with_name('.recovery-'+secrets.token_hex(8)+'.tmp')
        fd=os.open(tmp,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
        try:
            with os.fdopen(fd,'w') as f:json.dump(d,f);f.flush();os.fsync(f.fileno())
            os.replace(tmp,self.path)
            parent=os.open(self.path.parent,os.O_RDONLY)
            try:os.fsync(parent)
            finally:os.close(parent)
        finally:
            if tmp.exists():tmp.unlink()
    def issue(self):
        code='PBP-'+secrets.token_urlsafe(24);expires=int(self.clock())+900
        with self.locked(create=True):
            d=self.read(create=True)
            if len(d['codes'])>=64:raise ValueError('recovery_history_limit_operator_review_required')
            d['codes'].append({'digest':hashlib.sha256(code.encode()).hexdigest(),'expires_at':expires,'used_at':None});self.write(d)
        return code,expires
    def consume(self,code):
        if not isinstance(code,str) or not re.fullmatch(r'PBP-[A-Za-z0-9_-]{32}',code):return False
        digest=hashlib.sha256(code.encode()).hexdigest();now=int(self.clock())
        with self.locked():
            d=self.read();match=None
            for r in d['codes']:
                if hmac.compare_digest(r['digest'],digest):match=r
            if match is None or match['used_at'] is not None or now>=match['expires_at']:return False
            match['used_at']=now;self.write(d);return True

def main():
    if len(sys.argv)!=4 or sys.argv[1]!='issue':raise SystemExit('Usage: access_recovery.py issue PRIVATE_STATE_PATH PRIVATE_INVITATION_PATH')
    store=RecoveryStore(sys.argv[2]);out=Path(sys.argv[3]);store.secure_parent()
    if out.parent.is_symlink() or out.parent.stat().st_mode&0o077:raise ValueError('private_invitation_directory_required')
    fd=os.open(out,os.O_WRONLY|os.O_CREAT|os.O_EXCL|os.O_NOFOLLOW,0o600)
    try:
        code,expires=store.issue()
        with os.fdopen(fd,'w') as f:json.dump({'code':code,'expires_at':expires,'scope':'consultation-only demo viewer; single use; shared password unchanged'},f);f.write('\n');f.flush();os.fsync(f.fileno())
    except Exception:
        try:os.close(fd)
        except OSError:pass
        out.unlink(missing_ok=True);raise
    print('Recovery invitation written to the requested private file. Expires in15minutes; single use; viewer only.')
if __name__=='__main__':main()
