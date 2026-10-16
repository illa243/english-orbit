import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication, QDialog
from core import Store
from ui import ProfileDialog, STYLE
from main import create_window

def application():
    app=QApplication.instance() or QApplication([])
    app.setStyleSheet(STYLE)
    return app

def test_cancel_first_login_never_constructs_main_window(tmp_path):
    app=application();store=Store(tmp_path/'cancel.sqlite');created=[]
    def dialog(**kwargs):
        d=ProfileDialog(**kwargs);QTimer.singleShot(0,d.close);return d
    result=create_window(store,dialog_factory=dialog,window_factory=lambda *a,**k:created.append(True))
    assert result is None and created==[]
    assert store.get('onboarded') is False and store.get('capture') is False

def test_accept_profile_constructs_main_only_after_save(tmp_path):
    app=application();store=Store(tmp_path/'accept.sqlite');events=[];sentinel=object()
    def dialog(**kwargs):
        d=ProfileDialog(**kwargs);d.name.setText('Learner')
        def save():
            assert events==[];d.save()
        QTimer.singleShot(0,save);return d
    def window(*args,**kwargs):
        assert store.get('onboarded') and store.get('name')=='Learner'
        events.append('window');return sentinel
    assert create_window(store,False,dialog,window) is sentinel
    assert events==['window']

def test_existing_profile_bypasses_login(tmp_path):
    app=application();store=Store(tmp_path/'existing.sqlite');store.set('onboarded',True)
    def dialog(**kwargs):raise AssertionError('Unexpected login')
    assert create_window(store,False,dialog,lambda *a,**k:'main')=='main'

def test_accepted_without_saved_profile_does_not_start_services(tmp_path):
    app=application();store=Store(tmp_path/'unsaved.sqlite')
    def dialog(**kwargs):
        d=ProfileDialog(**kwargs);QTimer.singleShot(0,d.accept);return d
    def window(*args,**kwargs):raise AssertionError('Main window must not exist')
    assert create_window(store,True,dialog,window) is None
