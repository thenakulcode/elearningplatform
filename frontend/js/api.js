// ── API Client ────────────────────────────────────────────────────────────────
const IS_LOCAL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1';
const BASE = IS_LOCAL ? 'http://localhost:8000' : window.location.origin;
const LOGIN_PATH = window.location.pathname.includes('/frontend/') ? '/frontend/index.html' : '/index.html';

const api = {
  _token: () => localStorage.getItem('alp_token'),

  async req(method, path, body = null) {
    const headers = { 'Content-Type': 'application/json' };
    const token = this._token();
    if (token) headers['Authorization'] = `Bearer ${token}`;
    const opts = { method, headers };
    if (body) opts.body = JSON.stringify(body);
    const res = await fetch(BASE + path, opts);
    if (res.status === 401) {
      localStorage.removeItem('alp_token');
      localStorage.removeItem('alp_user');
      window.location.href = LOGIN_PATH;
      return;
    }
    const data = await res.json().catch(() => ({}));
    if (!res.ok) throw new Error(data.detail || 'Request failed');
    return data;
  },

  get:    (path)        => api.req('GET',    path),
  post:   (path, body)  => api.req('POST',   path, body),
  patch:  (path, body)  => api.req('PATCH',  path, body),
  delete: (path)        => api.req('DELETE', path),

  // Auth
  register: (d) => api.post('/api/auth/register', d),
  login:    (d) => api.post('/api/auth/login', d),
  me:       ()  => api.get('/api/auth/me'),

  // Courses
  courses:       ()        => api.get('/api/courses'),
  course:        (id)      => api.get(`/api/courses/${id}`),
  enroll:        (id)      => api.post(`/api/courses/enroll/${id}`),
  createCourse:  (d)       => api.post('/api/courses', d),
  // Admin
adminCourses: () => api.get('/api/courses/admin/all'),
  publishCourse: (id)      => api.patch(`/api/courses/${id}/publish`),
  addModule:     (cid, d)  => api.post(`/api/courses/${cid}/modules`, d),
  addLesson:     (mid, d)  => api.post(`/api/courses/modules/${mid}/lessons`, d),

  // Quiz
  quiz:       (lessonId)    => api.get(`/api/quiz/lesson/${lessonId}`),
  submitQuiz: (d)           => api.post('/api/quiz/submit', d),
  addQuestion:(lessonId, d) => api.post(`/api/quiz/questions?lesson_id=${lessonId}`, d),

  // Progress
  updateProgress: (d)   => api.post('/api/progress/lesson', d),
  courseProgress: (id)  => api.get(`/api/progress/course/${id}`),
  dashboard:      ()    => api.get('/api/progress/dashboard'),
};

// ── Auth helpers ──────────────────────────────────────────────────────────────
function saveSession(token, user) {
  localStorage.setItem('alp_token', token);
  localStorage.setItem('alp_user',  JSON.stringify(user));
}

function getUser() {
  try { return JSON.parse(localStorage.getItem('alp_user')); }
  catch { return null; }
}

function requireAuth(redirectTo = LOGIN_PATH) {
  if (!localStorage.getItem('alp_token')) {
    window.location.href = redirectTo;
    return null;
  }
  return getUser();
}

function logout() {
  localStorage.removeItem('alp_token');
  localStorage.removeItem('alp_user');
  window.location.href = LOGIN_PATH;
}

// ── Toast ─────────────────────────────────────────────────────────────────────
function toast(msg, type = 'info', duration = 3500) {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const icons = { success: '✅', error: '❌', info: 'ℹ️', warning: '⚠️' };
  const t = document.createElement('div');
  t.className = `toast ${type}`;
  t.innerHTML = `<span>${icons[type] || '💬'}</span><span>${msg}</span>`;
  container.appendChild(t);
  setTimeout(() => t.remove(), duration);
}

// ── Skill ring (canvas) ───────────────────────────────────────────────────────
function drawSkillRing(canvas, value, color = '#6c63ff') {
  const ctx  = canvas.getContext('2d');
  const size = canvas.width;
  const cx   = size / 2, cy = size / 2, r = size / 2 - 10;
  ctx.clearRect(0, 0, size, size);
  // track
  ctx.beginPath();
  ctx.arc(cx, cy, r, 0, Math.PI * 2);
  ctx.strokeStyle = '#2e3460';
  ctx.lineWidth   = 10;
  ctx.stroke();
  // fill
  const end = -Math.PI / 2 + (value / 100) * Math.PI * 2;
  ctx.beginPath();
  ctx.arc(cx, cy, r, -Math.PI / 2, end);
  ctx.strokeStyle = color;
  ctx.lineWidth   = 10;
  ctx.lineCap     = 'round';
  ctx.stroke();
}

// ── Sidebar active link ───────────────────────────────────────────────────────
function setActiveNav() {
  const links = document.querySelectorAll('.sidebar nav a');
  links.forEach(a => {
    if (a.href === window.location.href) a.classList.add('active');
  });
}
