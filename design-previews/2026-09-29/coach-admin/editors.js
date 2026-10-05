import { newProgram, saveProgram, publishProgram, assignProgram, saveExercise } from './data.js';
import {
  translator,
  localized,
  escapeHtml,
  unitText,
  icon,
  tool,
  button,
  badge,
  emptyState,
  directions,
} from './ui.js';

export function ensureEditor(state, programId) {
  if (state.programDraft && (!programId || state.programDraft.id === programId)) return;
  const program =
    state.data.programs.find((item) => item.id === programId) || state.data.programs[0];
  state.programDraft = structuredClone(program);
  state.editorRevision = program.revision;
  state.editorDirty = false;
  state.editorWeek = 0;
  state.editorSession = 0;
}

function currentSession(state) {
  return state.programDraft.weeks[state.editorWeek].sessions[state.editorSession];
}

function editorLabel(state) {
  const text = translator(state);
  return state.editorDirty
    ? text('Незбережені зміни', 'Unsaved changes')
    : text('Чернетку збережено', 'Draft saved');
}

export function programEditor(state) {
  ensureEditor(state);
  const text = translator(state);
  const program = state.programDraft;
  const session = currentSession(state);
  const selectedWeek = program.weeks[state.editorWeek];
  return `<main id="workspace-main" class="editor-page" tabindex="-1"><header class="page-heading"><div><p class="eyebrow">${text('Бібліотека програм', 'Program library')}</p><h1>${text('Конструктор програми', 'Program builder')}</h1></div><div class="editor-top-actions">${button('new-program', text('Нова', 'New'), 'library')}${tool('duplicate-program', text('Дублювати програму', 'Duplicate program'), 'library')}${tool('preview-program', text('Попередній перегляд', 'Preview program'), 'profile')}</div></header><div class="program-editor-layout"><aside class="editor-library"><label for="program-picker">${text('Шаблон програми', 'Program template')}</label><select id="program-picker" data-select="program">${state.data.programs.map((item) => `<option value="${item.id}" ${item.id === program.id ? 'selected' : ''}>${escapeHtml(localized(state, item.name))}</option>`).join('')}${state.data.programs.some((item) => item.id === program.id) ? '' : `<option value="${program.id}" selected>${text('Нова програма', 'New program')}</option>`}</select><div class="editor-week-list">${program.weeks.map((week, weekIndex) => `<section><button type="button" class="editor-week-button ${weekIndex === state.editorWeek ? 'chosen' : ''}" data-action="editor-week" data-index="${weekIndex}"><span>${text('Тиждень', 'Week')} ${weekIndex + 1}</span>${icon('right')}</button>${weekIndex === state.editorWeek ? week.sessions.map((item, sessionIndex) => `<button type="button" class="editor-session-button ${sessionIndex === state.editorSession ? 'chosen' : ''}" data-action="editor-session" data-index="${sessionIndex}">${icon('workout')}<span>${escapeHtml(item.name)}</span><small>${item.rows.length}</small></button>`).join('') : ''}</section>`).join('')}</div>${button('add-week', text('Додати тиждень', 'Add week'), 'calendar')}<div class="editor-versions"><p class="eyebrow">${text('Опубліковані версії', 'Published versions')}</p>${
    program.published.length
      ? program.published
          .toReversed()
          .map(
            (version) =>
              `<span>${badge(`v${version.number}`, 'success')} ${escapeHtml(localized(state, version.name))}</span>`,
          )
          .join('')
      : `<p class="muted">${text('Ще немає', 'None yet')}</p>`
  }</div></aside><form id="program-editor" class="program-editor-main"><div class="form-grid"><label>${text('Назва · UA', 'Name · UA')}<input name="program-uk" data-program-name="uk" maxlength="120" required value="${escapeHtml(program.name.uk)}"></label><label>${text('Назва · EN', 'Name · EN')}<input name="program-en" data-program-name="en" maxlength="120" required value="${escapeHtml(program.name.en)}"></label></div><div class="editor-session-heading"><label>${text('Назва заняття', 'Session name')}<input name="session-name" data-session-field="name" maxlength="60" value="${escapeHtml(session.name)}" required></label><div>${tool('add-session', text('Додати заняття', 'Add session'), 'workout')}${tool('remove-session', text('Видалити заняття', 'Remove session'), 'close', selectedWeek.sessions.length < 2 ? 'disabled' : '')}</div></div><label class="block-name">${text('Блок', 'Block')}<input name="block-name" data-session-field="block" value="${escapeHtml(localized(state, session.block) || text('Основна частина', 'Main block'))}" maxlength="80"></label><div class="builder-rows">${
    session.rows
      .map((row, rowIndex) => {
        const exercise = state.data.exercises.find((item) => item.id === row.exerciseId);
        return `<article class="builder-row" data-row-id="${row.id}"><div class="builder-row-heading"><span class="exercise-number">${String(rowIndex + 1).padStart(2, '0')}</span><h3>${escapeHtml(localized(state, exercise.name))}</h3>${exercise.archived ? badge(text('Архів', 'Archived')) : ''}<div class="row-tools">${tool('move-row-up', text('Вище', 'Move up'), 'left', `data-index="${rowIndex}" ${rowIndex === 0 ? 'disabled' : ''}`)}${tool('move-row-down', text('Нижче', 'Move down'), 'right', `data-index="${rowIndex}" ${rowIndex === session.rows.length - 1 ? 'disabled' : ''}`)}${tool('remove-row', text('Прибрати вправу', 'Remove exercise'), 'close', `data-index="${rowIndex}"`)}</div></div><div class="builder-sets">${row.targets.map((target, setIndex) => `<label>${text('Підхід', 'Set')} ${setIndex + 1} · ${unitText(state, exercise.unit)}<input type="number" min="1" max="600" step="1" required data-row="${rowIndex}" data-target="${setIndex}" value="${target}"></label>`).join('')}<label class="rest-input">${text('Відпочинок · с', 'Rest · s')}<input type="number" min="0" max="3600" step="1" required data-row="${rowIndex}" data-rest value="${row.rest}"></label><div class="set-tools">${tool('add-set', text('Додати підхід', 'Add set'), 'arrow', `data-index="${rowIndex}" ${row.targets.length >= 10 ? 'disabled' : ''}`)}${tool('remove-set', text('Прибрати підхід', 'Remove set'), 'close', `data-index="${rowIndex}" ${row.targets.length <= 1 ? 'disabled' : ''}`)}</div></div></article>`;
      })
      .join('') || emptyState(state, text('Додайте першу вправу', 'Add your first exercise'))
  }</div><div class="add-exercise-bar"><label for="add-exercise-select" class="sr-only">${text('Вправа', 'Exercise')}</label><select id="add-exercise-select">${state.data.exercises
    .filter((exercise) => !exercise.archived)
    .map(
      (exercise) =>
        `<option value="${exercise.id}">${escapeHtml(localized(state, exercise.name))}</option>`,
    )
    .join(
      '',
    )}</select>${button('add-row', text('Додати вправу', 'Add exercise'), 'workout')}</div><p class="form-error" id="program-error" role="alert"></p><footer class="editor-save-bar"><span data-editor-status class="${state.editorDirty ? 'dirty' : ''}">${editorLabel(state)}</span><div><button type="submit" class="button">${icon('check')}<span>${text('Зберегти', 'Save')}</span></button>${button('publish-program', text('Опублікувати версію', 'Publish version'), 'check', '', 'primary')}${button('assign', text('Призначити', 'Assign'), 'calendar')}</div></footer></form></div></main>`;
}

