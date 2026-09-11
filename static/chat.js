(() => {
  'use strict';
  const root = document.getElementById('swaran-app');
  const $ = name => document.getElementById('sw-' + name);
  const STORAGE = 'swaransoft-conversations-v1';
  const speechLanguages = { en: 'en-IN', hi: 'hi-IN', ta: 'ta-IN', te: 'te-IN', mr: 'mr-IN', gu: 'gu-IN', bn: 'bn-IN', pa: 'pa-IN' };
  const allowedLanguages = ['', ...Object.keys(speechLanguages)];
  let sessions = [], active = null, pending = null, attachment = null, attachmentURL = null;
  let recognition = null, listening = false, autoRead = false, followBottom = true;
  const retryFiles = new Map();
  const imageURLs = new Set();
  const icons = () => window.lucide?.createIcons({ attrs: { width: 18, height: 18 } });
  const uid = () => crypto.randomUUID();
  const notice = text => { $('notice').textContent = text; };

  function restore() {
    try {
      const raw = sessionStorage.getItem(STORAGE);
      if (!raw || raw.length > 2000000) return;
      const data = JSON.parse(raw);
      if (!Array.isArray(data.sessions)) return;
      sessions = data.sessions.filter(s => typeof s.id === 'string' && typeof s.title === 'string' && Array.isArray(s.messages))
        .slice(-30).map(s => ({ id: s.id, title: s.title.slice(0,100), messages: s.messages.filter(m =>
          m && typeof m.id === 'string' && ['user','assistant'].includes(m.role) && typeof m.text === 'string')
          .slice(-100).map(m => ({...m, imageURL: null, state: m.state === 'pending' ? 'stopped' : m.state,
            text: m.text.slice(0,50000), language: allowedLanguages.includes(m.language) ? m.language : 'en'})) }));
      active = sessions.find(s => s.id === data.active) || null;
    } catch { notice('Conversation history is unavailable in this browser.'); }
  }
  function persist() {
    try {
      const saved = sessions.slice(-30).map(s => ({...s,messages:s.messages.slice(-100).map(({imageURL,...m}) => m)}));
      sessionStorage.setItem(STORAGE, JSON.stringify({sessions:saved, active:active?.id}));
    } catch { notice('This conversation is available until the page closes; browser storage is full or unavailable.'); }
  }
  function safeURL(value) {
    try { const url = new URL(value); return ['https:','http:','mailto:'].includes(url.protocol) ? url.href : null; }
    catch { return null; }
  }
  function markdown(node, text) {
    if (!window.marked || !window.DOMPurify) { node.textContent = text; node.style.whiteSpace = 'pre-wrap'; return; }
    node.innerHTML = DOMPurify.sanitize(marked.parse(text, {gfm:true,breaks:false}), {
      FORBID_TAGS: ['img','iframe','style','form','input','button','svg','video','audio'],
      FORBID_ATTR: ['style','id','name','class'],
    });
    node.querySelectorAll('a').forEach(a => {
      const url = safeURL(a.getAttribute('href'));
      if (!url) { a.replaceWith(document.createTextNode(a.textContent)); return; }
      a.href = url; a.target = '_blank'; a.rel = 'noopener noreferrer';
    });
    node.querySelectorAll('table').forEach(table => { const wrap = document.createElement('div'); wrap.className='sw-table-scroll'; table.replaceWith(wrap); wrap.append(table); });
  }
  function scrollBottom(force = false) {
    if (followBottom || force) { $('scroll').scrollTop = $('scroll').scrollHeight; followBottom = true; $('jump').hidden = true; }
  }
  function setMenu(open) {
    root.dataset.menu = open ? 'open' : 'closed'; $('menu').setAttribute('aria-expanded',String(open)); $('backdrop').hidden = !open;
    const mobile = window.matchMedia('(max-width:550px)').matches;
    $('sidebar').inert = mobile && !open;
    if (mobile && open) $('new').focus();
  }
  function controls() {
    const busy = !!pending;
    $('send').disabled = !busy && !$('input').value.trim() && !attachment;
    $('send').innerHTML = `<i data-lucide="${busy ? 'square' : 'arrow-up'}" aria-hidden="true"></i>`;
    $('send').setAttribute('aria-label',busy ? 'Stop response' : 'Send message');
    $('send').dataset.tooltip = busy ? 'Stop response' : 'Send message';
    $('attach').disabled = busy; $('mic').disabled = busy; $('language').disabled = busy;
    $('delete').disabled = !active;
    root.querySelectorAll('.sw-suggestion').forEach(button => { button.disabled = busy; });
    icons();
  }
  function renderHistory() {
    $('history').replaceChildren();
    if (!sessions.length) {
      const empty = document.createElement('div'); empty.className='sw-history-empty'; empty.textContent='Your next idea starts here.'; $('history').append(empty);
    }
    sessions.slice().reverse().forEach(session => {
      const button = document.createElement('button'); button.type='button'; button.innerHTML='<i data-lucide="message-square" aria-hidden="true"></i><span></span>';
      button.querySelector('span').textContent=session.title; button.setAttribute('aria-current',String(session===active));
      button.addEventListener('click',() => { stopResponse(); active=session; renderConversation(); setMenu(false); persist(); });
      $('history').append(button);
    });
    icons();
  }
  function addSources(article, sources) {
    if (!Array.isArray(sources) || !sources.length) return;
    const details=document.createElement('details'); details.className='sw-sources';
    const summary=document.createElement('summary'); summary.textContent='Context sources'; details.append(summary);
    const list=document.createElement('ul');
    sources.forEach(source => {
      const row=document.createElement('li'); const url=safeURL(source.url);
      const label=document.createElement(url ? 'a' : 'span'); label.textContent=source.name || 'Company document';
      if(url) { label.href=url; label.target='_blank'; label.rel='noopener noreferrer'; }
      row.append(label); list.append(row);
    });
    details.append(list); article.append(details);
  }
  function renderMessage(message) {
    const article=document.createElement('article'); article.className='sw-message '+message.role; article.dataset.id=message.id;
    if(message.role==='user') {
      if(message.imageURL) { const image=document.createElement('img'); image.src=message.imageURL; image.alt=message.imageName || 'Attached image'; article.append(image); }
      else if(message.imageName) { const name=document.createElement('small'); name.textContent=message.imageName+' (image attachment)'; article.append(name,document.createElement('br')); }
      article.append(document.createTextNode(message.text));
      return article;
    }
    article.innerHTML='<div class="sw-message-head"><span class="sw-mini"><i data-lucide="sparkles" aria-hidden="true"></i></span>Swaran Soft</div><div class="sw-status" role="status" aria-live="polite"></div><div class="sw-message-body"></div>';
    const status=article.querySelector('.sw-status'), body=article.querySelector('.sw-message-body');
    if(message.state==='pending') {
      status.hidden=!!message.text;
      status.innerHTML='<span class="sw-spinner" aria-hidden="true"></span>';
      status.append(document.createTextNode(message.status || 'Thinking'));
    } else if(message.state==='stopped') status.textContent='Response stopped';
    else status.hidden=true;
    markdown(body,message.text);
    if(message.state==='error') {
      const error=document.createElement('div'); error.className='sw-error'; error.setAttribute('role','alert');
      error.textContent=message.error || 'The response could not be completed.';
      const retry=document.createElement('button'); retry.className='sw-retry'; retry.type='button'; retry.dataset.retry=message.id;
      retry.innerHTML='<i data-lucide="rotate-ccw" aria-hidden="true"></i>Try again'; error.append(retry); body.append(error);
    }
    if(message.state==='complete') {
      addSources(article,message.sources);
      if(message.location && Number.isFinite(message.location.latitude) && Number.isFinite(message.location.longitude)) {
        const {latitude,longitude}=message.location;
        const map=document.createElement('iframe'); map.className='sw-map'; map.title='Swaran Soft office location'; map.loading='lazy'; map.referrerPolicy='no-referrer';
        map.src=`https://www.google.com/maps?q=${latitude},${longitude}&output=embed`; body.append(map);
        const link=document.createElement('a'); link.className='sw-map-link'; link.href=`https://www.google.com/maps?q=${latitude},${longitude}`; link.target='_blank'; link.rel='noopener noreferrer'; link.textContent='Open directions'; body.append(link);
      }
      const actions=document.createElement('div'); actions.className='sw-message-actions';
      actions.innerHTML='<button class="sw-icon" type="button" data-copy="true" aria-label="Copy response" data-tooltip="Copy response"><i data-lucide="copy" aria-hidden="true"></i></button><button class="sw-icon" type="button" data-speak="true" aria-label="Read response aloud" data-tooltip="Read aloud"><i data-lucide="volume-2" aria-hidden="true"></i></button>';
      article.append(actions);
    }
    return article;
  }
  function renderConversation() {
    $('welcome').hidden=!!active; $('thread').hidden=!active; $('thread').replaceChildren();
    active?.messages.forEach(message => $('thread').append(renderMessage(message)));
    renderHistory(); controls(); icons(); scrollBottom(true);
  }
  function updateMessage(message) {
    const existing=Array.from($('thread').children).find(el=>el.dataset.id===message.id);
    if(existing) existing.replaceWith(renderMessage(message));
    icons(); scrollBottom();
  }
  function setAttachment(file) {
    if(attachmentURL) URL.revokeObjectURL(attachmentURL);
    attachment=file; attachmentURL=file ? URL.createObjectURL(file) : null;
    $('attachment').hidden=!file; $('image-name').textContent=file?.name || '';
    if(file) $('image-preview').src=attachmentURL; else $('image-preview').removeAttribute('src');
    controls();
  }
  function stopResponse() {
    if(!pending) return;
    const request=pending; pending=null; request.controller.abort();
    request.assistant.state='stopped'; updateMessage(request.assistant); persist(); controls(); notice('Response stopped.');
  }
  function newConversation() {
    stopResponse(); window.speechSynthesis?.cancel(); active=null; $('input').value=''; $('input').style.height='';
    setAttachment(null); $('file').value=''; setMenu(false); notice(''); renderConversation(); persist(); $('input').focus();
  }
  function requestHistory(messages) {
    const history=[]; let budget=45000;
    for(const message of messages.slice().reverse()) {
      if(message.role==='assistant' && message.state!=='complete') continue;
      const content=message.text.slice(0,8000); if(!content) continue;
      if(history.length>=20 || content.length>budget) break;
      budget-=content.length; history.unshift({role:message.role,content});
    }
    return history;
  }
  async function readEvents(response,onEvent) {
    if(!response.body) throw new Error('Streaming is unavailable in this browser.');
    const reader=response.body.getReader(), decoder=new TextDecoder(); let buffer='';
    try {
      while(true) {
        const {value,done}=await reader.read();
        buffer+=decoder.decode(value,{stream:!done});
        let match;
        while((match=/\r?\n\r?\n/.exec(buffer))) {
          const block=buffer.slice(0,match.index); buffer=buffer.slice(match.index+match[0].length);
          let event='message'; const lines=[];
          for(const line of block.split(/\r?\n/)) {
            if(line.startsWith('event:')) event=line.slice(6).trim();
            else if(line.startsWith('data:')) lines.push(line.slice(5).trimStart());
          }
          if(lines.length) onEvent(event,JSON.parse(lines.join('\n')));
        }
        if(done) break;
      }
    } finally { try { await reader.cancel(); } catch {} reader.releaseLock(); }
  }
  async function send(text, retryId) {
    if(pending) return;
    recognition?.stop();
    text=(text ?? $('input').value).trim();
    let user, assistant, file=attachment, history;
    if(retryId) {
      const index=active?.messages.findIndex(m=>m.id===retryId) ?? -1;
      if(index<1) return;
      assistant=active.messages[index]; user=active.messages[index-1];
      file=retryFiles.get(user.id) || null;
      if(user.imageName && !file) { notice('Please reattach the image and send your question again.'); return; }
      text=user.text; history=requestHistory(active.messages.slice(0,index-1));
    } else {
      if(!text && !file) return;
      if(!active) { active={id:uid(),title:text.slice(0,80) || 'Image conversation',messages:[]}; sessions.push(active); }
      history=requestHistory(active.messages);
      user={id:uid(),role:'user',text:text || 'Please review this image.',language:$('language').value};
      if(file) { user.imageName=file.name; user.imageURL=URL.createObjectURL(file); imageURLs.add(user.imageURL); retryFiles.set(user.id,file); }
      assistant={id:uid(),role:'assistant',text:'',state:'pending',language:user.language || 'en'};
      active.messages.push(user,assistant);
    }
    assistant.text=''; assistant.error=''; assistant.state='pending'; assistant.status='Thinking';
    const request={controller:new AbortController(),assistant}; pending=request;
    $('input').value=''; $('input').style.height=''; setAttachment(null); $('file').value=''; setMenu(false); notice('');
    renderConversation(); persist();
    const form=new FormData(); form.append('message',text || 'Please review this image.'); form.append('history',JSON.stringify(history));
    if(file) form.append('image',file); if(user.language) form.append('language',user.language);
    let receivedDone=false, timedOut=false, renderFrame=0;
    const deadline=setTimeout(()=>{timedOut=true;request.controller.abort();},100000);
    const paint=()=>{ if(!renderFrame) renderFrame=requestAnimationFrame(()=>{renderFrame=0;if(pending===request)updateMessage(assistant);}); };
    try {
      const response=await fetch('/chat/stream',{method:'POST',body:form,signal:request.controller.signal});
      if(!response.ok) {
        const data=await response.json().catch(()=>({}));
        throw new Error(typeof data.detail==='string' ? data.detail : 'The request could not be processed. Please try again.');
      }
      await readEvents(response,(event,data)=>{
        if(pending!==request) return;
        if(event==='status') { assistant.status=data.text; paint(); }
        if(event==='delta') { assistant.text+=data.text; paint(); }
        if(event==='error') throw new Error(data.message);
        if(event==='done') {
          receivedDone=true; assistant.text=data.text; assistant.sources=data.sources;
          assistant.language=data.language; assistant.state='complete';
          if(data.type==='location') assistant.location={latitude:data.latitude,longitude:data.longitude};
        }
      });
      if(!receivedDone) throw new Error('The connection ended before the reply was complete. Please try again.');
      if(autoRead) speak(assistant.text,assistant.language);
    } catch(error) {
      if(pending!==request) return;
      assistant.state='error'; assistant.error=timedOut ? 'The response timed out. Please try again.' : error.message || 'Unable to connect. Please try again.';
    } finally {
      clearTimeout(deadline); cancelAnimationFrame(renderFrame);
      if(pending===request) { pending=null; updateMessage(assistant); persist(); controls(); }
    }
  }
  function speak(text,language) {
    if(!('speechSynthesis' in window)) { notice('Reading aloud is not supported in this browser.'); return; }
    speechSynthesis.cancel(); const utterance=new SpeechSynthesisUtterance(text); utterance.lang=speechLanguages[language] || 'en-IN';
    utterance.onerror=()=>notice('The response could not be read aloud.'); speechSynthesis.speak(utterance);
  }
  function toggleMic() {
    if(listening) { recognition.stop(); return; }
    const API=window.SpeechRecognition || window.webkitSpeechRecognition;
    if(!API) { notice('Voice input is unavailable in this browser. Use Chrome or Edge, or type your message.'); return; }
    recognition=new API(); recognition.lang=speechLanguages[$('language').value] || 'en-IN'; recognition.interimResults=false;
    recognition.onstart=()=>{listening=true;$('mic').setAttribute('aria-pressed','true');notice('Listening...');};
    recognition.onresult=event=>{$('input').value=event.results[0][0].transcript;controls();notice('Voice captured. Send when ready.');};
    recognition.onerror=event=>notice(event.error==='not-allowed' ? 'Microphone permission was denied. You can still type your message.' : 'Voice input did not complete. Please try again.');
    recognition.onend=()=>{listening=false;$('mic').setAttribute('aria-pressed','false');};
    try { recognition.start(); } catch { notice('Voice input could not start. Please try again.'); }
  }
  async function checkHealth() {
    try {
      const response=await fetch('/health',{signal:AbortSignal.timeout(5000)}); if(!response.ok) throw new Error(); const health=await response.json();
      $('connection').dataset.state=health.configured ? 'ready' : 'setup'; $('connection-label').textContent=health.configured ? 'Groq configured' : 'Setup needed';
      $('setup').hidden=health.configured; $('setup').textContent=health.configured ? '' : 'The assistant is waiting for its Groq connection. Add the server API key to enable AI replies.';
    } catch { $('connection').dataset.state='offline';$('connection-label').textContent='Offline'; }
  }
  $('form').addEventListener('submit',event=>{event.preventDefault();if(pending)stopResponse();else send();});
  $('input').addEventListener('input',()=>{ $('input').style.height='auto';$('input').style.height=Math.min($('input').scrollHeight,150)+'px';controls(); });
  $('input').addEventListener('keydown',event=>{if(event.key==='Enter' && !event.shiftKey && !event.isComposing){event.preventDefault();if(!pending)send();}});
  $('new').addEventListener('click',newConversation);
  $('menu').addEventListener('click',()=>setMenu(root.dataset.menu!=='open'));
  $('backdrop').addEventListener('click',()=>{setMenu(false);$('menu').focus();});
  document.addEventListener('keydown',event=>{if(event.key==='Escape'){setMenu(false);if(listening)recognition.stop();}});
  window.matchMedia('(max-width:550px)').addEventListener('change',()=>setMenu(false));
  $('attach').addEventListener('click',()=>$('file').click());
  $('review').addEventListener('click',()=>{$('input').value='Please review this project brief.';controls();$('file').click();});
  $('file').addEventListener('change',()=>{
    const file=$('file').files[0];if(!file)return;
    if(!['image/png','image/jpeg','image/webp'].includes(file.type)){notice('Choose a PNG, JPEG, or WebP image.');$('file').value='';return;}
    if(file.size>4*1024*1024){notice('Please attach an image smaller than 4 MB.');$('file').value='';return;}
    setAttachment(file);notice('');
  });
  $('remove').addEventListener('click',()=>{setAttachment(null);$('file').value='';});
  $('mic').addEventListener('click',toggleMic);
  $('read').addEventListener('click',()=>{autoRead=!autoRead;$('read').setAttribute('aria-pressed',String(autoRead));if(!autoRead)window.speechSynthesis?.cancel();notice(autoRead ? 'New replies will be read aloud.' : 'Read aloud is off.');});
  root.querySelectorAll('[data-prompt]').forEach(button=>button.addEventListener('click',()=>send(button.dataset.prompt)));
  $('scroll').addEventListener('scroll',()=>{const el=$('scroll');followBottom=el.scrollHeight-el.scrollTop-el.clientHeight<100;$('jump').hidden=followBottom;});
  $('jump').addEventListener('click',()=>scrollBottom(true));
  $('thread').addEventListener('click',async event=>{
    const article=event.target.closest('.sw-message'); if(!article)return;
    const message=active?.messages.find(m=>m.id===article.dataset.id);if(!message)return;
    if(event.target.closest('[data-retry]')){send('',message.id);return;}
    if(event.target.closest('[data-copy]')){try{await navigator.clipboard.writeText(message.text);notice('Response copied.');}catch{notice('Copy is unavailable. You can select the response text.');}}
    if(event.target.closest('[data-speak]'))speak(message.text,message.language);
  });
  $('delete').addEventListener('click',()=>$('confirm').showModal());
  $('cancel-delete').addEventListener('click',()=>$('confirm').close());
  $('confirm-delete').addEventListener('click',()=>{
    stopResponse();const removed=active;sessions=sessions.filter(s=>s!==removed);
    removed?.messages.forEach(m=>{retryFiles.delete(m.id);if(m.imageURL){URL.revokeObjectURL(m.imageURL);imageURLs.delete(m.imageURL);}});
    $('confirm').close();newConversation();
  });
  window.addEventListener('pagehide',()=>{stopResponse();recognition?.stop();window.speechSynthesis?.cancel();imageURLs.forEach(url=>URL.revokeObjectURL(url));});
  restore();setMenu(false);renderConversation();checkHealth();
})();
