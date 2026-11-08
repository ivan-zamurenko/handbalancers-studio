import {beginLoading} from './loading.js';

const pendingForms = new WeakSet();

document.addEventListener('submit', async event => {
  const form = event.target;
  if (!(form instanceof HTMLFormElement) || !form.matches('[data-pending-form]')) return;

  event.preventDefault();
  if (pendingForms.has(form)) return;

  const submitter = event.submitter instanceof HTMLButtonElement
    ? event.submitter
    : form.querySelector('button[type="submit"]');
  if (!(submitter instanceof HTMLButtonElement)) return;

  pendingForms.add(form);
  const initialLabel = submitter.textContent;
  const wasDisabled = submitter.disabled;
  const feedback = form.querySelector('[data-form-feedback]');
  submitter.disabled = true;
  if (submitter.dataset.pendingLabel) submitter.textContent = submitter.dataset.pendingLabel;
  form.setAttribute('aria-busy', 'true');
  if (feedback instanceof HTMLElement) {
    feedback.textContent = '';
    feedback.hidden = true;
  }

  const finishLoading = beginLoading();
  try {
    const method = form.method.toUpperCase();
    const destination = new URL(form.action, document.baseURI);
    const body = new FormData(form, submitter);
    const options = { method, headers: { Accept: 'application/json' } };
    if (method === 'GET') {
      for (const [name, value] of body.entries()) {
        if (typeof value === 'string') destination.searchParams.append(name, value);
      }
    } else {
      options.body = body;
    }

    const response = await fetch(destination, options);
    if (!response.ok) throw new Error('Request failed');
    form.dispatchEvent(new CustomEvent('form:success', {
      bubbles: true,
      detail: { response },
    }));
  } catch {
    if (feedback instanceof HTMLElement) {
      feedback.textContent = form.dataset.failureMessage || 'Could not submit. Please try again.';
      feedback.hidden = false;
    }
  } finally {
    finishLoading();
    pendingForms.delete(form);
    form.removeAttribute('aria-busy');
    submitter.disabled = wasDisabled;
    submitter.textContent = initialLabel;
  }
});
