from test_ui import app,window
from PySide6.QtWidgets import QLabel

def test_presence_during_response_and_random_delay(window,app):
    window.navigate('chats','mia')
    assert window.chat_presence_label.text()=='last seen recently'
    callbacks=[]
    window.ai=lambda task,payload,done,*a,**k:callbacks.append(done)
    window.send_message('mia','Hi');app.processEvents()
    assert window.chat_presence_label.text()=='online'
    callbacks.pop()({'reply':'Hello','patterns':[]});app.processEvents()
    timer=window.presence_timers['mia']
    assert timer.isActive() and 3000<=timer.interval()<=7000
    assert window.chat_presence_label.text()=='online'
    timer.stop();timer.timeout.emit()
    assert window.chat_presence_label.text()=='last seen recently'

def test_new_request_cancels_offline_and_chats_are_independent(window,app):
    window.set_agent_online('mia');window.finish_agent_presence('mia')
    timer=window.presence_timers['mia']
    window.pending_agents.add('mia');window.set_agent_online('mia')
    assert not timer.isActive()
    timer.timeout.emit();assert 'mia' in window.online_agents
    window.navigate('chats','leo');assert window.chat_presence_label.text()=='last seen recently'
    window.navigate('chats','mia');assert window.chat_presence_label.text()=='online'
    window.pending_agents.discard('mia');window.finish_agent_presence('mia',failed=True)
    assert window.chat_presence_label.text()=='last seen recently'
