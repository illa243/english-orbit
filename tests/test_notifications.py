from test_ui import app,window
from PySide6.QtCore import Qt,QPoint
from PySide6.QtTest import QTest
from ui import Popup
import ui

def ready(window,monkeypatch):
    window.store.set('hours_start',0);window.store.set('hours_end',24)
    monkeypatch.setattr(ui,'idle_seconds',lambda:25)
    monkeypatch.setattr(window,'viewing_chat',lambda aid:False)

def add(window,aid):window.store.add_message(aid,'assistant','Hello from '+aid,unread=1);window.queue_notification('chat',aid)

def test_queue_keeps_each_sender(window,app,monkeypatch):
    ready(window,monkeypatch);add(window,'mia');add(window,'leo');window.tick();app.processEvents()
    assert [p.agent['id'] for p in window.popups]==['mia','leo']
    assert not window.notifications
    assert window.hide_all_toast.isVisible()
    assert window.popups[0].geometry().bottom()<window.popups[1].geometry().top()
    window.popups[0].close();app.processEvents()
    assert not window.hide_all_toast.isVisible()
    window.popup.close()


def test_toast_click_opens_exact_chat_from_tray(window,app,monkeypatch):
    ready(window,monkeypatch);window.hide();add(window,'leo');window.tick();app.processEvents();popup=window.popup
    assert popup.isVisible() and popup.parent() is None
    assert popup.testAttribute(Qt.WA_ShowWithoutActivating)
    QTest.mouseClick(popup,Qt.LeftButton,pos=QPoint(120,45));app.processEvents()
    assert window.isVisible() and window.page=='chats' and window.active_agent=='leo'
    assert window.store.one("SELECT count(*) n FROM messages WHERE agent='leo' AND unread=1")['n']==0
    assert not popup.isVisible()

def test_close_button_does_not_open_chat_or_mark_read(window,app,monkeypatch):
    ready(window,monkeypatch);window.hide();add(window,'mia');window.tick();app.processEvents()
    window.popup.dismiss.click();app.processEvents()
    assert not window.isVisible() and not window.popup.isVisible()
    assert window.store.one("SELECT unread FROM messages WHERE agent='mia'")['unread']==1

def test_dnd_idle_and_schedule_gate(window,app,monkeypatch):
    ready(window,monkeypatch);add(window,'mia');window.store.set('dnd',True);window.tick();assert window.popup is None
    window.store.set('dnd',False);monkeypatch.setattr(ui,'idle_seconds',lambda:2);window.tick();assert window.popup.isVisible();window.popup.close();add(window,'leo')
    monkeypatch.setattr(ui,'idle_seconds',lambda:25);window.store.set('hours_start',24);window.tick();assert not window.popup.isVisible()
    window.store.set('hours_start',0);window.tick();assert window.popup.isVisible();window.popup.close()

def test_background_reply_queues_notification(window,app,monkeypatch):
    ready(window,monkeypatch);window.active_agent='mia';window.page='texts'
    window.ai=lambda task,payload,done,*a,**k:done({'reply':'Hello!','patterns':[]})
    window.send_message('mia','Hi')
    assert ('chat','mia') in window.notifications
    assert window.store.one("SELECT unread FROM messages WHERE role='assistant'")['unread']==1

def test_preview_does_not_write_fake_messages(window,app):
    before=window.store.rows('SELECT id FROM messages');window.test_notification();app.processEvents()
    assert window.popup.isVisible();assert window.store.rows('SELECT id FROM messages')==before
    screen=window.screen().availableGeometry();assert screen.contains(window.popup.geometry());window.popup.close()


def test_active_computer_does_not_block_minimized_chat(window,app,monkeypatch):
    window.store.set('hours_start',0);window.store.set('hours_end',24)
    monkeypatch.setattr(ui,'idle_seconds',lambda:0)
    window.showMinimized();app.processEvents()
    window.notifications.append(('review',None));add(window,'mia');window.tick();app.processEvents()
    assert window.popup.isVisible() and window.popup.agent['id']=='mia'
    assert window.notifications==[('review',None)]
    assert window.isMinimized();window.popup.close()

def test_undelivered_survives_restart_but_shown_does_not(window,app,monkeypatch):
    ready(window,monkeypatch);add(window,'mia')
    restarted=ui.MainWindow(window.store,False);restarted.tick_timer.stop();restarted.scheduler.stop()
    assert ('chat','mia') in restarted.notifications
    restarted.deliver_notifications();assert restarted.popup.isVisible();restarted.popup.close();restarted.exiting=True;restarted.close()
    again=ui.MainWindow(window.store,False);again.tick_timer.stop();again.scheduler.stop()
    assert ('chat','mia') not in again.notifications
    again.exiting=True;again.close()


def test_hide_all_preserves_unread_and_dismisses_queue(window,app,monkeypatch):
    ready(window,monkeypatch);window.hide()
    for aid in ('mia','leo','emma'):add(window,aid)
    window.tick();app.processEvents()
    assert len(window.popups)==3
    add(window,'mia');window.tick()
    assert window.notifications
    window.hide_all_toast.button.click();app.processEvents()
    assert not window.popups and not window.notifications
    assert not window.hide_all_toast.isVisible() and not window.isVisible()
    assert window.store.one('SELECT COUNT(*) n FROM messages WHERE unread=1')['n']==4
    assert window.store.one('SELECT COUNT(*) n FROM notification_receipts')['n']==4
    window.tick();assert not window.popups


def test_preview_elides_to_two_lines(window,app):
    body='Hi Illia! Have you watched any films or listened to any music lately that you would recommend? '*5
    window.store.add_message('emma','assistant',body,unread=1)
    agent=window.store.one("SELECT * FROM agents WHERE id='emma'")
    window.show_notification(agent);app.processEvents()
    preview=window.popup.body
    lines=preview.text().splitlines()
    assert len(lines)==2 and lines[-1].endswith('…')
    assert all(preview.fontMetrics().horizontalAdvance(line)<=preview.width() for line in lines)
    assert preview.height()>=2*preview.fontMetrics().lineSpacing()
    assert window.popup.rect().contains(preview.mapTo(window.popup,preview.rect().bottomRight()))
    window.popup.close()
