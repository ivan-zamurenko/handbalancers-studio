import {
  STORAGE_KEY,
  freshData,
  noteKey,
  saveNote,
  finishReview,
  pendingClients,
  latestSession,
} from './data.js';
import { translator, escapeHtml, tool, button, localized } from './ui.js';
import {
  selection,
  noteDraft,
  shell,
  clientPreview,
  clientHeading,
  clientTabs,
  clientContent,
  reviewPanel,
} from './components.js';
import { variants, renderVariant, gallery, directory } from './variants.js';
import {
  programEditor,
  catalogView,
  settingsView,
  ensureEditor,
  handleEditorAction,
  handleEditorInput,
  handleEditorSubmit,
} from './editors.js';

function restore() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    return saved?.schema === 1 &&
      Array.isArray(saved.data?.clients) &&
      Array.isArray(saved.data?.exercises)
      ? saved
      : null;
  } catch {
    return null;
  }
}

const saved = restore();
const requestedVariant = new URLSearchParams(location.search).get('variant');
const state = {
  data: saved?.data || freshData(),
  locale: saved?.locale || 'uk',
  theme: saved?.theme || 'dark',
  variant: variants.some((variant) => variant.id === requestedVariant) ? requestedVariant : '02',
  page: requestedVariant ? 'workspace' : 'gallery',
  clientId: 'emma',
  entryId: null,
  tab: 'overview',
  metric: 'handstand',
  range: 'all',
  visibility: 'client',
  search: '',
  pendingOnly: false,
  drafts: saved?.drafts || {},
};
const app = document.querySelector('#app');
const modal = document.querySelector('#modal');
let opener;
let toastTimeout;

function persist() {
  try {
    localStorage.setItem(
      STORAGE_KEY,
      JSON.stringify({
        schema: 1,
        data: state.data,
        locale: state.locale,
        theme: state.theme,
        drafts: state.drafts,
      }),
    );
    return true;
  } catch {
    return false;
  }
}

function toast(message) {
  const element = document.querySelector('#toast');
  element.textContent = message;
  element.classList.add('visible');
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => element.classList.remove('visible'), 2600);
}

function render() {
  const focused = document.activeElement?.id;
  const focusedAction = app.contains(document.activeElement)
    ? document.activeElement?.dataset.action
    : null;
  const focusedData = focusedAction ? { ...document.activeElement.dataset } : null;
  const caret = ['client-search', 'catalog-search'].includes(focused)
    ? document.activeElement.selectionStart
    : null;
  document.documentElement.lang = state.locale;
  document.documentElement.dataset.theme = state.theme;
  document.documentElement.dataset.variant = state.variant;
  document.querySelector('.skip-link').textContent = translator(state)(
    'До вмісту',
    'Skip to content',
  );
  state.variantName = variants.find((variant) => variant.id === state.variant)[state.locale];
  let content = renderVariant(state);
  if (state.page === 'client-view') content = clientPreview(state);
  if (state.page === 'client-details')
    content = `<main id="workspace-main" class="client-details-page" tabindex="-1"><div class="client-details-main">${clientHeading(state)}${clientTabs(state)}${clientContent(state)}</div>${reviewPanel(state)}</main>`;
  if (state.page === 'clients')
    content = `<main id="workspace-main" class="directory-page" tabindex="-1">${directory(state)}</main>`;
  if (state.page === 'programs') content = programEditor(state);
  if (state.page === 'exercises') content = catalogView(state);
  if (state.page === 'settings') content = settingsView(state);
  app.innerHTML = state.page === 'gallery' ? gallery(state) : shell(state, content);
  if (focused) {
    const replacement = document.getElementById(focused);
    replacement?.focus({ preventScroll: true });
    if (caret !== null && replacement?.setSelectionRange)
      replacement.setSelectionRange(caret, caret);
  } else if (focusedAction) {
    const replacement = [...app.querySelectorAll('[data-action]')].find((element) =>
      Object.entries(focusedData).every(([key, value]) => element.dataset[key] === value),
    );
    replacement?.focus({ preventScroll: true });
  }
}

function openModal(title, body, actions = '') {
  if (!modal.open) opener = document.activeElement;
  modal.innerHTML = `<div class="modal-header"><h2 id="modal-title">${escapeHtml(title)}</h2>${tool('close-modal', translator(state)('Закрити', 'Close'), 'close')}</div><div class="modal-body">${body}</div>${actions ? `<div class="modal-actions">${actions}</div>` : ''}`;
  if (!modal.open) modal.showModal();
}

