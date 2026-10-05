export const TODAY = '2026-09-29';
export const STORAGE_KEY = 'hbs:coach-admin-preview:20260929:v1';

const dates = ['03', '07', '10', '14', '17', '21', '24', '28'];
const handstand = [18, 20, 22, 23, 27, 29, 32, 34];
const pushups = [6, 7, 7, 8, 9, 10, 10, 12];

const catalog = [
  {
    id: 'handstand',
    name: { uk: 'Стійка біля стіни', en: 'Wall handstand' },
    unit: 'sec',
    direction: 'handstand',
    cue: {
      uk: 'Контрольована опора. Усе тіло в кадрі.',
      en: 'Controlled support. Keep the whole body in frame.',
    },
  },
  {
    id: 'pushups',
    name: { uk: 'Відтискання від підлоги', en: 'Floor push-ups' },
    unit: 'reps',
    direction: 'strength',
    cue: { uk: 'Рівний корпус, зручний темп.', en: 'A steady trunk and a comfortable pace.' },
  },
  {
    id: 'squats',
    name: { uk: 'Присідання', en: 'Bodyweight squats' },
    unit: 'reps',
    direction: 'strength',
    cue: { uk: 'Зберігайте опору на всій стопі.', en: 'Keep your whole foot supported.' },
  },
  {
    id: 'mobility',
    name: { uk: 'Рухливість плечей', en: 'Shoulder mobility' },
    unit: 'reps',
    direction: 'mobility',
    cue: { uk: 'Працюйте в комфортній амплітуді.', en: 'Use a comfortable range of motion.' },
  },
  {
    id: 'plank',
    name: { uk: 'Планка', en: 'Forearm plank' },
    unit: 'sec',
    direction: 'fitness',
    cue: {
      uk: 'Зберігайте контроль і спокійне дихання.',
      en: 'Maintain control and relaxed breathing.',
    },
  },
];

function sessionFor(clientId, offset, date, index) {
  return {
    id: `${clientId}-${date}`,
    date: `2026-09-${date}`,
    status: 'completed',
    title: { uk: 'Баланс і контроль', en: 'Balance & control' },
    minutes: 38 + index,
    version: 1,
    entries: catalog.slice(0, 3).map((exercise, exerciseIndex) => {
      const best =
        exerciseIndex === 0 ? handstand[index] + offset : exerciseIndex === 1 ? pushups[index] : 15;
      return {
        id: `${clientId}-${date}-${exercise.id}`,
        exerciseId: exercise.id,
        name: structuredClone(exercise.name),
        cue: structuredClone(exercise.cue),
        unit: exercise.unit,
        target: Array(3).fill(exerciseIndex === 0 ? 35 : exerciseIndex === 1 ? 12 : 15),
        actual: [best, Math.max(0, best - 2), Math.max(0, best - 4)],
        rest: 60,
        side: 'both',
        load: null,
        video: exerciseIndex === 0 ? 'demo' : null,
      };
    }),
  };
}

function programTemplate() {
  return {
    id: 'foundation',
    name: { uk: 'Баланс і сила', en: 'Balance & strength' },
    revision: 1,
    status: 'draft',
    published: [],
    weeks: Array.from({ length: 4 }, (_, weekIndex) => ({
      id: `week-${weekIndex + 1}`,
      sessions: ['A', 'B', 'C'].map((label, sessionIndex) => ({
        id: `week-${weekIndex + 1}-${label}`,
        name: `Practice ${label}`,
        rows: catalog
          .slice(sessionIndex === 1 ? 2 : 0, sessionIndex === 1 ? 5 : 3)
          .map((exercise) => ({
            id: `week-${weekIndex + 1}-${label}-${exercise.id}`,
            exerciseId: exercise.id,
            targets: Array(3).fill(exercise.unit === 'sec' ? 35 : 12),
            rest: 60,
          })),
      })),
    })),
  };
}