export function catalogView(state) {
  const text = translator(state);
  const exercises = state.data.exercises.filter(
    (exercise) =>
      localized(state, exercise.name)
        .toLowerCase()
        .includes((state.catalogSearch || '').toLowerCase()) &&
      (state.showArchived || !exercise.archived),
  );
  return `<main id="workspace-main" class="catalog-page" tabindex="-1"><header class="page-heading"><div><p class="eyebrow">${text('Бібліотека студії', 'Studio library')}</p><h1>${text('Вправи й матеріали', 'Exercises & materials')}</h1></div>${button('new-exercise', text('Нова вправа', 'New exercise'), 'workout', '', 'primary')}</header><div class="catalog-controls"><label for="catalog-search" class="sr-only">${text('Знайти вправу', 'Find an exercise')}</label><input id="catalog-search" type="search" placeholder="${text('Пошук вправи', 'Find an exercise')}" value="${escapeHtml(state.catalogSearch || '')}"><label class="check-label"><input id="show-archived" type="checkbox" ${state.showArchived ? 'checked' : ''}>${text('Показати архів', 'Show archived')}</label></div><div class="table-scroll" tabindex="0" role="region" aria-label="${text('Каталог вправ', 'Exercise catalog')}"><table class="catalog-table"><thead><tr><th>${text('Вправа', 'Exercise')}</th><th>${text('Напрям', 'Direction')}</th><th>${text('Вимір', 'Unit')}</th><th>${text('Матеріали', 'Materials')}</th><th>${text('Дії', 'Actions')}</th></tr></thead><tbody>${exercises.map((exercise) => `<tr><td><strong>${escapeHtml(localized(state, exercise.name))}</strong><small>${escapeHtml(exercise.name[state.locale === 'uk' ? 'en' : 'uk'])}</small>${exercise.archived ? badge(text('В архіві', 'Archived')) : ''}</td><td>${escapeHtml(directions(state)[exercise.direction])}</td><td>${unitText(state, exercise.unit)}</td><td>${exercise.tutorialUrl ? badge('YouTube') : text('Без туторіалу', 'No tutorial')}</td><td><div class="table-actions">${tool('edit-exercise', text('Редагувати', 'Edit'), 'edit', `data-id="${exercise.id}"`)}${tool('duplicate-exercise', text('Дублювати', 'Duplicate'), 'library', `data-id="${exercise.id}"`)}${tool('archive-exercise', exercise.archived ? text('Повернути з архіву', 'Unarchive') : text('Архівувати', 'Archive'), 'history', `data-id="${exercise.id}"`)}</div></td></tr>`).join('') || `<tr><td colspan="5">${text('Вправ не знайдено', 'No exercises found')}</td></tr>`}</tbody></table></div><section class="materials-section"><div class="section-head"><h2>${text('Матеріали до вправ', 'Exercise materials')}</h2><span class="muted">${state.data.exercises.filter((exercise) => exercise.tutorialUrl).length}</span></div>${
    state.data.exercises.some((exercise) => exercise.tutorialUrl)
      ? state.data.exercises
          .filter((exercise) => exercise.tutorialUrl)
          .map(
            (exercise) =>
              `<article class="material-row">${icon('play')}<div><h3>${escapeHtml(localized(state, exercise.name))}</h3><p>${escapeHtml(exercise.tutorialUrl)}</p></div>${tool('edit-exercise', text('Редагувати матеріал', 'Edit material'), 'edit', `data-id="${exercise.id}"`)}</article>`,
          )
          .join('')
      : emptyState(state, text('Туторіалів ще немає', 'No tutorials yet'))
  }</section></main>`;
}

