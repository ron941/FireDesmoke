import os,time
from firedesmoke.demo import RequestStore

def test_expiry_isolated_active_requests(tmp_path):
    store=RequestStore(tmp_path,ttl=10)
    a=store.new();b=store.new()
    assert a!=b
    store.finish(a)
    old=time.time()-20
    os.utime(a,(old,old));os.utime(b,(old,old))
    store.cleanup()
    assert not a.exists() and b.exists()
    store.finish(b);os.utime(b,(old,old));store.cleanup()
    assert not b.exists()
