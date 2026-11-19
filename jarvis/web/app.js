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
      await history();
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
  try { await call('/api/logout','POST');$('reply-panel').hidden=true;state('Signed out.');await refresh(); }
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