export function exerciseForm(state, id, duplicate = false) {
  const text = translator(state);
  const exercise = state.data.exercises.find((item) => item.id === id);
  return `<form id="exercise-form" data-id="${duplicate ? '' : exercise?.id || ''}"><div class="form-grid"><label>${text('Назва · UA', 'Name · UA')}<input name="name-uk" value="${escapeHtml(exercise?.name.uk || '')}${duplicate ? ' (копія)' : ''}" required maxlength="120"></label><label>${text('Назва · EN', 'Name · EN')}<input name="name-en" value="${escapeHtml(exercise?.name.en || '')}${duplicate ? ' (copy)' : ''}" required maxlength="120"></label><label>${text('Вимір', 'Measurement')}<select name="unit"><option value="sec" ${exercise?.unit === 'sec' ? 'selected' : ''}>${text('Секунди', 'Seconds')}</option><option value="reps" ${exercise?.unit === 'reps' ? 'selected' : ''}>${text('Повтори', 'Repetitions')}</option></select></label><label>${text('Напрям', 'Direction')}<select name="direction">${Object.entries(
    directions(state),
  )
    .map(
      ([direction, label]) =>
        `<option value="${direction}" ${exercise?.direction === direction ? 'selected' : ''}>${label}</option>`,
    )
    .join(
      '',
    )}</select></label></div><label>${text('Інструкція · UA', 'Instructions · UA')}<textarea name="cue-uk" maxlength="2000" rows="2">${escapeHtml(exercise?.cue.uk || '')}</textarea></label><label>${text('Інструкція · EN', 'Instructions · EN')}<textarea name="cue-en" maxlength="2000" rows="2">${escapeHtml(exercise?.cue.en || '')}</textarea></label><label>${text('Навчальне відео · YouTube URL', 'Tutorial · YouTube URL')}<input name="tutorial" type="url" value="${escapeHtml(exercise?.tutorialUrl || '')}" placeholder="https://www.youtube.com/watch?v=…"></label><p class="form-error" role="alert"></p><div class="form-actions">${button('close-modal', text('Скасувати', 'Cancel'))}<button type="submit" class="button primary">${icon('check')}<span>${text('Зберегти вправу', 'Save exercise')}</span></button></div></form>`;
}

