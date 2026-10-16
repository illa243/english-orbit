"""Session lifecycle survives closing Settings; transient errors retain saved sessions."""
import time
from PySide6.QtCore import QObject,Signal,QTimer
from providers import PROVIDERS,discover,login,logout
class Accounts(QObject):
    changed=Signal(str)
    def __init__(self,owner):
        super().__init__(owner);self.owner=owner;self.store=owner.store;self.busy=set();self.pending={};self.errors={};self.processes={}
        self.timer=QTimer(self);self.timer.setInterval(5000);self.timer.timeout.connect(self.poll)
    def refresh(self,p,after=None):
        if p in self.busy:return
        self.busy.add(p);self.errors.pop(p,None);self.changed.emit(p)
        def done(info):
            self.busy.discard(p);self.store.set('provider_'+p,info)
            if info.get('connected'):self.pending.pop(p,None)
            self.changed.emit(p)
            if after:after(info)
        def failed(error):
            self.busy.discard(p);self.errors[p]=error;self.changed.emit(p)
        self.owner.work(lambda:discover(p),done,failed)
    def connect(self,p):
        if p in self.busy or p in self.pending:return
        # Check the persisted official session before opening any sign-in UI.
        def checked(info):
            if info.get('connected'):return
            try:self.processes[p]=login(p);self.pending[p]=time.monotonic()+900;self.timer.start();self.changed.emit(p)
            except Exception as e:self.errors[p]=str(e);self.changed.emit(p)
        self.refresh(p,checked)
    def poll(self):
        for p,deadline in list(self.pending.items()):
            if time.monotonic()>deadline:
                self.pending.pop(p,None);self.errors[p]='Час очікування входу минув. Можна спробувати ще раз.';self.changed.emit(p)
            else:self.refresh(p)
        if not self.pending:self.timer.stop()
    def logout(self,p):
        if p in self.busy:return
        if self.owner.workers:self.errors[p]='Дочекайтеся завершення поточних запитів.';self.changed.emit(p);return
        self.busy.add(p);self.changed.emit(p)
        def done(_):
            self.busy.discard(p);self.pending.pop(p,None);self.errors.pop(p,None);self.store.set('provider_'+p,{'connected':False,'models':[],'status':'Ви вийшли з акаунту.'});self.changed.emit(p)
        def failed(e):self.busy.discard(p);self.errors[p]=e;self.changed.emit(p)
        self.owner.work(lambda:logout(p),done,failed)
