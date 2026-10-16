import os, sys, json
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import pytest
from PySide6.QtWidgets import QApplication
from ui import MainWindow, STYLE, SettingsDialog, ProfileDialog, AgentDialog, WordDialog, AnalysisDialog, PracticeDialog, Popup
from core import Store

@pytest.fixture(scope='module')
def app():
    app=QApplication.instance() or QApplication([]);app.setStyleSheet(STYLE);yield app

@pytest.fixture
def window(app,tmp_path):
    store=Store(tmp_path/'ui.sqlite');store.set('onboarded',True);store.set('name','Test learner')
    w=MainWindow(store,False);w.show();app.processEvents();yield w
    w.tick_timer.stop();w.scheduler.stop();w.exiting=True
    for d in w.dialogs:d.close()
    w.close();app.processEvents()

def test_all_screens(window,app):
    for page in ('chats','texts','words','practice'):
        window.navigate(page);app.processEvents();assert window.page==page
    for cls in (SettingsDialog,ProfileDialog,AgentDialog,WordDialog):
        d=cls(window);d.show();app.processEvents();assert d.isVisible();d.close()

def test_failed_chat_is_preserved(window,app):
    assert window.send_message('mia','Hello there')
    app.processEvents()
    msg=window.store.one('SELECT * FROM messages');assert msg['body']=='Hello there';assert msg['status']=='failed'
    assert window.store.one('SELECT * FROM jobs')['status']=='failed'
    assert not window.pending_agents

def test_chat_success_and_corrections(window,app):
    def fake(task,payload,done,*args,**kwargs):
        done({'reply':'Tell me more.','errors':[{'before':'decided go','after':'decided to go','explanation':'Use to.'}],'patterns':[{'pattern':'decide to do','explanation':'Use to.'}]})
    window.ai=fake;window.send_message('mia','I decided go')
    app.processEvents();rows=window.store.rows('SELECT * FROM messages ORDER BY created')
    assert len(rows)==2 and rows[0]['status']=='sent';assert 'decided to go' in rows[0]['corrections']
    assert len(window.store.shared_learning())==1
    window.navigate('chats','mia');app.processEvents()

def test_analysis_and_snapshot(window,app):
    tid=window.store.save_text('manual','I decided go');record=window.store.one('SELECT * FROM texts WHERE id=?',(tid,))
    def fake(task,payload,done,*args,**kwargs):done({'minimal':'I decided to go','natural':'I decided to go','errors':[],'patterns':[{'pattern':'decide to do'}]})
    window.ai=fake;d=AnalysisDialog(window,record);d.start();app.processEvents()
    assert window.store.one('SELECT * FROM analyses')['original']=='I decided go'
    assert d.practice.isEnabled();d.close()

def test_review_close_does_not_grade(window,app):
    store=window.store;wid=store.add_word(store.dictionary('Test'),'hello','привіт','Hello, friend!')
    d=PracticeDialog(window);app.processEvents();d.close()
    assert not store.rows('SELECT * FROM events')
    d=PracticeDialog(window);d.answer.setText('привіт');d.submit();app.processEvents()
    assert len(store.rows('SELECT * FROM reviews'))==2
    assert store.one('SELECT * FROM events')['kind']=='review';d.close()

def test_word_confirm_only(window,app):
    d=WordDialog(window,'test');d.uk.setText('тест');d.dictionary.setCurrentText('New dictionary')
    assert not window.store.rows('SELECT * FROM words')
    d.save();assert window.store.one('SELECT * FROM words')['english']=='test';d.close()

def test_learning_memory_and_hint_flow(window,app):
    from learning_ui import HintDialog, MemoryDialog
    seen=[]
    def fake(task,payload,done,*args,**kwargs):
        seen.append((task,payload))
        if task=='hint':done({'hint':'Use decide to' if payload['stage']==1 else 'I decided to ...' if payload['stage']==2 else 'I decided to make games.'})
        else:done({'reply':'What would you like to build?', 'patterns':[], 'observations':[{'pattern':'decide to do','outcome':'correct','evidence':'decided to make'}], 'memories':[{'topic':'interest.games','fact':'Makes games','evidence':'make games'}]})
    window.ai=fake
    agent=window.store.one("SELECT * FROM agents WHERE id='mia'")
    d=HintDialog(window,agent,'');d.request();d.request();d.request()
    assert [p['stage'] for task,p in seen]==[1,2,3]
    assert window.store.get('hint_level_mia')==3
    window.send_message('mia','I decided to make games')
    row=window.store.learning_stats()[0]
    assert row['assisted']==1 and row['independent']==0
    assert window.store.get('hint_level_mia')==0
    assert window.chat_context('mia')['memory']
    assert not window.chat_context('leo')['memory']
    mem=MemoryDialog(window,agent);mem.items.setCurrentRow(0);mem.forget()
    assert window.chat_context('mia')['forgotten_topics']==['interest.games']
    window.navigate('practice');app.processEvents()
    mem.close();d.close()