function assignmentForm(state) {
  const text = translator(state);
  const published = state.data.programs.filter((program) => program.published.length);
  if (!published.length)
    return `<p>${text('Немає опублікованої версії для призначення.', 'No published version is available to assign.')}</p><div class="form-actions">${button('programs', text('До редактора', 'Open builder'), 'edit')}</div>`;
  return `<form id="assignment-form"><label>${text('Клієнт', 'Client')}<select name="client">${state.data.clients.map((client) => `<option value="${client.id}" ${state.clientId === client.id ? 'selected' : ''}>${escapeHtml(client.name)}</option>`).join('')}</select></label><label>${text('Опублікована програма', 'Published program')}<select name="program">${published.map((program) => `<option value="${program.id}" ${state.programDraft?.id === program.id ? 'selected' : ''}>${escapeHtml(localized(state, program.name))} · v${program.published.at(-1).number}</option>`).join('')}</select></label><label>${text('Початок', 'Starts on')}<input name="starts" type="date" min="2026-09-30" value="2026-10-01" required></label><p class="form-error" role="alert"></p><div class="form-actions"><button type="submit" class="button primary">${icon('calendar')}<span>${text('Призначити на майбутнє', 'Assign future program')}</span></button></div></form>`;
}

function previewProgram(state) {
  const text = translator(state);
  const session = currentSession(state);
  return `<article class="program-draft-preview"><p class="eyebrow">${text('Чернетка · попередній перегляд', 'Draft · preview')}</p><h3>${escapeHtml(localized(state, state.programDraft.name) || text('Без назви', 'Untitled'))}</h3>${
    session.rows
      .map((row) => {
        const exercise = state.data.exercises.find((item) => item.id === row.exerciseId);
        return `<div><strong>${escapeHtml(localized(state, exercise.name))}</strong><p>${row.targets.join(' / ')} ${unitText(state, exercise.unit)} · ${text('відпочинок', 'rest')} ${row.rest} ${text('с', 's')}</p></div>`;
      })
      .join('') || emptyState(state, text('Вправ поки немає', 'No exercises yet'))
  }</article>`;
}

