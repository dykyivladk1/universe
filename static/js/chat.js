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