export function freshData() {
  const clients = [
    ['emma', 'Emma Wilson', 'EW', 'Pro', 'handstand', 0, 'active'],
    ['liam', "Liam O'Brien", 'LO', 'Pro', 'strength', -5, 'active'],
    ['sofia', 'Sofia Martin', 'SM', 'Plus', 'mobility', 3, 'active'],
    ['noah', 'Noah Murphy', 'NM', 'Pro+', 'handstand', -2, 'ending'],
    ['anna', 'Anna Kovalenko', 'AK', 'Essential', 'fitness', 2, 'inactive'],
    ['oliver', 'Oliver Hughes', 'OH', 'Plus', 'fitness', 0, 'active'],
  ].map(([id, name, initials, plan, direction, offset, access]) => ({
    id,
    name,
    initials,
    plan,
    direction,
    access,
    timezone: 'Europe/Dublin',
    program: id === 'oliver' ? null : 'foundation',
    sessions:
      id === 'oliver' ? [] : dates.map((date, index) => sessionFor(id, offset, date, index)),
  }));
  return {
    schema: 1,
    clients,
    exercises: catalog.map((exercise) => ({
      ...structuredClone(exercise),
      archived: false,
      tutorialUrl: '',
    })),
    programs: [programTemplate()],
    notes: {},
    reviews: {},
    assignments: [],
    audit: [],
  };
}

export const latestSession = (client) => client.sessions.at(-1) || null;
export const noteKey = (clientId, entryId) => `${clientId}:${entryId}`;

export function findEntry(data, clientId, entryId) {
  const client = data.clients.find((item) => item.id === clientId);
  for (const session of client?.sessions || []) {
    const entry = session.entries.find((item) => item.id === entryId);
    if (entry) return { client, session, entry };
  }
  throw new Error('Assignment does not belong to this client');
}

export function saveNote(data, clientId, entryId, visibility, text) {
  findEntry(data, clientId, entryId);
  if (!['client', 'private'].includes(visibility)) throw new Error('Invalid visibility');
  if (typeof text !== 'string' || text.length > 2000) throw new Error('Invalid note');
  const key = noteKey(clientId, entryId);
  data.notes[key] = { ...data.notes[key], [visibility]: text.trim() };
  return data.notes[key];
}

export function finishReview(data, clientId, entryId) {
  findEntry(data, clientId, entryId);
  data.reviews[noteKey(clientId, entryId)] = 'completed';
}

export function clientAssignment(data, clientId, entryId) {
  const { entry } = findEntry(data, clientId, entryId);
  return { ...structuredClone(entry), note: data.notes[noteKey(clientId, entryId)]?.client || '' };
}

export function trendFor(client, exerciseId) {
  return client.sessions
    .filter((session) => session.status !== 'skipped')
    .flatMap((session) => {
      const entry = session.entries.find((item) => item.exerciseId === exerciseId);
      const actual =
        entry?.actual.filter((value) => typeof value === 'number' && Number.isFinite(value)) || [];
      if (!actual.length) return [];
      return [
        {
          date: session.date,
          value: Math.max(...actual),
          target: Math.max(...entry.target),
          unit: entry.unit,
          entryId: entry.id,
        },
      ];
    });
}

export function comparisonFor(points) {
  if (points.length < 2) return null;
  const first = points[0].value;
  const latest = points.at(-1).value;
  return {
    first,
    latest,
    delta: latest - first,
    percent: first > 0 ? ((latest - first) / first) * 100 : null,
  };
}

export function pendingClients(data) {
  return data.clients.filter(
    (client) =>
      ['Pro', 'Pro+'].includes(client.plan) &&
      client.sessions.some(
        (session) =>
          session.date === latestSession(client)?.date &&
          session.entries.some(
            (entry) => entry.video && data.reviews[noteKey(client.id, entry.id)] !== 'completed',
          ),
      ),
  );
}

export function validYouTube(value) {
  try {
    const url = new URL(value);
    if (url.protocol !== 'https:' || url.username || url.password || url.port) return false;
    const host = url.hostname;
    const videoId =
      host === 'youtu.be'
        ? url.pathname.slice(1)
        : ['youtube.com', 'www.youtube.com', 'm.youtube.com'].includes(host)
          ? url.pathname === '/watch'
            ? url.searchParams.get('v')
            : /^\/(shorts|embed)\//.test(url.pathname)
              ? url.pathname.split('/')[2]
              : ''
          : '';
    return /^[A-Za-z0-9_-]{11}$/.test(videoId || '');
  } catch {
    return false;
  }
}