const errors = {
  names: ['Заповніть назви українською й англійською.', 'Enter Ukrainian and English names.'],
  emptyProgram: [
    'Додайте щонайменше одну вправу в кожне заняття.',
    'Add at least one exercise to each session.',
  ],
  target: [
    'Ціль підходу: ціле число від 1 до 600.',
    'Set targets must be whole numbers from 1 to 600.',
  ],
  rest: ['Відпочинок: від 0 до 3600 секунд.', 'Rest must be from 0 to 3600 seconds.'],
  video: [
    'Вкажіть HTTPS-посилання на конкретне YouTube-відео.',
    'Enter an HTTPS link to a specific YouTube video.',
  ],
  unitLocked: [
    'Вправа вже в програмі. Створіть копію для іншого виміру.',
    'This exercise is used in a program. Duplicate it to change its unit.',
  ],
  future: ['Оберіть дату після 29 вересня 2026.', 'Choose a date after 29 September 2026.'],
  access: [
    'Немає активного доступу для цього клієнта.',
    'This client does not have active access.',
  ],
  conflict: [
    'Версію змінено в іншій вкладці. Перезавантажте її або збережіть окрему копію.',
    'Another tab changed this version. Reload it or save a separate copy.',
  ],
  unpublished: ['Спершу опублікуйте версію.', 'Publish a version first.'],
  unsaved: ['Спершу збережіть чернетку.', 'Save the draft first.'],
};
export function errorText(state, error) {
  return (errors[error.message] || [
    'Не вдалося зберегти. Перевірте поля.',
    'Could not save. Check the fields.',
  ])[state.locale === 'uk' ? 0 : 1];
}

export function handleEditorInput(state, target) {
  if (target.dataset.programName)
    state.programDraft.name[target.dataset.programName] = target.value;
  else if (target.dataset.sessionField === 'name') currentSession(state).name = target.value;
  else if (target.dataset.sessionField === 'block')
    currentSession(state).block = {
      ...(currentSession(state).block || {}),
      [state.locale]: target.value,
    };
  else if (target.hasAttribute('data-target'))
    currentSession(state).rows[Number(target.dataset.row)].targets[Number(target.dataset.target)] =
      Number(target.value);
  else if (target.hasAttribute('data-rest'))
    currentSession(state).rows[Number(target.dataset.row)].rest = Number(target.value);
  else return false;
  state.editorDirty = true;
  const indicator = document.querySelector('[data-editor-status]');
  if (indicator) {
    indicator.textContent = editorLabel(state);
    indicator.className = 'dirty';
  }
  return true;
}

export function handleEditorSubmit(state, form, api) {
  const text = translator(state);
  try {
    if (form.id === 'program-editor') {
      const saved = saveProgram(state.data, state.programDraft, state.editorRevision);
      state.programDraft = structuredClone(saved);
      state.editorRevision = saved.revision;
      state.editorDirty = false;
      api.persist();
      api.render();
      api.toast(text('Чернетку збережено', 'Draft saved'));
      return true;
    }
    if (form.id === 'exercise-form') {
      const values = new FormData(form);
      saveExercise(state.data, {
        id: form.dataset.id,
        name: { uk: values.get('name-uk'), en: values.get('name-en') },
        cue: { uk: values.get('cue-uk'), en: values.get('cue-en') },
        unit: values.get('unit'),
        direction: values.get('direction'),
        tutorialUrl: values.get('tutorial'),
      });
      api.persist();
      api.close();
      api.render();
      api.toast(text('Вправу збережено', 'Exercise saved'));
      return true;
    }
    if (form.id === 'assignment-form') {
      const values = new FormData(form);
      assignProgram(state.data, values.get('program'), values.get('client'), values.get('starts'));
      api.persist();
      api.close();
      api.render();
      api.toast(text('Програму призначено на майбутнє', 'Future program assigned'));
      return true;
    }
  } catch (error) {
    form.querySelector('.form-error').textContent = errorText(state, error);
    return true;
  }
  return false;
}

