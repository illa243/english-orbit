const status=document.getElementById('status');
chrome.storage.local.get('token').then(x=>document.getElementById('token').value=x.token||'');
document.getElementById('pair').onclick=async()=>{
  await chrome.storage.local.set({token:document.getElementById('token').value.trim()});
  const result=await chrome.runtime.sendMessage({type:'config'});
  status.textContent=result.error||'Підключено. Збір '+(result.enabled?'увімкнено.':'призупинено.');
};
async function allow(all){
  try{
    const site=document.getElementById('site').value.trim().replace(/^https?:\/\//,'').replace(/\/$/,'');
    if(!all&&!/^[a-z0-9.-]+\.[a-z]{2,}$/i.test(site))throw new Error('Введіть домен, наприклад chatgpt.com');
    const origins=all?['https://*/*','http://*/*']:[`https://${site}/*`,`https://*.${site}/*`];
    const ok=await chrome.permissions.request({origins});
    if(ok){await chrome.runtime.sendMessage({type:'register'});status.textContent='Дозвіл надано. Додайте домен також у налаштуваннях утиліти й перезавантажте вкладку.';}
  }catch(e){status.textContent=e.message;}
}
document.getElementById('allow').onclick=()=>allow(false);
document.getElementById('all').onclick=()=>allow(true);
