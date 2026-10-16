(()=>{
  if(window.__englishOrbitCapture)return;window.__englishOrbitCapture=true;
  let config={enabled:false}, counter=0;
  const states=new WeakMap(), tracked=new Set();
  async function refresh(){try{config=await chrome.runtime.sendMessage({type:'config'});}catch{config={enabled:false};}}
  refresh();setInterval(refresh,10000);
  function allowed(){return config.enabled&&(config.all||(config.sites||[]).some(s=>location.hostname===s||location.hostname.endsWith('.'+s)));}
  function editable(target){
    if(!(target instanceof Element))return null;
    const el=target.closest('textarea,input,[contenteditable="true"],[role="textbox"]');
    if(!el||el.closest('[data-orbit-ignore]')||el.matches('[readonly],[disabled]'))return null;
    if(el.tagName==='INPUT'&&!['text','search',''].includes(el.type))return null;
    if(/password|credit.?card|card.?number|otp|one.?time|cvc|cvv/i.test([el.name,el.id,el.autocomplete,el.getAttribute('aria-label')].join(' ')))return null;
    return el;
  }
  const value=el=>('value' in el?el.value:el.innerText)||'';
  function send(el,final=false){
    if(!allowed())return;
    let state=states.get(el);if(!state)return;
    const text=value(el);
    if(state.submitted!==undefined){
      if(text===state.submitted)return;
      delete state.submitted;
    }
    if(!text.trim()&&state.last.trim()){
      chrome.runtime.sendMessage({type:'capture',field:state.id,text:state.last,final:true}).catch(()=>{});
      state.id=String(++counter);state.last='';return;
    }
    if(text.length>50000)return;
    if(text===state.last&&!final)return;
    state.last=text;
    chrome.runtime.sendMessage({type:'capture',field:state.id,text,final}).catch(()=>{});
    if(final){state.id=String(++counter);state.last='';state.submitted=text;}
  }
  document.addEventListener('input',e=>{
    const el=editable(e.target);if(!el||!allowed())return;
    if(!states.has(el)){states.set(el,{id:String(++counter),last:''});tracked.add(el);}
    send(el);
  },true);
  // Form submission is reliable. Do not assume Enter means send: it may insert a newline.
  document.addEventListener('submit',e=>{for(const el of tracked)if(e.target.contains(el))send(el,true);},true);
  // SPA composers often clear programmatically without an input event.
  setInterval(()=>{
    for(const el of tracked){
      if(!el.isConnected){const s=states.get(el);if(s?.last&&allowed())chrome.runtime.sendMessage({type:'capture',field:s.id,text:s.last,final:true}).catch(()=>{});tracked.delete(el);}
      else send(el);
    }
  },700);
})();