export function handleEditorAction(state, trigger, api) {
  const action = trigger.dataset.action;
  const text = translator(state);
  if (action === 'assign') {
    api.openModal(text('Призначити програму', 'Assign program'), assignmentForm(state));
    return true;
  }
  if (['new-exercise', 'edit-exercise', 'duplicate-exercise'].includes(action)) {
    api.openModal(
      action === 'new-exercise'
        ? text('Нова вправа', 'New exercise')
        : text('Редактор вправи', 'Exercise editor'),
      exerciseForm(state, trigger.dataset.id, action === 'duplicate-exercise'),
    );
    return true;
  }
  if (action === 'archive-exercise') {
    const exercise = state.data.exercises.find((item) => item.id === trigger.dataset.id);
    exercise.archived = !exercise.archived;
    api.persist();
    api.render();
    api.toast(
      text(
        exercise.archived ? 'Вправу архівовано. Історію збережено.' : 'Вправу повернуто',
        exercise.archived ? 'Exercise archived. History preserved.' : 'Exercise restored',
      ),
    );
    return true;
  }
  const actions = [
    'new-program',
    'duplicate-program',
    'preview-program',
    'editor-week',
    'editor-session',
    'add-week',
    'add-session',
    'remove-session',
    'move-row-up',
    'move-row-down',
    'remove-row',
    'add-set',
    'remove-set',
    'add-row',
    'publish-program',
    'reload-program',
    'confirm-publish',
  ];
  if (!actions.includes(action)) return false;
  ensureEditor(state);
  const session = currentSession(state);
  const index = Number(trigger.dataset.index);
  if (action === 'new-program' || action === 'duplicate-program') {
    if (state.editorDirty && !state.allowEditorReplacement) {
      state.pendingEditorAction = action;
      api.openModal(
        text('Є незбережена чернетка', 'Unsaved draft'),
        `<p>${text('Залишитися в редакторі чи відкинути ці зміни?', 'Stay in the editor or discard these changes?')}</p>`,
        `${button('close-modal', text('Залишитися', 'Stay'))}${button('discard-editor', text('Відкинути', 'Discard'), 'close')}`,
      );
      return true;
    }
    state.allowEditorReplacement = false;
    state.programDraft =
      action === 'new-program'
        ? newProgram()
        : {
            ...structuredClone(state.programDraft),
            id: crypto.randomUUID(),
            name: {
              uk: `${state.programDraft.name.uk} (копія)`,
              en: `${state.programDraft.name.en} (copy)`,
            },
            revision: 0,
            published: [],
            status: 'draft',
          };
    state.editorWeek = 0;
    state.editorSession = 0;
    state.editorRevision = 0;
    state.editorDirty = true;
  }
  if (action === 'editor-week') {
    state.editorWeek = index;
    state.editorSession = 0;
  }
  if (action === 'editor-session') state.editorSession = index;
  if (action === 'preview-program') {
    api.openModal(text('Перегляд програми', 'Program preview'), previewProgram(state));
    return true;
  }
  if (action === 'add-week') {
    const week = structuredClone(state.programDraft.weeks[state.editorWeek]);
    week.id = crypto.randomUUID();
    week.sessions.forEach((item) => {
      item.id = crypto.randomUUID();
      item.rows.forEach((row) => {
        row.id = crypto.randomUUID();
      });
    });
    state.programDraft.weeks.push(week);
    state.editorWeek = state.programDraft.weeks.length - 1;
    state.editorSession = 0;
    state.editorDirty = true;
  }
  if (action === 'add-session') {
    const added = structuredClone(session);
    added.id = crypto.randomUUID();
    added.name = `${session.name} +`;
    added.rows.forEach((row) => {
      row.id = crypto.randomUUID();
    });
    state.programDraft.weeks[state.editorWeek].sessions.push(added);
    state.editorSession = state.programDraft.weeks[state.editorWeek].sessions.length - 1;
    state.editorDirty = true;
  }
  if (
    action === 'remove-session' &&
    state.programDraft.weeks[state.editorWeek].sessions.length > 1
  ) {
    state.programDraft.weeks[state.editorWeek].sessions.splice(state.editorSession, 1);
    state.editorSession = 0;
    state.editorDirty = true;
  }
  if (action === 'add-row') {
    const id = document.querySelector('#add-exercise-select').value;
    session.rows.push({ id: crypto.randomUUID(), exerciseId: id, targets: [10, 10, 10], rest: 60 });
    state.editorDirty = true;
  }
  if (action === 'remove-row') {
    session.rows.splice(index, 1);
    state.editorDirty = true;
  }
  if (action === 'move-row-up' || action === 'move-row-down') {
    const destination = index + (action === 'move-row-up' ? -1 : 1);
    if (destination >= 0 && destination < session.rows.length)
      [session.rows[index], session.rows[destination]] = [
        session.rows[destination],
        session.rows[index],
      ];
    state.editorDirty = true;
  }
  if (action === 'add-set' && session.rows[index].targets.length < 10) {
    session.rows[index].targets.push(session.rows[index].targets.at(-1));
    state.editorDirty = true;
  }
  if (action === 'remove-set' && session.rows[index].targets.length > 1) {
    session.rows[index].targets.pop();
    state.editorDirty = true;
  }
  if (action === 'publish-program') {
    if (state.editorDirty || !state.editorRevision) {
      document.querySelector('#program-error').textContent = text(
        'Спершу збережіть чернетку.',
        'Save the draft first.',
      );
      return true;
    }
    api.openModal(
      text('Опублікувати нову версію?', 'Publish a new version?'),
      `<p>${escapeHtml(localized(state, state.programDraft.name))}</p><p class="muted">${text('Завершені заняття не зміняться. Призначення клієнту є окремим кроком.', 'Completed sessions will not change. Client assignment is a separate step.')}</p>`,
      `${button('close-modal', text('Скасувати', 'Cancel'))}${button('confirm-publish', text('Опублікувати', 'Publish'), 'check', '', 'primary')}`,
    );
    return true;
  }
  if (action === 'confirm-publish') {
    publishProgram(state.data, state.programDraft.id);
    const id = state.programDraft.id;
    state.programDraft = null;
    ensureEditor(state, id);
    api.persist();
    api.close();
    api.toast(text('Версію опубліковано в прев’ю', 'Version published in preview'));
  }
  if (action === 'reload-program') {
    const id = state.programDraft.id;
    state.programDraft = null;
    ensureEditor(state, id);
    api.close();
  }
  api.render();
  return true;
}

