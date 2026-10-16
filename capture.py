"""Opt-in final-text capture, never a keylogger. Chrome bridge binds loopback only."""
import os, ctypes, threading, time, json, secrets, re
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import psutil
from PySide6.QtCore import QThread, Signal

def idle_seconds():
    if os.name!='nt':return 999
    class LASTINPUTINFO(ctypes.Structure):_fields_=[('cbSize',ctypes.c_uint),('dwTime',ctypes.c_uint)]
    info=LASTINPUTINFO();info.cbSize=ctypes.sizeof(info)
    if ctypes.windll.user32.GetLastInputInfo(ctypes.byref(info)):
        return ((ctypes.windll.kernel32.GetTickCount() & 0xffffffff)-info.dwTime & 0xffffffff)/1000
    return 0

def host_allowed(url,sites):
    host=(urlparse(url).hostname or '').lower()
    return any(host==s.strip().lower() or host.endswith('.'+s.strip().lower()) for s in sites if s.strip())

def english_layout():
    if os.name!='nt':return True
    user=ctypes.windll.user32;user.GetForegroundWindow.restype=ctypes.c_void_p
    tid=user.GetWindowThreadProcessId(ctypes.c_void_p(user.GetForegroundWindow()),None)
    return (user.GetKeyboardLayout(tid)&0x3ff)==9

class NativeCapture(QThread):
    captured=Signal(str,str,str,bool)
    selected=Signal(str,str)
    health=Signal(str)
    def __init__(self,store):super().__init__();self.store=store;self.running=True;self.last=None;self.hot_down=set()
    def run(self):
        if os.name!='nt':return
        import uiautomation as auto
        user=ctypes.windll.user32
        user.GetForegroundWindow.restype=ctypes.c_void_p
        with auto.UIAutomationInitializerInThread():
            auto.SetGlobalSearchTimeout(.3)
            self.health.emit('Збір готовий · Ctrl+Alt+S — текст · Ctrl+Alt+W — слово')
            while self.running:
                try:
                    # Only two explicit hotkeys are observed, no character stream is recorded.
                    modifier=bool(user.GetAsyncKeyState(0x11)&0x8000) and bool(user.GetAsyncKeyState(0x12)&0x8000)
                    for vk,kind in ((0x53,'text'),(0x57,'word')):
                        pressed=modifier and bool(user.GetAsyncKeyState(vk)&0x8000)
                        if pressed and vk not in self.hot_down:
                            self.hot_down.add(vk);text=''
                            try:
                                focus=auto.GetFocusedControl()
                                if focus and not focus.IsPassword:
                                    pattern=focus.GetTextPattern()
                                    if pattern:text=''.join(r.GetText(-1) for r in pattern.GetSelection())
                            except Exception:pass
                            self.selected.emit(kind,text[:50000])
                        if not pressed:self.hot_down.discard(vk)
                    if not self.store.get('onboarded') or not self.store.get('capture'):
                        time.sleep(.4);continue
                    hwnd=user.GetForegroundWindow();pid=ctypes.c_ulong()
                    tid=user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd),ctypes.byref(pid))
                    if pid.value==os.getpid():time.sleep(.4);continue
                    process=psutil.Process(pid.value).name().lower()
                    if process in ('chrome.exe','msedge.exe','firefox.exe'):time.sleep(.4);continue
                    all_apps=self.store.get('listen_all')
                    if not all_apps and process not in [x.lower() for x in self.store.get('apps',[])]:time.sleep(.4);continue
                    if all_apps and (user.GetKeyboardLayout(tid)&0x3ff)!=9:time.sleep(.4);continue
                    control=auto.GetFocusedControl()
                    if not control or control.IsPassword:time.sleep(.4);continue
                    if control.ControlType not in (auto.ControlType.EditControl,auto.ControlType.DocumentControl):time.sleep(.4);continue
                    text=None
                    value=control.GetValuePattern()
                    if value and not value.IsReadOnly:text=value.Value
                    elif control.ControlType==auto.ControlType.EditControl:
                        pattern=control.GetTextPattern()
                        if pattern:text=pattern.DocumentRange.GetText(-1)
                    if text is not None and len(text)<=50000:
                        rid=':'.join(map(str,control.GetRuntimeId()))
                        key=f'native:{pid.value}:{hwnd}:{rid}'
                        current=(key,text)
                        if current!=self.last:
                            self.captured.emit(key,process,text,False);self.last=current
                except (psutil.Error,Exception):pass
                time.sleep(.45)
    def stop(self):self.running=False

class Bridge:
    def __init__(self,store,callback,selection):
        self.store=store;self.callback=callback;self.selection=selection;self.server=None
        self.token=store.get('bridge_token')
        if not self.token:self.token=secrets.token_urlsafe(32);store.set('bridge_token',self.token)
    def start(self):
        bridge=self
        class Handler(BaseHTTPRequestHandler):
            def log_message(self,*args):pass
            def origin_ok(self):
                origin=self.headers.get('Origin','')
                return not origin or bool(re.fullmatch(r'chrome-extension://[a-p]{32}',origin))
            def reply(self,status,obj):
                data=json.dumps(obj).encode();self.send_response(status)
                origin=self.headers.get('Origin','')
                if self.origin_ok() and origin:self.send_header('Access-Control-Allow-Origin',origin)
                self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(data)));self.end_headers();self.wfile.write(data)
            def do_OPTIONS(self):
                if not self.origin_ok():self.reply(403,{});return
                self.send_response(204);self.send_header('Access-Control-Allow-Origin',self.headers.get('Origin',''))
                self.send_header('Access-Control-Allow-Headers','Authorization,Content-Type');self.send_header('Access-Control-Allow-Methods','GET,POST,OPTIONS');self.end_headers()
            def authorized(self):
                return self.origin_ok() and secrets.compare_digest(self.headers.get('Authorization',''),'Bearer '+bridge.token)
            def do_GET(self):
                if not self.authorized():self.reply(403,{'error':'Pairing required'});return
                if self.path!='/config':self.reply(404,{});return
                self.reply(200,{'enabled':bridge.store.get('onboarded') and bridge.store.get('capture'), 'sites':bridge.store.get('sites'), 'all':bridge.store.get('listen_all')})
            def do_POST(self):
                if not self.authorized():self.reply(403,{});return
                try:
                    size=int(self.headers.get('Content-Length','0'))
                    if not 0<size<=250000:self.reply(413,{});return
                    data=json.loads(self.rfile.read(size));text=data.get('text','')
                    if not isinstance(text,str) or len(text)>50000:raise ValueError()
                    if self.path=='/capture':
                        if not bridge.store.get('capture') or not bridge.store.get('onboarded'):self.reply(200,{'ignored':True});return
                        if bridge.store.get('listen_all') and not english_layout():self.reply(200,{'ignored':True});return
                        if not bridge.store.get('listen_all') and not host_allowed(data.get('url',''),bridge.store.get('sites',[])):self.reply(403,{});return
                        bridge.callback(str(data.get('key',''))[:500],urlparse(data.get('url','')).hostname or 'Chrome',text,bool(data.get('final')))
                    elif self.path in ('/word','/manual'):
                        bridge.selection('word' if self.path=='/word' else 'text',text)
                    else:self.reply(404,{});return
                    self.reply(200,{'ok':True})
                except Exception:self.reply(400,{'error':'Invalid payload'})
        self.server=ThreadingHTTPServer(('127.0.0.1',18743),Handler)
        threading.Thread(target=self.server.serve_forever,daemon=True).start()
    def stop(self):
        if self.server:self.server.shutdown();self.server.server_close()
