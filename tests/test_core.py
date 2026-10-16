import sys, time, json, zipfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store, Collector, learning_text, now
from capture import host_allowed
from providers import parse_json, ProviderError
import pytest

@pytest.fixture
def store(tmp_path):return Store(tmp_path/'test.sqlite')

def test_idle_edit_send(store):
    clock=[0];c=Collector(store,lambda:clock[0])
    c.receive('one','Chrome','I want learn English')
    clock[0]=19;c.tick();assert len(store.rows('SELECT * FROM texts'))==0
    clock[0]=21;c.tick();first=store.one('SELECT * FROM texts');assert first['version']==1
    clock[0]=50;c.receive('one','Chrome','I want to learn English')
    clock[0]=71;c.tick();changed=store.one('SELECT * FROM texts');assert changed['id']==first['id'];assert changed['version']==2
    c.receive('one','Chrome','I want to learn English',True)
    assert store.one('SELECT * FROM texts')['final']==1
    c.receive('one','Chrome','Another prompt',True)
    assert len(store.rows('SELECT * FROM texts'))==2

def test_submit_before_idle_and_clear(store):
    c=Collector(store);c.receive('x','native','Hello English');c.receive('x','native','')
    assert store.one('SELECT * FROM texts')['body']=='Hello English'
    c.receive('x','native','Next English',True);assert len(store.rows('SELECT * FROM texts'))==2

def test_separate_fields(store):
    c=Collector(store,lambda:30);c.receive('a','A','English one',True);c.receive('b','B','English two',True)
    assert len(store.rows('SELECT * FROM texts'))==2

def test_analysis_is_immutable(store):
    tid=store.save_text('manual','I decided listen');r=store.one('SELECT * FROM texts WHERE id=?',(tid,))
    store.save_analysis(r,r['body'],{'minimal':'I decided to listen','patterns':[]})
    store.save_text('manual','I decided to read',tid)
    a=store.one('SELECT * FROM analyses');assert a['original']=='I decided listen';assert a['version']==1

def test_retention_protects_analyzed_pinned(store):
    a=store.save_text('a','old first');b=store.save_text('b','old pinned');c=store.save_text('c','old analyzed')
    store.execute('UPDATE texts SET updated=?',(now()-9*86400,));store.execute('UPDATE texts SET pinned=1 WHERE id=?',(b,))
    store.save_analysis(store.one('SELECT * FROM texts WHERE id=?',(c,)),'old analyzed',{})
    store.cleanup();assert {r['id'] for r in store.rows('SELECT * FROM texts')}=={b,c}

def test_two_directions_and_no_advance_on_typo(store):
    w=store.add_word(store.dictionary('Words'),'shift','зміна','A small shift.');r=store.one('SELECT * FROM reviews')
    store.grade(r['id'],'typo');assert len(store.rows('SELECT * FROM reviews'))==1
    store.grade(r['id'],'correct');rows=store.rows('SELECT * FROM reviews');assert len(rows)==2
    assert next(x for x in rows if x['direction']=='uk-en')['streak']==0
    store.grade(r['id'],'correct');assert len(store.rows('SELECT * FROM reviews'))==2

def test_profiles_and_chats_separate(store):
    store.add_message('mia','user','private text');store.add_patterns([{'pattern':'decide to do','explanation':'grammar'}])
    assert not store.rows('SELECT * FROM messages WHERE agent=?',('leo',))
    assert 'private text' not in json.dumps(store.shared_learning())

def test_filters():
    text='Hello English\n```python\nprint(1)\n```\n> quoted\nINFO log\nI enjoy music.'
    assert learning_text(text)=='Hello English\n\nI enjoy music.'
    assert host_allowed('https://chatgpt.com/c/1',['chatgpt.com'])
    assert not host_allowed('https://evilchatgpt.com',['chatgpt.com'])
    assert not host_allowed('https://chatgpt.com.evil.com',['chatgpt.com'])

def test_backup(store,tmp_path):
    agents=tmp_path/'agents';agents.mkdir();(agents/'AGENT.md').write_text('Instructions')
    store.save_text('manual','Example English');target=tmp_path/'backup.zip';store.backup(target,agents)
    with zipfile.ZipFile(target) as z:assert set(z.namelist())=={'orbit.sqlite','agents/AGENT.md','manifest.json'}
    store.save_text('manual','Second English');store.restore(target,agents);assert len(store.rows('SELECT * FROM texts'))==1

def test_json():
    assert parse_json('```json\n{"reply":"hi"}\n```')['reply']=='hi'
    with pytest.raises(ProviderError):parse_json('not json')
