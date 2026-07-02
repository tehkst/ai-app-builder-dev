from __future__ import annotations


def render_board_room_js() -> str:
    return r'''
window.addEventListener('DOMContentLoaded', function () {
  let token = localStorage.getItem('mission_control_token') || '';
  let meetingId = localStorage.getItem('board_room_meeting_id') || ('BR-' + Date.now());
  localStorage.setItem('board_room_meeting_id', meetingId);
  let messages = JSON.parse(localStorage.getItem('board_room_messages') || '[]');
  const loginScreen = document.getElementById('loginScreen');
  const app = document.getElementById('app');
  const loginError = document.getElementById('loginError');
  const loginBtn = document.getElementById('loginBtn');
  const thread = document.getElementById('thread');
  const msgBox = document.getElementById('message');
  const sendBtn = document.getElementById('sendBtn');

  function post(url, body) {
    return fetch(url, { method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body) }).then(r => r.json());
  }
  function save() { localStorage.setItem('board_room_messages', JSON.stringify(messages)); }
  function showApp() { loginScreen.style.display = 'none'; app.style.display = 'grid'; renderThread(); updateMinutes(); }
  function showLogin() { loginScreen.style.display = 'grid'; app.style.display = 'none'; }
  function escapeHtml(s) { return String(s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }
  function initials(role) { return role.split(' ').map(x => x[0]).join('').slice(0,3); }
  function klass(role) { if (role === 'Founder') return 'founder'; if (role === 'Corporate Secretary') return 'corpsec'; return 'board'; }

  window.login = async function () {
    loginError.textContent = '';
    loginBtn.disabled = true;
    loginBtn.textContent = 'Signing in...';
    try {
      const data = await post('/mission-control/auth/login', {email: document.getElementById('email').value, password: document.getElementById('password').value});
      if (data.session && data.session.token) {
        token = data.session.token;
        localStorage.setItem('mission_control_token', token);
        showApp();
      } else {
        loginError.textContent = data.status || data.error || 'Login failed';
      }
    } catch (error) {
      loginError.textContent = 'Login failed: ' + error;
    } finally {
      loginBtn.disabled = false;
      loginBtn.textContent = 'Enter Board Room';
    }
  };
  loginBtn.addEventListener('click', window.login);

  async function validateSession() {
    if (!token) { showLogin(); return; }
    const data = await post('/mission-control/auth/session', {token});
    if (data.authenticated) showApp();
    else { localStorage.removeItem('mission_control_token'); token = ''; showLogin(); }
  }
  window.logout = function () { token = ''; localStorage.removeItem('mission_control_token'); showLogin(); };

  function addMessage(role, text) {
    messages.push({role, text, time: new Date().toLocaleTimeString()});
    save(); renderThread(); updateMinutes();
  }
  function renderThread() {
    thread.innerHTML = '';
    if (messages.length === 0) {
      messages.push({role:'Corporate Secretary', text:'Meeting opened. INT-01 Company Intelligence is loaded. Ask the Board Room to begin.', time:new Date().toLocaleTimeString()});
      save();
    }
    messages.forEach(m => {
      const div = document.createElement('div');
      div.className = 'msg';
      div.innerHTML = '<div class="avatar ' + klass(m.role) + '">' + initials(m.role) + '</div><div class="bubble"><div class="speaker"><strong>' + escapeHtml(m.role) + '</strong><span class="small">' + escapeHtml(m.time) + '</span></div>' + escapeHtml(m.text).replace(/\n/g, '<br>') + '</div>';
      thread.appendChild(div);
    });
    thread.scrollTop = thread.scrollHeight;
  }

  function splitBoardResponse(text) {
    const roles = ['AI CEO','AI CTO','Product Manager','Engineering Manager','QA Lead','DevOps Lead','Security Advisor','Corporate Secretary'];
    let added = false;
    roles.forEach(role => {
      const re = new RegExp(role + '[:\\n]([\\s\\S]*?)(?=AI CEO|AI CTO|Product Manager|Engineering Manager|QA Lead|DevOps Lead|Security Advisor|Corporate Secretary|$)', 'i');
      const match = text.match(re);
      if (match && match[1].trim()) { addMessage(role, match[1].trim()); added = true; }
    });
    if (!added) addMessage('Board Room', text);
  }

  window.sendMessage = async function () {
    const text = msgBox.value.trim();
    if (!text) return;
    msgBox.value = '';
    addMessage('Founder', text);
    sendBtn.disabled = true;
    sendBtn.textContent = 'Thinking...';
    try {
      const prompt = 'Continuing Board Room meeting ' + meetingId + '\n\nRecent messages:\n' + messages.slice(-10).map(m => m.role + ': ' + m.text).join('\n\n') + '\n\nLatest Founder message:\n' + text;
      const data = await post('/mission-control/operating-console/chat', {token, meeting_id: meetingId, message: prompt});
      splitBoardResponse(data.board_room_response || JSON.stringify(data, null, 2));
    } catch (error) {
      addMessage('Corporate Secretary', 'Board Room request failed: ' + error);
    } finally {
      sendBtn.disabled = false;
      sendBtn.textContent = 'Send';
    }
  };

  window.focusComposer = function (text) { msgBox.value = text; msgBox.focus(); };
  window.seedAudit = function () {
    focusComposer('Board Room Meeting\n\nThis is now the primary operating environment for AI Software Factory.\n\nPerform an audit-only Mission Control architectural review. Cover: current system architecture, existing capabilities, missing capabilities, duplicate functionality, unfinished work, disconnected workflows, placeholder implementations, UI inconsistencies, architecture debt, risks and guardrails, and estimated completion toward full autonomy.\n\nDo not implement anything yet. Ask for founder approval before producing execution proposals.');
  };

  function collect(words) {
    const found = [];
    messages.forEach(m => words.forEach(w => { if (m.text.toLowerCase().includes(w) && found.length < 6) found.push(m.text.split('\n')[0].slice(0, 180)); }));
    return [...new Set(found)];
  }
  function renderList(id, items, fallback) { document.getElementById(id).innerHTML = (items.length ? items : [fallback]).map(x => '<li>' + escapeHtml(x) + '</li>').join(''); }
  function updateMinutes() {
    renderList('decisions', collect(['approve','decision','recommendation','founder decision']), 'No decision yet.');
    renderList('actions', collect(['next action','action','proposal','audit report','implement']), 'No action item yet.');
    renderList('risks', collect(['risk','guardrail','blocked','security','approval']), 'Execution requires founder approval.');
    const record = messages.map(m => '[' + m.time + '] ' + m.role + ': ' + m.text).join('\n\n');
    document.getElementById('meetingRecord').textContent = record || 'Waiting...';
    const approval = messages.find(m => /approve|approval|founder decision required|audit report/i.test(m.text));
    document.getElementById('approveBtn').disabled = !approval;
    document.getElementById('approvalText').textContent = approval ? 'Approval opportunity detected from discussion.' : 'No approval detected yet.';
  }
  window.approveCurrentMeeting = async function () {
    addMessage('Founder', 'Approved. Create a proposal from the current meeting minutes. Keep execution blocked until explicit founder approval.');
    try {
      const data = await post('/mission-control/operating-console/workflow', {token, action:'create-proposal', message: document.getElementById('meetingRecord').textContent});
      addMessage('Corporate Secretary', 'Approval routed to workflow. Status: ' + (data.status || 'created') + '\nNext step: ' + (data.next_step || 'Review proposal.'));
    } catch (error) { addMessage('Corporate Secretary', 'Approval routing failed: ' + error); }
  };
  window.newMeeting = function () { meetingId = 'BR-' + Date.now(); localStorage.setItem('board_room_meeting_id', meetingId); messages = []; save(); renderThread(); updateMinutes(); };
  window.copyMinutes = function () { navigator.clipboard.writeText(document.getElementById('meetingRecord').textContent); };
  validateSession();
});
'''
