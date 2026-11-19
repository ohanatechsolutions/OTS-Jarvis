'use strict';
const $ = id => document.getElementById(id);
function state(message, error=false) {
  $('status').textContent = message;
  $('status').classList.toggle('error', error);
}
async function call(path, method='GET', data) {
  let response;
  try {
    response = await fetch(path, {method, credentials:'same-origin', headers:data ? {'Content-Type':'application/json'} : {}, body:data ? JSON.stringify(data) : undefined});
  } catch (_) { throw new Error('Jarvis server unavailable. Check that it is running.'); }
  const body = await response.json();
  if (!response.ok) throw new Error(body.error || `Request failed (${response.status})`);
  return body;
}
function show(section) {
  for (const id of ['setup','login','assistant']) $(id).hidden = id !== section;
  $('logout').hidden = section !== 'assistant';
}
async function refresh() {
  try {
    const data = await call('/api/me');
    if (data.enrollment_required) show('setup');
    else if (!data.user) show('login');
    else {
      $('identity').textContent = data.user.username;
      show('assistant');
      await Promise.all([history(), refreshActions()]);
    }
  } catch (e) { state(e.message, true); }
}
function formData(form) { return Object.fromEntries(new FormData(form).entries()); }
$('setup-form').addEventListener('submit', async e => {
  e.preventDefault();
  try {
    await call('/api/setup','POST',formData(e.target));
    e.target.reset(); state('Administrator created. Sign in to continue.');show('login');
  } catch (err) { state(err.message,true); }
});
$('login-form').addEventListener('submit', async e => {
  e.preventDefault();
  try { await call('/api/login','POST',formData(e.target)); e.target.reset();state('Signed in.');await refresh(); }
  catch (err) { state(err.message,true); }
});
$('logout').addEventListener('click', async () => {
  try { await call('/api/logout','POST');$('reply-panel').hidden=true;$('action-queue').replaceChildren();$('notes').replaceChildren();$('action-audit').replaceChildren();state('Signed out.');await refresh(); }
  catch (err) { state(err.message,true); }
});
$('task-form').addEventListener('submit', async e => {
  e.preventDefault();const button=$('ask');button.disabled=true;state('Waiting for local model…');
  try {
    const data = await call('/api/tasks','POST',formData(e.target));
    $('reply').textContent=data.reply;$('reply-panel').hidden=false;
    state('Local response complete.');await history();
  } catch (err) {state(err.message,true);await history();}
  finally {button.disabled=false;}
});
async function history() {
  try {
    const data = await call('/api/tasks'); const container=$('history');container.replaceChildren();
    if (!data.tasks.length) {container.textContent='No requests yet.';return;}
    for (const task of data.tasks) {
      const article=document.createElement('article');
      const meta=document.createElement('small');meta.textContent=`${new Date(task.created_at*1000).toLocaleString()} · ${task.effort} · ${task.state}`;
      const prompt=document.createElement('p');prompt.textContent=task.prompt;
      article.append(meta,prompt);container.append(article);
    }
  } catch (e) {state(e.message,true);}
}
refresh();

// Local action execution is strictly a separate, explicit user interaction;
// model replies are displayed as plain text and never invoked as tools.
function actionButton(label, onClick, className='secondary') {
  const button = document.createElement('button');
  button.type = 'button'; button.className = className; button.textContent = label;
  button.addEventListener('click', async () => {
    button.disabled = true;
    try { await onClick(); await refreshActions(); }
    catch (err) { state(err.message, true); }
    finally { button.disabled = false; }
  });
  return button;
}
async function decideAction(id, decision) {
  const result = await call('/api/actions/decision', 'POST', {id,decision});
  state(`Action ${id}: ${result.state}.`);
}
async function refreshActions() {
  try {
    const data = await call('/api/actions');
    const pause = $('pause-actions');
    pause.textContent = data.paused ? 'Resume actions' : 'Pause actions';
    pause.setAttribute('aria-pressed', String(data.paused));
    $('propose-note').disabled = data.paused;
    const queue = $('action-queue'); queue.replaceChildren();
    const pending = data.actions.filter(action => action.state === 'pending');
    if (!pending.length) queue.textContent = 'No pending actions.';
    for (const action of pending) {
      const article = document.createElement('article');
      const header = document.createElement('small');
      header.textContent = `Action #${action.id} · local note · expires ${new Date(action.expires_at * 1000).toLocaleTimeString()}`;
      const preview = document.createElement('pre');preview.textContent = action.preview;
      const buttons = document.createElement('div');buttons.className = 'inline-buttons';
      buttons.append(
        actionButton('Approve & save', () => decideAction(action.id,'approve'),'primary'),
        actionButton('Cancel', () => decideAction(action.id,'cancel'))
      );
      article.append(header, preview, buttons);queue.append(article);
    }
    const notes = $('notes');notes.replaceChildren();
    if (!data.notes.length) notes.textContent = 'No saved notes.';
    for (const note of data.notes) {
      const article=document.createElement('article');
      const date=document.createElement('small');date.textContent=new Date(note.created_at*1000).toLocaleString();
      const value=document.createElement('pre');value.textContent=note.text;
      const actionId=note.action_id;
      article.append(date,value);
      if (actionId) article.append(actionButton('Undo save',()=>decideAction(actionId,'undo')));
      notes.append(article);
    }
    const audit = $('action-audit');audit.replaceChildren();
    if (!data.events.length) audit.textContent='No action events.';
    for (const entry of data.events) {
      const line=document.createElement('p');
      line.textContent=`${new Date(entry.created_at*1000).toLocaleString()} · ${entry.action_id ? `#${entry.action_id} · ` : ''}${entry.event.replaceAll('_',' ')}`;
      audit.append(line);
    }
  } catch (err) { state(err.message, true); }
}
$('note-form').addEventListener('submit',async e => {
  e.preventDefault(); const button=$('propose-note');button.disabled=true;
  try {
    const text=$('note-text').value;
    const action=await call('/api/actions/propose','POST',{kind:'save_note',text});
    $('note-text').value='';
    state(`Action #${action.id} proposed. Review its contents below; nothing was saved yet.`);
    await refreshActions();
  } catch (err) { state(err.message,true); }
  finally { if ($('pause-actions').getAttribute('aria-pressed') !== 'true') button.disabled=false; }
});
$('pause-actions').addEventListener('click',async () => {
  const button=$('pause-actions');button.disabled=true;
  const paused=button.getAttribute('aria-pressed')!=='true';
  try {
    await call('/api/actions/pause','POST',{paused});
    state(paused ? 'Action execution paused. Pending actions can still be cancelled.' : 'Action execution resumed.');
    await refreshActions();
  } catch (err) { state(err.message,true); }
  finally {button.disabled=false;}
});
