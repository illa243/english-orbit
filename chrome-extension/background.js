const BASE = 'http://127.0.0.1:18743';
async function bridge(path, body) {
  const {token} = await chrome.storage.local.get('token');
  if (!token) throw new Error('Enter your pairing code first.');
  const r = await fetch(BASE+path, {method:body?'POST':'GET',headers:{Authorization:'Bearer '+token,'Content-Type':'application/json'},...(body?{body:JSON.stringify(body)}:{})});
  if(!r.ok) throw new Error('Open English Orbit and check the pairing code.');
  return r.json();
}
async function register() {
  const permissions = await chrome.permissions.getAll();
  const matches = (permissions.origins||[]).filter(x=>!x.includes('127.0.0.1'));
  await chrome.scripting.unregisterContentScripts();
  if(matches.length) await chrome.scripting.registerContentScripts([{id:'orbit-capture',matches,js:['content.js'],runAt:'document_idle',allFrames:false}]);
}
chrome.runtime.onInstalled.addListener(()=>{
  chrome.contextMenus.create({id:'orbit-word',title:'English Orbit: add to dictionary',contexts:['selection']});
  chrome.contextMenus.create({id:'orbit-text',title:'English Orbit: save for analysis',contexts:['selection']});
  register().catch(()=>{});
});
chrome.permissions.onAdded.addListener(()=>register().catch(()=>{}));
chrome.permissions.onRemoved.addListener(()=>register().catch(()=>{}));
chrome.contextMenus.onClicked.addListener((info)=>bridge(info.menuItemId==='orbit-word'?'/word':'/manual',{text:info.selectionText||''}).catch(()=>{}));
chrome.runtime.onMessage.addListener((msg,sender,respond)=>{
  if(sender.id!==chrome.runtime.id)return;
  if(msg.type==='config')bridge('/config').then(respond).catch(e=>respond({error:e.message}));
  else if(msg.type==='capture'){
    // Never trust URL, tab ID or identity supplied by the page.
    const url=sender.url||sender.tab?.url||'';
    bridge('/capture',{text:String(msg.text||''),key:`chrome:${sender.tab?.id}:${sender.documentId}:${msg.field}`,url,final:!!msg.final}).then(respond).catch(e=>respond({error:e.message}));
  }else if(msg.type==='register') register().then(()=>respond({ok:true})).catch(e=>respond({error:e.message}));
  else return;
  return true;
});
