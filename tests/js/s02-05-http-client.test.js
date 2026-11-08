import assert from 'node:assert/strict';
import test from 'node:test';
import { ApiError, NetworkError, requestApi } from '../../server/static/js/api/client.js';
import { createSaveStatus } from '../../server/static/js/state/save-status.js';

const errorResponse = (status, code, messageKey = `errors.${code}`) => new Response(
  JSON.stringify({
    error: {
      code,
      message_key: messageKey,
      field_errors: [],
      request_id: 'a'.repeat(32),
    },
  }),
  { status, headers: { 'content-type': 'application/json' } },
);

test('credentials_same_origin: only same-origin requests receive cookies and CSRF', async () => {
  const calls = [];
  const fetchImpl = async (url, options) => {
    calls.push({ url: new URL(url), options });
    return new Response('{}', { status: 200 });
  };

  await requestApi('/api/profile', {
    baseUrl: 'https://studio.test',
    method: 'POST',
    body: { first_name: 'Олена' },
    documentObject: {
      querySelector(selector) {
        assert.equal(selector, 'meta[name="csrf-token"]');
        return { content: 'csrf-token' };
      },
    },
    fetchImpl,
  });
  await requestApi('https://third-party.test/collect', {
    baseUrl: 'https://studio.test',
    method: 'POST',
    csrfToken: 'must-not-leak',
    body: { event: 'view' },
    fetchImpl,
  });

  assert.equal(calls[0].options.credentials, 'same-origin');
  assert.equal(calls[0].options.headers.get('X-CSRF-Token'), 'csrf-token');
  assert.equal(calls[0].options.headers.get('Content-Type'), 'application/json');
  assert.equal(calls[1].options.credentials, 'omit');
  assert.equal(calls[1].options.headers.get('X-CSRF-Token'), null);
});

test('no_blind_retry_mutation: failed POST is issued once without a generated key', async () => {
  let callCount = 0;
  await assert.rejects(
    requestApi('/api/programs', {
      baseUrl: 'https://studio.test',
      method: 'POST',
      body: { name: 'draft' },
      fetchImpl: async () => {
        callCount += 1;
        return errorResponse(503, 'service_unavailable');
      },
    }),
    error => error instanceof ApiError && error.status === 503,
  );
  assert.equal(callCount, 1);
});

test('conflict_preserves_input: 409 maps to conflict without changing draft', async () => {
  const draft = { title: 'Unsaved title', row_version: 4 };
  const original = structuredClone(draft);
  const saveStatus = createSaveStatus();

  try {
    await requestApi('/api/programs/1', {
      baseUrl: 'https://studio.test',
      method: 'PUT',
      body: draft,
      fetchImpl: async () => errorResponse(409, 'conflict'),
    });
  } catch (error) {
    saveStatus.setFailure(error);
  }

  assert.deepEqual(draft, original);
  assert.equal(saveStatus.value.state, 'conflict');
  assert.equal(saveStatus.value.error.code, 'conflict');
});

test('unauthorized_redirect: 401 marks unauthorized and does not replace the draft', async () => {
  const draft = { note: 'Keep this local draft' };
  const original = structuredClone(draft);
  const saveStatus = createSaveStatus();

  try {
    await requestApi('/api/workouts/current', {
      baseUrl: 'https://studio.test',
      method: 'POST',
      body: draft,
      fetchImpl: async () => errorResponse(401, 'unauthorized'),
    });
  } catch (error) {
    saveStatus.setFailure(error);
  }

  assert.deepEqual(draft, original);
  assert.equal(saveStatus.value.state, 'unauthorized');
  assert.equal(saveStatus.value.error.code, 'unauthorized');
});

test('network failure remains distinct from a business response', async () => {
  await assert.rejects(
    requestApi('/api/profile', {
      baseUrl: 'https://studio.test',
      fetchImpl: async () => { throw new TypeError('connection reset'); },
    }),
    error => error instanceof NetworkError && error.kind === 'network',
  );
});

test('local loading options are not forwarded to fetch', async () => {
  await requestApi('/api/example', {
    loading: {mode: 'button', target: {localOnly: true}},
    fetchImpl: async (_url, options) => {
      assert.equal(Object.hasOwn(options, 'loading'), false);
      return new Response(null, {status: 204});
    },
  });
});
