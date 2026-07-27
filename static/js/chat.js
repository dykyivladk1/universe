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

