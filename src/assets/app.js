// Static website only. Customer data is entered and handled inside Google's form.
const toggle = document.querySelector('.menu-toggle');
const nav = document.getElementById('navigation');
if (toggle && nav) {
  const close = () => { toggle.setAttribute('aria-expanded', 'false'); nav.classList.remove('is-open'); };
  toggle.addEventListener('click', () => {
    const open = toggle.getAttribute('aria-expanded') !== 'true';
    toggle.setAttribute('aria-expanded', String(open)); nav.classList.toggle('is-open', open);
  });
  nav.addEventListener('click', e => { if (e.target.closest('a')) close(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape' && nav.classList.contains('is-open')) { close(); toggle.focus(); } });
  document.addEventListener('click', e => { if (!e.target.closest('.header-inner')) close(); });
}
// The local fallback stays inert, including when opened without a server.
document.getElementById('inquiry-form')?.addEventListener('submit', e => e.preventDefault());
const frame = document.getElementById('google-inquiry');
if (frame) {
  const status = document.getElementById('google-form-status');
  if (location.protocol !== 'https:' || location.origin !== frame.dataset.origin) {
    status.textContent = '이 화면에서는 전화로 문의해 주세요.';
  } else {
    const channel = crypto.randomUUID();
    const url = new URL(frame.dataset.url);
    url.searchParams.set('embed', '1'); url.searchParams.set('channel', channel);
    frame.src = url.href;
    const timeout = setTimeout(() => {
      if (frame.hidden) status.textContent = '문의창을 불러오지 못했습니다. 페이지를 새로고침하거나 전화로 문의해 주세요.';
    }, 20000);
    window.addEventListener('message', e => {
      const googleOrigin = e.origin === 'https://script.google.com' || /^https:\/\/[a-z0-9-]+\.googleusercontent\.com$/.test(e.origin);
      const data = e.data;
      if (!googleOrigin || !data || data.channel !== channel) return;
      if (data.type === 'ok-express-form-ready') { clearTimeout(timeout); frame.hidden = false; status.textContent = ''; }
      if (data.type === 'ok-express-form-height' && Number.isFinite(data.height)) frame.style.height = `${Math.max(360, Math.min(1900, data.height + 65))}px`;
      if (data.type === 'ok-express-form-focus') document.body.classList.toggle('keyboard-open', data.active === true);
      if (data.type === 'ok-express-form-saved') { document.body.classList.remove('keyboard-open'); frame.scrollIntoView({ block: 'start', behavior: 'smooth' }); }
    });
    document.addEventListener('focusin', () => {
      if (document.activeElement !== frame) document.body.classList.remove('keyboard-open');
    });
  }
}
