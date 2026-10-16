import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from PySide6.QtWidgets import QTabWidget,QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from test_ui import app,window
from settings_ui import SettingsDialog,Stepper

def test_sidebar_replaces_old_tabs(window,app):
    from PySide6.QtGui import QFontDatabase
    for f in ('segoeui.ttf','segoeuib.ttf'):QFontDatabase.addApplicationFont('C:/Windows/Fonts/'+f)
    d=SettingsDialog(window);d.show();app.processEvents()
    assert not d.findChildren(QTabWidget)
    assert d.pages.count()==4
    for index,b in enumerate(d.nav_buttons):
        b.click();app.processEvents();assert d.pages.currentIndex()==index
        assert sum(x.isChecked() for x in d.nav_buttons)==1
    d.resize(1000,650);app.processEvents()
    for index in range(4):
        d.select_page(index);app.processEvents()
        assert d.pages.currentWidget().horizontalScrollBar().maximum()==0,index
        assert d.save_button.isVisible()
    d.close()

def test_settings_round_trip(window,app):
    d=SettingsDialog(window);d.start.setCurrentIndex(d.start.findData(9));d.end.setCurrentIndex(d.end.findData(22));d.daily.setValue(4);d.reminders.setValue(2);d.dnd.setChecked(True);d.autostart.setChecked(False);d.enabled.setChecked(False);d.apps.setPlainText('Telegram.exe');d.sites.setPlainText('https://chatgpt.com/');d.save()
    s=window.store
    assert (s.get('hours_start'),s.get('hours_end'),s.get('daily_chats'),s.get('review_reminders'))==(9,22,4,2)
    assert s.get('dnd') and not s.get('autostart')
    assert s.get('apps')==['telegram.exe'] and s.get('sites')==['chatgpt.com']
    assert window.dnd_action.isChecked() and window.capture_action.isChecked()
    reopened=SettingsDialog(window);assert reopened.start.currentData()==9;assert reopened.daily.value()==4;reopened.close()

def test_cancel_and_invalid_schedule_do_not_save(window,app,monkeypatch):
    d=SettingsDialog(window);d.daily.setValue(8);d.reject();assert window.store.get('daily_chats')==2
    d=SettingsDialog(window);d.start.setCurrentIndex(d.start.findData(22));d.end.setCurrentIndex(d.end.findData(10));messages=[]
    monkeypatch.setattr(QMessageBox,'information',lambda *a:messages.append(a))
    d.save();assert messages and d.pages.currentIndex()==2;assert window.store.get('hours_start')==10;d.close()

def test_model_ids_and_switching_provider(window,app):
    window.store.set('provider_ChatGPT',{'connected':True,'models':[{'id':'model-a','name':'Model A'}]});window.store.set('model','model-a')
    d=SettingsDialog(window);assert d.model.currentData()=='model-a'
    d.provider.setCurrentText('Claude');assert d.model.currentData()==''
    d.provider.setCurrentText('ChatGPT');d.model.setCurrentIndex(d.model.findData('model-a'));d.save();assert window.store.get('model')=='model-a'

def test_refresh_updates_status_and_recovers_from_failure(window,app,monkeypatch):
    import accounts
    d=SettingsDialog(window)
    monkeypatch.setattr(accounts,'discover',lambda p:{'connected':True,'models':[{'id':'test-model'}],'status':'Підключено','plan':'Test plan','limits':None})
    window.work=lambda fn,done,fail:done(fn());d.refresh('ChatGPT')
    assert '1 моделей' in d.statuses['ChatGPT'].text();assert d.model.findData('test-model')>0
    assert d.plan_labels['ChatGPT'].text()=='Test plan'
    window.work=lambda fn,done,fail:fail('Connection failed');d.refresh('ChatGPT')
    assert d.refresh_buttons['ChatGPT'].isEnabled();assert d.statuses['ChatGPT'].text()=='Connection failed';d.close()

def test_stepper_bounds(app):
    s=Stepper(5,0);s.minus.click();assert s.value()==0
    for _ in range(10):s.plus.click()
    assert s.value()==5 and not s.plus.isEnabled()
    s.minus.click();assert s.value()==4