const editorApi = { render, persist, toast, openModal, close: () => modal.close() };

function navigate(page) {
  if (state.page === 'programs' && state.editorDirty && page !== 'programs') {
    state.pendingNavigation = page;
    openModal(
      translator(state)('Є незбережені зміни', 'Unsaved changes'),
      `<p>${translator(state)('Залишитися в редакторі чи відкинути зміни?', 'Stay in the editor or discard changes?')}</p>`,
      `${button('close-modal', translator(state)('Залишитися', 'Stay'))}${button('discard-navigation', translator(state)('Відкинути й перейти', 'Discard and leave'), 'arrow')}`,
    );
    return false;
  }
  state.page = page;
  if (page === 'programs') ensureEditor(state);
  if (modal.open) modal.close();
  if (page === 'gallery') history.pushState(null, '', '?');
  render();
  return true;
}

function changeVariant(id) {
  if (state.page === 'programs' && state.editorDirty) {
    state.pendingVariant = id;
    navigate('workspace');
    return;
  }
  state.variant = id;
  state.page = 'workspace';
  history.pushState(null, '', `?variant=${id}`);
  render();
}

function selectClient(id) {
  if (!state.data.clients.some((client) => client.id === id)) return;
  state.clientId = id;
  state.entryId = null;
  state.visibility = 'client';
  state.page = 'workspace';
  render();
}

function saveCurrentNote() {
  const { client, entry } = selection(state);
  if (!entry) return;
  saveNote(state.data, client.id, entry.id, state.visibility, noteDraft(state));
  delete state.drafts[`${noteKey(client.id, entry.id)}:${state.visibility}`];
  const stored = persist();
  render();
  toast(
    translator(state)(
      stored ? 'Нотатку збережено' : 'Збережено лише в цій вкладці',
      stored ? 'Note saved' : 'Saved in this tab only',
    ),
  );
}

app.addEventListener('input', (event) => {
  if (handleEditorInput(state, event.target)) return;
  if (event.target.id === 'catalog-search') {
    state.catalogSearch = event.target.value;
    render();
  }
  if (event.target.id === 'client-search') {
    state.search = event.target.value;
    render();
  }
  if (event.target.id === 'coach-note') {
    const { client, entry } = selection(state);
    state.drafts[`${noteKey(client.id, entry.id)}:${state.visibility}`] = event.target.value;
    document.querySelector('[data-draft-state]').textContent = translator(state)(
      'Чернетка',
      'Draft',
    );
    persist();
  }
});

app.addEventListener('change', (event) => {
  if (event.target.id === 'pending-filter') {
    state.pendingOnly = event.target.checked;
    render();
  }
  if (event.target.dataset.select === 'range') {
    state.range = event.target.value;
    render();
  }
  if (event.target.dataset.select === 'client') selectClient(event.target.value);
  if (event.target.dataset.select === 'sort') {
    state.sort = event.target.value;
    render();
  }
  if (event.target.dataset.select === 'metric') {
    state.metric = event.target.value;
    render();
  }
  if (event.target.id === 'show-archived') {
    state.showArchived = event.target.checked;
    render();
  }
  if (event.target.dataset.select === 'program') {
    if (state.editorDirty) {
      toast(
        translator(state)(
          'Збережіть чернетку перед зміною шаблону.',
          'Save this draft before switching templates.',
        ),
      );
      render();
      return;
    }
    state.programDraft = null;
    ensureEditor(state, event.target.value);
    render();
  }
});

document.addEventListener('submit', (event) => {
  event.preventDefault();
  if (event.target.id === 'note-form') saveCurrentNote();
  else handleEditorSubmit(state, event.target, editorApi);
});