export function settingsView(state) {
  const text = translator(state);
  return `<main id="workspace-main" class="settings-page" tabindex="-1"><header class="page-heading"><div><p class="eyebrow">Handbalancer's Studio</p><h1>${text('Налаштування', 'Settings')}</h1></div></header><section><div class="settings-row"><div><h2>${text('Тема', 'Appearance')}</h2><p>${state.theme === 'dark' ? text('Темна', 'Dark') : text('Світла', 'Light')}</p></div>${button('theme', text('Змінити', 'Change'), 'today')}</div><div class="settings-row"><div><h2>${text('Мова', 'Language')}</h2><p>${state.locale === 'uk' ? 'Українська' : 'English'}</p></div>${button('language', state.locale === 'uk' ? 'English' : 'Українська')}</div><div class="settings-row"><div><h2>${text('Демонстраційні дані', 'Demo data')}</h2><p>${text('Лише цей локальний макет', 'This local prototype only')}</p></div>${button('reset', text('Скинути', 'Reset'), 'history')}</div></section><section class="state-testing"><h2>${text('Стани прев’ю', 'Preview states')}</h2><div class="state-options">${[
    ['empty', text('Новий клієнт', 'New client')],
    ['loading', text('Завантаження', 'Loading')],
    ['error', text('Помилка', 'Error')],
    ['unavailable', text('Відео недоступне', 'Unavailable video')],
    ['denied', text('Доступ заборонений', 'Access denied')],
    ['conflict', text('Конфлікт версій', 'Version conflict')],
  ]
    .map(([id, label]) => button('demo-state', label, '', `data-id="${id}"`))
    .join('')}</div></section></main>`;
}
