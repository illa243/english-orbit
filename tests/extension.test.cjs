const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');const path=require('node:path');
const source=fs.readFileSync(path.join(__dirname,'../chrome-extension/content.js'),'utf8');
async function setup(){
 const handlers={},timers=[],messages=[];
 class Element{constructor(){this.value='';this.tagName='TEXTAREA';this.name='prompt';this.id='';this.autocomplete='';this.isConnected=true;}closest(sel){return sel==='[data-orbit-ignore]'?null:this;}matches(){return false;}getAttribute(){return '';}contains(x){return x===this;}}
 const ctx={Element,window:{},location:{hostname:'chatgpt.com'},document:{addEventListener:(e,f)=>handlers[e]=f},setInterval:f=>timers.push(f),chrome:{runtime:{sendMessage:async msg=>{if(msg.type==='config')return {enabled:true,sites:['chatgpt.com']};messages.push(msg);return {ok:true};}}}};
 vm.runInNewContext(source,ctx);await new Promise(r=>setImmediate(r));return {Element,handlers,timers,messages};
}
test('captures edited text, finalizes cleared composer',async()=>{const s=await setup(),el=new s.Element();el.value='I want learn';s.handlers.input({target:el});el.value='I want to learn';s.handlers.input({target:el});el.value='';s.timers[1]();assert.equal(s.messages.length,3);assert.equal(s.messages[2].text,'I want to learn');assert.equal(s.messages[2].final,true);});
test('submit does not duplicate until a new prompt starts',async()=>{const s=await setup(),el=new s.Element();el.value='English prompt';s.handlers.input({target:el});s.handlers.submit({target:el});s.timers[1]();assert.equal(s.messages.length,2);el.value='';s.timers[1]();el.value='New prompt';s.handlers.input({target:el});assert.equal(s.messages.length,3);assert.notEqual(s.messages[2].field,s.messages[0].field);});
test('password and OTP fields are excluded',async()=>{const s=await setup(),el=new s.Element();el.tagName='INPUT';el.type='password';el.value='Secret';s.handlers.input({target:el});el.type='text';el.autocomplete='one-time-code';s.handlers.input({target:el});assert.equal(s.messages.length,0);});
