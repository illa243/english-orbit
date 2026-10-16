import sys, json, urllib.request, urllib.error
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store
from capture import Bridge
import pytest

def test_bridge_auth_and_allowlist(tmp_path,monkeypatch):
    import capture
    server=capture.ThreadingHTTPServer
    monkeypatch.setattr(capture,"ThreadingHTTPServer",lambda address,handler:server((address[0],0),handler))
    store=Store(tmp_path/'bridge.sqlite');store.set('onboarded',True);store.set('capture',True)
    received=[];bridge=Bridge(store,lambda *x:received.append(x),lambda *x:None);bridge.start()
    try:
        def request(path,data=None,token=None,origin='chrome-extension://'+'a'*32):
            headers={'Content-Type':'application/json','Origin':origin}
            if token:headers['Authorization']='Bearer '+token
            return urllib.request.urlopen(urllib.request.Request(f'http://127.0.0.1:{bridge.server.server_port}'+path,data=json.dumps(data).encode() if data else None,headers=headers),timeout=3)
        with pytest.raises(urllib.error.HTTPError):request('/config')
        with pytest.raises(urllib.error.HTTPError):request('/config',token=bridge.token,origin='https://evil.example')
        assert json.load(request('/config',token=bridge.token))['enabled']
        with pytest.raises(urllib.error.HTTPError):request('/capture',{'url':'https://evil.example','text':'hello there','key':'1'},bridge.token)
        request('/capture',{'url':'https://chatgpt.com/c/x','text':'hello there','key':'1','final':True},bridge.token).close()
        assert received==[('1','chatgpt.com','hello there',True)]
        store.set('capture',False)
        request('/capture',{'url':'https://chatgpt.com','text':'not collected','key':'2'},bridge.token).close()
        assert len(received)==1
    finally:bridge.stop()
