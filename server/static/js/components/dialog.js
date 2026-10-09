const focusableSelector = [
  'a[href]',
  'button:not(:disabled)',
  'input:not(:disabled)',
  'select:not(:disabled)',
  'textarea:not(:disabled)',
  '[tabindex]:not([tabindex="-1"])',
].join(',');

document.addEventListener('keydown', event => {
  if (event.key !== 'Tab') return;

  const dialog = document.querySelector('dialog[open]');
  if (!(dialog instanceof HTMLDialogElement)) return;

  const focusable = [...dialog.querySelectorAll(focusableSelector)]
    .filter(element => element.getClientRects().length > 0);
  if (focusable.length === 0) {
    event.preventDefault();
    dialog.focus();
    return;
  }

  const first = focusable[0];
  const last = focusable.at(-1);
  if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
    event.preventDefault();
    last.focus();
  } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
    event.preventDefault();
    first.focus();
  }
}, true);

document.addEventListener('click', event => {
  if (!(event.target instanceof Element)) return;

  const trigger = event.target.closest('[data-dialog-open]');
  if (trigger instanceof HTMLElement) {
    const dialog = document.getElementById(trigger.dataset.dialogOpen);
    if (dialog instanceof HTMLDialogElement && !dialog.open) {
      dialog.addEventListener('close', () => {
        if (trigger.isConnected) trigger.focus();
      }, { once: true });
      dialog.showModal();
    }
    return;
  }

  const closeButton = event.target.closest('[data-dialog-close]');
  const dialog = closeButton?.closest('dialog');
  if (dialog instanceof HTMLDialogElement && dialog.open) dialog.close();
});