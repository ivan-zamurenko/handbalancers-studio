// UI preview only. Real submission requires the server session and CSRF flow.
const form = document.getElementById('login-form');
form?.addEventListener('submit', event => event.preventDefault());
const password = document.getElementById('login-password');
const toggle = document.querySelector('[data-password-toggle]');
if (password && toggle) {
  toggle.disabled = false;
  toggle.addEventListener('click', () => {
    const visible = password.type === 'password';
    password.type = visible ? 'text' : 'password';
    toggle.setAttribute('aria-pressed', String(visible));
    toggle.textContent = visible ? toggle.dataset.hide : toggle.dataset.show;
  });
}
for (const control of document.querySelectorAll('[data-login-interactive]')) control.disabled = false;
// A browser history entry must not keep the preview password visible or populated.
window.addEventListener('pagehide', () => {
  if (password) { password.value = ''; password.type = 'password'; }
  if (toggle) { toggle.setAttribute('aria-pressed', 'false'); toggle.textContent = toggle.dataset.show; }
});