document.addEventListener('click', (event) => {
  const trigger = event.target.closest('[data-action]');
  if (!trigger || trigger.disabled) return;
  const action = trigger.dataset.action;
  const text = translator(state);
  if (action === 'close-modal') {
    modal.close();
    return;
  }
  if (handleEditorAction(state, trigger, editorApi)) return;
  if (['programs', 'exercises', 'settings'].includes(action)) {
    navigate(action);
    return;
  }
  if (action === 'discard-navigation') {
    state.editorDirty = false;
    state.programDraft = null;
    modal.close();
    if (state.pendingVariant) {
      const id = state.pendingVariant;
      state.pendingVariant = null;
      changeVariant(id);
    } else navigate(state.pendingNavigation);
    return;
  }
  if (action === 'discard-editor') {
    state.allowEditorReplacement = true;
    modal.close();
    handleEditorAction(state, { dataset: { action: state.pendingEditorAction } }, editorApi);
    return;
  }
  if (action === 'gallery') {
    navigate('gallery');
    return;
  }
  if (action === 'previous-variant' || action === 'next-variant') {
    const index = variants.findIndex((variant) => variant.id === state.variant);
    changeVariant(variants[(index + (action === 'next-variant' ? 1 : 9)) % 10].id);
    return;
  }
  if (action === 'theme') {
    state.theme = state.theme === 'dark' ? 'light' : 'dark';
    persist();
    render();
    return;
  }
  if (action === 'language') {
    state.locale = state.locale === 'uk' ? 'en' : 'uk';
    persist();
    render();
    return;
  }
  if (action === 'select-client') {
    selectClient(trigger.dataset.id);
    return;
  }
  if (action === 'next-client') {
    const pending = pendingClients(state.data).filter((client) => client.id !== state.clientId);
    if (pending.length) selectClient(pending[0].id);
    else toast(text('Усі перевірки завершені', 'All reviews complete'));
    return;
  }
  if (action === 'select-entry') {
    state.entryId = trigger.dataset.id;
    state.metric = selection(state).entry.exerciseId;
    render();
    if (innerWidth < 768)
      document.querySelector('.review-pane')?.scrollIntoView({ block: 'start' });
    return;
  }
  if (action === 'tab') {
    state.tab = trigger.dataset.id;
    render();
    document.querySelector(`#tab-${state.tab}`)?.focus();
    return;
  }
  if (action === 'visibility') {
    state.visibility = trigger.dataset.id;
    render();
    return;
  }
  if (action === 'complete-review') {
    const { client, entry } = selection(state);
    finishReview(state.data, client.id, entry.id);
    persist();
    render();
    toast(text('Перевірку завершено', 'Review completed'));
    return;
  }
  if (action === 'client-view' || action === 'workspace' || action === 'clients') {
    navigate(action);
    return;
  }
  if (action === 'client-details') {
    state.tab = 'history';
    navigate('client-details');
    return;
  }
  if (action === 'reviews') {
    changeVariant('03');
    return;
  }
  if (['previous-week', 'next-week', 'this-week'].includes(action)) {
    state.weekOffset =
      action === 'this-week' ? 0 : (state.weekOffset || 0) + (action === 'next-week' ? 1 : -1);
    render();
    return;
  }
  if (action === 'calendar-session') {
    const client = state.data.clients.find((item) => item.id === trigger.dataset.client);
    const session = client.sessions.find((item) => item.date === trigger.dataset.date);
    if (session) {
      state.clientId = client.id;
      state.entryId = session.entries[0].id;
      render();
    } else
      openModal(
        text('Майбутнє заняття', 'Future session'),
        `<p>${escapeHtml(client.name)} · ${trigger.dataset.date}</p><p class="muted">${text('Заплановано. Фактичних результатів ще немає.', 'Planned. No actual results yet.')}</p>`,
        button('programs', text('Відкрити редактор', 'Open editor'), 'edit'),
      );
    return;
  }
  if (action === 'open-program-session') {
    ensureEditor(state);
    state.editorWeek = Number(trigger.dataset.week);
    state.editorSession = Number(trigger.dataset.session);
    navigate('programs');
    return;
  }
  if (action === 'demo-state') {
    const id = trigger.dataset.id;
    if (id === 'empty') {
      selectClient('oliver');
      return;
    }
    if (id === 'conflict') {
      ensureEditor(state);
      state.data.programs.find((program) => program.id === state.programDraft.id).revision += 1;
      state.page = 'programs';
      render();
      openModal(
        text('Конфлікт версій', 'Version conflict'),
        `<p>${text('Демонстрація: інша вкладка зберегла новішу версію.', 'Simulation: another tab saved a newer version.')}</p>`,
        `${button('reload-program', text('Завантажити новішу', 'Load newer version'), 'history')}${button('close-modal', text('Залишити чернетку', 'Keep draft'))}`,
      );
      return;
    }
    const messages = {
      loading: [
        text('Завантаження профілю', 'Loading profile'),
        text('Очікування даних…', 'Waiting for data…'),
      ],
      error: [
        text('Не вдалося завантажити', 'Could not load'),
        text('Дані не змінені. Можна повторити спробу.', 'Your data is unchanged. You can retry.'),
      ],
      unavailable: [
        text('Відео недоступне', 'Video unavailable'),
        text(
          'Відео може бути приватним або видаленим. Потрібне нове посилання.',
          'The video may be private or deleted. A new link is needed.',
        ),
      ],
      denied: [
        text('Немає доступу', 'Access denied'),
        text(
          'Цей профіль недоступний поточному тренеру.',
          'This profile is unavailable to the current coach.',
        ),
      ],
    };
    openModal(
      messages[id][0],
      `<div class="demo-state-message ${id === 'loading' ? 'loading-state' : ''}">${escapeHtml(messages[id][1])}</div>`,
      button(
        id === 'denied' ? 'close-modal' : 'retry-state',
        id === 'denied' ? text('Закрити', 'Close') : text('Повторити', 'Retry'),
        'history',
      ),
    );
    return;
  }
  if (action === 'retry-state') {
    modal.close();
    state.page = 'workspace';
    render();
    toast(text('Демонстраційні дані завантажено', 'Demo data loaded'));
    return;
  }
  if (action === 'video') {
    const { client, entry } = selection(state);
    if (!entry) return;
    openModal(
      `${client.name} · ${localized(state, entry.name)}`,
      `<figure class="video-demo"><img src="assets/hero.webp" alt="${text('Художня ілюстрація, не відеозапис', 'Artistic illustration, not a video recording')}"><figcaption>${text('Демонстраційний кадр. Відео клієнта не підключене.', 'Demonstration frame. No client video is connected.')}</figcaption></figure>`,
    );
    return;
  }
  if (action === 'reset') {
    openModal(
      text('Скинути демонстраційні зміни?', 'Reset demo changes?'),
      `<p>${text('Програми й нотатки цього прев’ю повернуться до початкового стану.', 'Programs and notes in this preview will return to their initial state.')}</p>`,
      `${button('close-modal', text('Скасувати', 'Cancel'))}${button('confirm-reset', text('Скинути', 'Reset'), 'history', '', 'primary')}`,
    );
    return;
  }
  if (action === 'confirm-reset') {
    state.data = freshData();
    state.drafts = {};
    state.programDraft = null;
    state.editorDirty = false;
    state.clientId = 'emma';
    state.entryId = latestSession(state.data.clients[0]).entries[0].id;
    persist();
    modal.close();
    render();
    return;
  }
});