export function saveExercise(data, values) {
  const existing = data.exercises.find((exercise) => exercise.id === values.id);
  if (!values.name.uk.trim() || !values.name.en.trim()) throw new Error('names');
  if (values.name.uk.length > 120 || values.name.en.length > 120) throw new Error('names');
  if (!['sec', 'reps'].includes(values.unit)) throw new Error('unit');
  if (!['handstand', 'strength', 'mobility', 'fitness'].includes(values.direction))
    throw new Error('direction');
  if (values.tutorialUrl && !validYouTube(values.tutorialUrl)) throw new Error('video');
  if (
    existing &&
    existing.unit !== values.unit &&
    data.programs.some((program) =>
      program.weeks.some((week) =>
        week.sessions.some((session) => session.rows.some((row) => row.exerciseId === existing.id)),
      ),
    )
  )
    throw new Error('unitLocked');
  const exercise = {
    id: existing?.id || crypto.randomUUID(),
    name: { uk: values.name.uk.trim(), en: values.name.en.trim() },
    cue: { uk: values.cue.uk.trim(), en: values.cue.en.trim() },
    unit: values.unit,
    direction: values.direction,
    tutorialUrl: values.tutorialUrl.trim(),
    archived: existing?.archived || false,
  };
  if (existing) Object.assign(existing, exercise);
  else data.exercises.push(exercise);
  return exercise;
}

export function newProgram() {
  const id = crypto.randomUUID();
  const program = {
    id,
    name: { uk: '', en: '' },
    revision: 0,
    status: 'draft',
    published: [],
    weeks: [
      {
        id: `${id}-week`,
        sessions: [
          {
            id: `${id}-session`,
            name: 'A',
            block: { uk: 'Основна частина', en: 'Main block' },
            rows: [],
          },
        ],
      },
    ],
  };
  return program;
}

export function saveProgram(data, draft, expectedRevision) {
  const current = data.programs.find((program) => program.id === draft.id);
  if ((current?.revision || 0) !== expectedRevision) throw new Error('conflict');
  if (!draft.name.uk.trim() || !draft.name.en.trim()) throw new Error('names');
  if (
    !draft.weeks.length ||
    draft.weeks.some(
      (week) => !week.sessions.length || week.sessions.some((session) => !session.rows.length),
    )
  )
    throw new Error('emptyProgram');
  for (const week of draft.weeks) {
    for (const session of week.sessions) {
      for (const row of session.rows) {
        if (!data.exercises.some((exercise) => exercise.id === row.exerciseId))
          throw new Error('exercise');
        if (
          !row.targets.length ||
          row.targets.length > 10 ||
          row.targets.some((target) => !Number.isInteger(target) || target < 1 || target > 600)
        )
          throw new Error('target');
        if (!Number.isInteger(row.rest) || row.rest < 0 || row.rest > 3600) throw new Error('rest');
      }
    }
  }
  const program = {
    ...structuredClone(draft),
    name: { uk: draft.name.uk.trim(), en: draft.name.en.trim() },
    revision: expectedRevision + 1,
    status: 'draft',
    published: structuredClone(current?.published || []),
  };
  if (current) data.programs[data.programs.indexOf(current)] = program;
  else data.programs.push(program);
  return program;
}

export function publishProgram(data, programId) {
  const program = data.programs.find((item) => item.id === programId);
  if (!program || !program.revision) throw new Error('unsaved');
  const version = {
    number: program.published.length + 1,
    name: structuredClone(program.name),
    weeks: program.weeks.map((week) => ({
      ...structuredClone(week),
      sessions: week.sessions.map((session) => ({
        ...structuredClone(session),
        rows: session.rows.map((row) => {
          const exercise = data.exercises.find((item) => item.id === row.exerciseId);
          return {
            ...structuredClone(row),
            name: structuredClone(exercise.name),
            cue: structuredClone(exercise.cue),
            unit: exercise.unit,
            tutorialUrl: exercise.tutorialUrl,
          };
        }),
      })),
    })),
  };
  program.published.push(version);
  program.status = 'published';
  return version;
}

export function assignProgram(data, programId, clientId, startsOn) {
  const program = data.programs.find((item) => item.id === programId);
  const client = data.clients.find((item) => item.id === clientId);
  if (!client || client.access === 'inactive') throw new Error('access');
  const version = program?.published.at(-1);
  if (!version) throw new Error('unpublished');
  if (
    !/^\d{4}-\d{2}-\d{2}$/.test(startsOn) ||
    startsOn <= TODAY ||
    new Date(startsOn).toISOString().slice(0, 10) !== startsOn
  )
    throw new Error('future');
  const assignment = {
    id: crypto.randomUUID(),
    clientId,
    programId,
    startsOn,
    version: structuredClone(version),
  };
  data.assignments.push(assignment);
  return assignment;
}
