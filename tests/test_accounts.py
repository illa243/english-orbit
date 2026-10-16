from test_ui import app,window
from settings_ui import SettingsDialog
from providers import model_info
import accounts

def inline(window):
    def work(fn,done,failed):
        try:result=fn()
        except Exception as e:failed(str(e))
        else:done(result)
    window.work=work

def test_saved_session_does_not_login(window,app,monkeypatch):
    inline(window);monkeypatch.setattr(accounts,'discover',lambda p:{'connected':True,'account_name':'Learner','models':[]})
    monkeypatch.setattr(accounts,'login',lambda p:(_ for _ in ()).throw(AssertionError('must not login')))
    d=SettingsDialog(window);d.connect('ChatGPT')
    assert d.connect_buttons['ChatGPT'].text()=='Вийти'
    assert 'Learner' in d.statuses['ChatGPT'].text()
    assert not window.accounts.pending;d.close()

def test_login_poll_updates_after_dialog_closed(window,app,monkeypatch):
    inline(window);state={'connected':False,'models':[]};calls=[]
    monkeypatch.setattr(accounts,'discover',lambda p:state.copy());monkeypatch.setattr(accounts,'login',lambda p:calls.append(p))
    d=SettingsDialog(window);d.connect('Claude');d.close();assert calls==['Claude']
    state.update(connected=True,account_name='name@example.com',models=[{'id':'example'}]);window.accounts.poll()
    assert not window.accounts.pending and window.store.get('provider_Claude')['models'][0]['id']=='example'
    reopened=SettingsDialog(window);assert reopened.connect_buttons['Claude'].text()=='Вийти';reopened.close()

def test_logout_and_transient_failure(window,app,monkeypatch):
    inline(window);window.store.set('provider_ChatGPT',{'connected':True,'account_name':'Test','models':[]})
    def fail(p):raise RuntimeError('offline')
    monkeypatch.setattr(accounts,'discover',fail);window.accounts.refresh('ChatGPT');assert window.store.get('provider_ChatGPT')['connected']
    calls=[];monkeypatch.setattr(accounts,'logout',lambda p:calls.append(p));d=SettingsDialog(window);d.connect('ChatGPT')
    assert calls==['ChatGPT'];assert not window.store.get('provider_ChatGPT')['connected'];assert d.connect_buttons['ChatGPT'].text()=='Підключити';d.close()

def test_efforts_from_catalog_and_persist(window,app):
    window.store.set('provider_ChatGPT',{'connected':True,'models':[{'id':'m1','efforts':['low','high']},{'id':'m2','efforts':['medium']}]});window.store.set('model','m1')
    d=SettingsDialog(window);assert [d.effort.itemData(i) for i in range(d.effort.count())]==['','low','high']
    d.effort.setCurrentIndex(2);d.model.setCurrentIndex(d.model.findData('m2'));assert [d.effort.itemData(i) for i in range(d.effort.count())]==['','medium']
    d.model.setCurrentIndex(d.model.findData('m1'));assert d.effort.currentData()=='high';d.save()
    assert window.store.get('efforts')['ChatGPT|m1']=='high'
    d=SettingsDialog(window);assert d.effort.currentData()=='high';d.close()

def test_catalog_normalization():
    assert model_info({'id':'x','supportedReasoningEfforts':[{'reasoningEffort':'low'},{'reasoningEffort':'xhigh'}]},'ChatGPT')['efforts']==['low','xhigh']
    assert model_info({'value':'y','supportedEffortLevels':['low','max']},'Claude')['efforts']==['low','max']
    assert model_info({'id':'z'},'ChatGPT')['efforts']==[]


def test_reasoning_is_passed_to_official_clients(monkeypatch):
    import providers,json
    monkeypatch.setattr(providers,'environment',lambda p:{})
    class FakeRpc:
        def __init__(self,*a):pass
        def request(self,*a,**k):return {'account':{'type':'chatgpt'}}
        def send(self,*a):pass
        def close(self):pass
    monkeypatch.setattr(providers,'Rpc',FakeRpc);calls=[]
    def run(p,args,*a,**k):
        calls.append(args)
        if args[:2]==['auth','status']:return json.dumps({'loggedIn':True,'authMethod':'oauth'})
        if p=='ChatGPT':return json.dumps({'type':'item.completed','item':{'type':'agent_message','text':'{"reply":"OK"}'}})
        return json.dumps({'result':'{"reply":"OK"}'})
    monkeypatch.setattr(providers,'run',run)
    assert providers.query('ChatGPT','model','test','high')=={'reply':'OK'}
    assert 'model_reasoning_effort="high"' in calls[-1]
    assert providers.query('Claude','model','test','low')=={'reply':'OK'}
    assert calls[-1][-2:]==['--effort','low']