document.addEventListener('keydown', (event) => {
  if (
    event.target.getAttribute('role') !== 'tab' ||
    !['ArrowLeft', 'ArrowRight'].includes(event.key)
  )
    return;
  const tabs = [...event.target.parentElement.querySelectorAll('[role=tab]')];
  const next =
    (tabs.indexOf(event.target) + (event.key === 'ArrowRight' ? 1 : -1) + tabs.length) %
    tabs.length;
  event.preventDefault();
  tabs[next].click();
});
modal.addEventListener('close', () => opener?.isConnected && opener.focus());
window.addEventListener('beforeunload', (event) => {
  if (state.editorDirty) {
    event.preventDefault();
    event.returnValue = '';
  }
});
window.addEventListener('storage', (event) => {
  if (event.key !== STORAGE_KEY || !event.newValue) return;
  try {
    const updated = JSON.parse(event.newValue);
    if (updated.schema !== 1 || !Array.isArray(updated.data?.programs)) return;
    state.data = updated.data;
    if (state.page === 'programs' && state.editorDirty) {
      openModal(
        translator(state)('Дані змінились в іншій вкладці', 'Data changed in another tab'),
        `<p>${translator(state)('Ваша чернетка залишається тут. Перед збереженням перевірте версію.', 'Your draft is still here. Check the revision before saving.')}</p>`,
        button('close-modal', translator(state)('Зрозуміло', 'OK')),
      );
    } else {
      state.programDraft = null;
      render();
    }
  } catch {
    toast(
      translator(state)(
        'Не вдалося прочитати зміни іншої вкладки.',
        'Could not read changes from another tab.',
      ),
    );
  }
});
window.addEventListener('popstate', () => {
  const id = new URLSearchParams(location.search).get('variant');
  if (state.editorDirty) {
    history.pushState(null, '', `?variant=${state.variant}`);
    navigate(id ? 'workspace' : 'gallery');
    return;
  }
  state.variant = variants.some((variant) => variant.id === id) ? id : '02';
  state.page = id ? 'workspace' : 'gallery';
  render();
});
render();
