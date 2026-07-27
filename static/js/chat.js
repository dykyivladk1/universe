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

