from test_ui import app,window
from core import Store
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QPushButton,QMessageBox

def test_pin_latest_and_persistence(window,app):
    a=window.store.add_message('mia','assistant','First pinned text')
    b=window.store.add_message('mia','user','Second pinned text')
    for mid in (a,b):window.set_pin(window.store.one('SELECT * FROM messages WHERE id=?',(mid,)))
    assert [m['id'] for m in window.pins('mia')]==[b,a]
    assert Store(window.store.path).one('SELECT count(*) n FROM message_links WHERE pinned>0')['n']==2
    assert not window.pins('leo')
    window.findChild(QPushButton,'openPinnedMessages').click();app.processEvents()
    assert window.pins_agent=='mia' and len(window.message_widgets)==2
    window.set_pin(window.store.one('SELECT * FROM messages WHERE id=?',(b,)),False)
    assert len(window.pins('mia'))==1

def test_jump_to_old_pin(window,app):
    first=window.store.add_message('mia','assistant','Old target')
    for i in range(110):window.store.add_message('mia','assistant','Message '+str(i))
    window.jump_to_message('mia',first);QTest.qWait(150)
    assert first in window.message_widgets and window.pins_agent is None
    target=window.message_widgets[first]
    p=target.mapTo(window.chat_scroll.viewport(),target.rect().center())
    assert window.chat_scroll.viewport().rect().contains(p)

def test_context_reply_and_delete(window,app,monkeypatch):
    mid=window.store.add_message('mia','assistant','Which puzzle did you choose?')
    m=window.store.one('SELECT * FROM messages WHERE id=?',(mid,))
    menu=window.message_menu(m)
    assert [a.text() for a in menu.actions()]==['Reply','Pin','Copy Text','Delete']
    menu.actions()[2].trigger();assert app.clipboard().text()==m['body']
    window.start_reply(m);window.chat_composer.setPlainText('The greenhouse puzzle.')
    captured=[]
    def fake(task,payload,done,*args,**kwargs):captured.append(payload);done({'reply':'Nice choice!','patterns':[]})
    window.ai=fake;window.chat_composer.submitted.emit();app.processEvents()
    assert captured[0]['reply_to']['body']==m['body']
    assert window.store.one('SELECT reply_to FROM message_links WHERE reply_to=?',(mid,))
    window.set_pin(m)
    monkeypatch.setattr(QMessageBox,'question',lambda *a:QMessageBox.Yes)
    window.delete_message(m)
    assert not window.pins('mia') and not window.store.one('SELECT id FROM messages WHERE id=?',(mid,))
    window.navigate('chats','mia');app.processEvents()
