// Shared helpers + chat logic, used by the full chat page and by the builder playground.

function escapeHtml(str) {
  return String(str ?? '').replace(/[&<>"']/g, m => ({
    '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
  })[m]);
}

function renderMarkdown(text) {
  return marked.parse(text || '');
}

// keep in sync with avatar_color() in app.py
function avatarColor(id) {
  let sum = 0;
  for (const ch of id) sum += ch.charCodeAt(0);
  return 'av-' + (sum % 8);
}

function initials(name) {
  return (name || '?').split(/\s+/).slice(0, 2).map(w => w[0]).join('').toUpperCase();
}

function avatarHtml(id, name, size = '') {
  if (id && id.startsWith('team:')) {
    return `<span class="avatar ${size} av-team"><i class="fas fa-users"></i></span>`;
  }
  return `<span class="avatar ${size} ${avatarColor(id || name || '')}">${escapeHtml(initials(name))}</span>`;
}

async function api(url, options = {}) {
  const res = await fetch(url, {
    headers: { 'Content-Type': 'application/json' },
    ...options,
    body: options.body ? JSON.stringify(options.body) : undefined,
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
  return data;
}

function addCopyButtonsToCodeBlocks(container) {
  container.querySelectorAll('pre code').forEach(codeBlock => {
    const pre = codeBlock.parentNode;
    if (pre.querySelector('.code-copy-btn')) return;
    const btn = document.createElement('button');
    btn.className = 'code-copy-btn';
    btn.innerHTML = '<i class="fas fa-copy"></i> Copy';
    btn.addEventListener('click', () => {
      navigator.clipboard.writeText(codeBlock.textContent).then(() => {
        btn.innerHTML = '<i class="fas fa-check"></i> Copied';
        setTimeout(() => { btn.innerHTML = '<i class="fas fa-copy"></i> Copy'; }, 2000);
      });
    });
    pre.appendChild(btn);
  });
}

function polish(el) {
  Prism.highlightAllUnder(el);
  addCopyButtonsToCodeBlocks(el);
}

/*
  opts:
    messagesEl, inputEl, sendBtn, stopBtn  - dom elements
    getTarget()     -> 'agent:coder' / 'team:dev-team'
    getThread()     -> history thread id (optional, defaults to target)
    agentInfo(id)   -> {name, model} for the avatar + name above answers
    empty()         -> {title, text, suggestions: []} for the empty state
    beforeSend()    -> optional async hook, return false to cancel sending
*/
function createChat(opts) {
  const { messagesEl, inputEl, sendBtn, stopBtn } = opts;
  const getThread = opts.getThread || opts.getTarget;
  let busy = false;
  let source = null;

  // messages live in a centered column inside the scroll area
  const inner = document.createElement('div');
  inner.className = 'chat-inner';
  messagesEl.appendChild(inner);

  const scrollDown = () => { messagesEl.scrollTop = messagesEl.scrollHeight; };

  // for a single agent every answer is from that agent,
  // for teams the server tells us who is talking
  function defaultAgentId() {
    const target = opts.getTarget();
    return target.startsWith('agent:') ? target.slice(6) : null;
  }

  function showEmpty() {
    if (inner.children.length || !opts.empty) return;
    const e = opts.empty();
    const suggestions = (e.suggestions || [])
      .map(s => `<button class="suggestion">${escapeHtml(s)}</button>`)
      .join('');
    inner.innerHTML = `
      <div class="chat-empty">
        ${avatarHtml(opts.getTarget().startsWith('team:') ? opts.getTarget() : defaultAgentId(), e.title, 'lg')}
        <h3>${escapeHtml(e.title)}</h3>
        <p>${escapeHtml(e.text || '')}</p>
        <div class="suggestions">${suggestions}</div>
      </div>`;
  }

  inner.addEventListener('click', e => {
    const s = e.target.closest('.suggestion');
    if (s) send(s.textContent);
  });

  function addMessage(role, content, agentId = null) {
    inner.querySelector('.chat-empty')?.remove();

    const message = document.createElement('div');
    message.className = `message message-${role}`;

    if (role === 'assistant') {
      const info = (agentId && opts.agentInfo(agentId)) || { name: 'Assistant', model: '' };
      message.innerHTML = `
        ${avatarHtml(agentId, info.name, 'md')}
        <div class="body">
          <div class="who">${escapeHtml(info.name)} <span class="model">${escapeHtml(info.model || '')}</span></div>
          <div class="message-content markdown-content"></div>
        </div>`;
    } else {
      message.innerHTML = `<div class="body"><div class="message-content markdown-content"></div></div>`;
    }

    message.querySelector('.message-content').innerHTML = renderMarkdown(content);
    message.insertAdjacentHTML('beforeend',
      '<div class="message-actions"><button class="copy-message" title="Copy"><i class="fas fa-copy"></i></button></div>');

    inner.appendChild(message);
    scrollDown();
    return message;
  }

  inner.addEventListener('click', e => {
    const btn = e.target.closest('.copy-message');
    if (!btn) return;
    const text = btn.closest('.message').querySelector('.message-content').textContent;
    navigator.clipboard.writeText(text);
    btn.innerHTML = '<i class="fas fa-check"></i>';
    setTimeout(() => { btn.innerHTML = '<i class="fas fa-copy"></i>'; }, 1500);
  });

  function showTyping() {
    const el = document.createElement('div');
    el.className = 'typing-indicator';
    el.innerHTML = '<div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div>';
    inner.appendChild(el);
    scrollDown();
  }

  function hideTyping() {
    inner.querySelectorAll('.typing-indicator').forEach(el => el.remove());
  }

  function setBusy(value) {
    busy = value;
    stopBtn?.classList.toggle('d-none', !value);
    sendBtn.classList.toggle('d-none', value && !!stopBtn);
    sendBtn.disabled = value || !inputEl.value.trim();
  }

  async function loadHistory() {
    inner.innerHTML = '';
    const data = await api('/chat/history/' + encodeURIComponent(getThread()));
    (data.chat?.messages || []).forEach(m => {
      const el = addMessage(m.role, m.content, m.agent || defaultAgentId());
      if (m.role === 'assistant') polish(el);
    });
    showEmpty();
    scrollDown();
  }

  async function clear() {
    if (busy) return;
    await api('/chat/clear/' + encodeURIComponent(getThread()), { method: 'POST' });
    inner.innerHTML = '';
    showEmpty();
  }

  async function send(text) {
    text = (text ?? inputEl.value).trim();
    if (!text || busy) return;

    // builder uses this to save unsaved changes before testing
    if (opts.beforeSend) {
      setBusy(true);
      const ok = await opts.beforeSend();
      setBusy(false);
      if (!ok) return;
    }

    addMessage('user', text);
    inputEl.value = '';
    inputEl.dispatchEvent(new Event('input'));
    setBusy(true);
    showTyping();

    const params = new URLSearchParams({ message: text, target: opts.getTarget(), thread: getThread() });
    source = new EventSource('/chat?' + params);

    // one bubble per agent turn, teams can have a few
    let bubble = null;
    let buffer = '';

    function newBubble(agentId) {
      if (bubble) polish(bubble);
      hideTyping();
      bubble = addMessage('assistant', '', agentId || defaultAgentId());
      buffer = '';
    }

    function finish() {
      source?.close();
      source = null;
      hideTyping();
      if (bubble) polish(bubble);
      setBusy(false);
      inputEl.focus();
    }

    source.onmessage = event => {
      const data = JSON.parse(event.data);

      if (data.type === 'agent') {
        newBubble(data.agent);
      } else if (data.type === 'tool') {
        if (!bubble) newBubble(null);
        const note = document.createElement('span');
        note.className = 'tool-note';
        note.innerHTML = `<i class="fas fa-bolt"></i>${escapeHtml(data.tool)}`;
        bubble.querySelector('.message-content').before(note);
      } else if (data.type === 'token') {
        if (!bubble) newBubble(null);
        buffer += data.text;
        bubble.querySelector('.message-content').innerHTML = renderMarkdown(buffer);
        scrollDown();
      } else if (data.type === 'error') {
        if (!bubble) newBubble(null);
        bubble.querySelector('.message-content').innerHTML =
          `<span style="color: var(--danger)"><i class="fas fa-triangle-exclamation me-1"></i>${escapeHtml(data.error)}</span>`;
      }

      if (data.done) finish();
    };

    source.onerror = () => {
      if (!bubble) newBubble(null);
      if (!buffer) {
        bubble.querySelector('.message-content').textContent = 'Something went wrong, check the server log.';
      }
      finish();
    };
  }

  function stop() {
    if (!source) return;
    source.close();
    source = null;
    hideTyping();
    setBusy(false);
  }

  // input behaviour: autogrow, Enter sends, Shift+Enter new line
  inputEl.addEventListener('input', () => {
    inputEl.style.height = 'auto';
    inputEl.style.height = inputEl.scrollHeight + 'px';
    sendBtn.disabled = busy || !inputEl.value.trim();
  });
  inputEl.addEventListener('keydown', e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  });
  sendBtn.addEventListener('click', () => send());
  stopBtn?.addEventListener('click', stop);

  return { send, stop, clear, loadHistory, isBusy: () => busy };
}
