import sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from core import Store
from providers import make_prompt


def result(outcome='error',evidence='decided go'):
    return {'observations':[{'pattern':'decide to do','outcome':outcome,'evidence':evidence}]}


def test_observation_evidence_dedup_assistance(tmp_path):
    store=Store(tmp_path/'data.sqlite')
    store.record_learning('1','I decided go',result())
    store.record_learning('1','I decided go',result())
    store.record_learning('2','I decided go',result())
    store.record_learning('3','I decided to go',result('correct','decided to go'),1)
    store.record_learning('4','I decided to go',result('correct','decided to go'))
    store.record_learning('5','Nothing related',result())
    row=store.learning_stats()[0]
    assert (row['mistakes'],row['independent'],row['assisted'])==(2,1,1)
    assert store.conversation_learning()[0]['mistakes']==2


def test_memory_isolation_updates_and_forgetting(tmp_path):
    store=Store(tmp_path/'data.sqlite')
    r={'memories':[{'topic':'work','fact':'Works in games','evidence':'I make games'}]}
    store.remember('mia','1','I make games',r)
    assert len(store.memories('mia'))==1
    assert not store.memories('leo')
    store.remember('leo','2','Hello',r)
    assert not store.memories('leo')
    store.forget_memory('leo',store.memories('mia')[0]['id'])
    assert store.memories('mia')
    store.forget_memory('mia',store.memories('mia')[0]['id'])
    store.remember('mia','3','I make games',r)
    assert not store.memories('mia')
    assert Store(store.path).rows('SELECT topic FROM character_memories WHERE deleted=1')


def test_old_database_restore_migrates(tmp_path):
    store=Store(tmp_path/'data.sqlite');agents=tmp_path/'agents';agents.mkdir()
    store.backup(tmp_path/'old.zip',agents)
    store.restore(tmp_path/'old.zip',agents)
    store.record_learning('1','decided go',result())
    assert store.learning_stats()[0]['mistakes']==1


def test_prompts_have_evidence_and_staged_help():
    for task in ('chat','analyze','hint','opener'):
        prompt=make_prompt(task,{}, {'stage':1})
        assert 'forgotten_topics' in prompt
        assert 'stage 1' in prompt
    assert 'observations' in make_prompt('chat',{}, {})

def test_memory_new_detail_preserves_name_and_explicit_change(tmp_path):
    store=Store(tmp_path/'data.sqlite')
    def remember(source,text,operation='append'):
        store.remember('mia',source,text,{'memories':[{'topic':'project','fact':text,'evidence':text,'operation':operation}]})
    remember('1','Project is Moon Garden')
    remember('2','Testing tomorrow')
    assert 'Moon Garden' in store.memories('mia')[0]['fact']
    assert 'Testing tomorrow' in store.memories('mia')[0]['fact']
    remember('3','Project renamed to Sun Garden','replace')
    assert store.memories('mia')[0]['fact']=='Project renamed to Sun Garden'
