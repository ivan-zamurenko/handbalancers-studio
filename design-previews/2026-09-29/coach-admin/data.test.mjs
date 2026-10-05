import assert from 'node:assert/strict';
import test from 'node:test';
import {
  freshData,
  latestSession,
  saveNote,
  finishReview,
  clientAssignment,
  noteKey,
  trendFor,
  comparisonFor,
  validYouTube,
  saveExercise,
  newProgram,
  saveProgram,
  publishProgram,
  assignProgram,
} from './data.js';

test('notes belong to one client and assignment; review is a separate action', () => {
  const data = freshData();
  const emma = data.clients[0];
  const entry = latestSession(emma).entries[0];
  saveNote(data, emma.id, entry.id, 'client', '  Visible feedback  ');
  saveNote(data, emma.id, entry.id, 'private', 'Coach only');
  assert.equal(data.reviews[noteKey(emma.id, entry.id)], undefined);
  const projection = clientAssignment(data, emma.id, entry.id);
  assert.equal(projection.note, 'Visible feedback');
  assert.ok(!JSON.stringify(projection).includes('Coach only'));
  assert.throws(() => saveNote(data, 'liam', entry.id, 'client', 'Wrong owner'));
  assert.throws(() => saveNote(data, emma.id, entry.id, 'public', 'Bad visibility'));
  finishReview(data, emma.id, entry.id);
  assert.equal(data.reviews[noteKey(emma.id, entry.id)], 'completed');
});

test('catalog and template edits cannot mutate completed history', () => {
  const data = freshData();
  const original = structuredClone(data.clients);
  data.exercises[0].name.uk = 'New exercise title';
  data.exercises[0].archived = true;
  data.programs[0].weeks[0].sessions[0].rows[0].targets[0] = 99;
  assert.deepEqual(data.clients, original);
});

test('charts derive best sets in the correct unit; missing values are not zero', () => {
  const data = freshData();
  const client = data.clients[0];
  const points = trendFor(client, 'handstand');
  assert.deepEqual(
    points.map((point) => point.value),
    [18, 20, 22, 23, 27, 29, 32, 34],
  );
  assert.ok(points.every((point) => point.unit === 'sec'));
  assert.equal(comparisonFor(points).delta, 16);
  client.sessions.at(-1).entries[0].actual = [null, null, null];
  assert.equal(trendFor(client, 'handstand').length, 7);
  assert.equal(comparisonFor([]), null);
  assert.equal(comparisonFor([{ value: 0 }, { value: 10 }]).percent, null);
  assert.deepEqual(trendFor(data.clients.at(-1), 'handstand'), []);
});

test('video links accept only HTTPS YouTube video URLs, without a network request', () => {
  for (const url of [
    'https://youtu.be/abcdefghijk',
    'https://www.youtube.com/watch?v=abcdefghijk',
    'https://youtube.com/shorts/abcdefghijk',
  ])
    assert.ok(validYouTube(url));
  for (const url of [
    'javascript:alert(1)',
    'http://youtu.be/abcdefghijk',
    'https://youtube.com.evil.invalid/watch?v=abcdefghijk',
    'https://user:pass@youtube.com/watch?v=abcdefghijk',
    'https://youtube.com/@channel',
    'https://127.0.0.1/watch?v=abcdefghijk',
    'https://youtu.be/short',
  ])
    assert.equal(validYouTube(url), false);
});

test('create, save, publish and assign are separate; past records stay immutable', () => {
  const data = freshData();
  const history = structuredClone(data.clients);
  const exercise = saveExercise(data, {
    name: { uk: 'Тест', en: 'Test' },
    cue: { uk: '', en: '' },
    unit: 'reps',
    direction: 'strength',
    tutorialUrl: '',
  });
  const draft = newProgram();
  assert.throws(() => saveProgram(data, draft, 0), /names/);
  draft.name = { uk: 'Моя програма', en: 'My program' };
  assert.throws(() => saveProgram(data, draft, 0), /emptyProgram/);
  draft.weeks[0].sessions[0].rows.push({
    id: 'row',
    exerciseId: exercise.id,
    targets: [8, 8, 8],
    rest: 60,
  });
  const saved = saveProgram(data, draft, 0);
  assert.equal(saved.revision, 1);
  assert.throws(() => assignProgram(data, saved.id, 'emma', '2026-10-01'), /unpublished/);
  const version = publishProgram(data, saved.id);
  assert.equal(version.number, 1);
  assert.throws(() => assignProgram(data, saved.id, 'emma', '2026-09-28'), /future/);
  assert.throws(() => assignProgram(data, saved.id, 'anna', '2026-10-01'), /access/);
  const assignment = assignProgram(data, saved.id, 'emma', '2026-10-01');
  exercise.name.uk = 'Changed title';
  assert.equal(assignment.version.weeks[0].sessions[0].rows[0].name.uk, 'Тест');
  saved.weeks[0].sessions[0].rows[0].targets[0] = 99;
  assert.equal(version.weeks[0].sessions[0].rows[0].targets[0], 8);
  assert.deepEqual(data.clients, history);
});

test('stale program revisions, invalid targets, URLs and incompatible units are rejected', () => {
  const data = freshData();
  const draft = structuredClone(data.programs[0]);
  assert.throws(() => saveProgram(data, draft, 0), /conflict/);
  draft.weeks[0].sessions[0].rows[0].targets[0] = 0;
  assert.throws(() => saveProgram(data, draft, 1), /target/);
  draft.weeks[0].sessions[0].rows[0].targets[0] = 20;
  draft.weeks[0].sessions[0].rows[0].rest = -1;
  assert.throws(() => saveProgram(data, draft, 1), /rest/);
  assert.throws(() => saveExercise(data, { ...data.exercises[0], unit: 'reps' }), /unitLocked/);
  assert.throws(
    () => saveExercise(data, { ...data.exercises[0], tutorialUrl: 'https://example.com/video' }),
    /video/,
  );
  assert.throws(
    () => saveExercise(data, { ...data.exercises[0], name: { uk: '', en: 'Present' } }),
    /names/,
  );
});
