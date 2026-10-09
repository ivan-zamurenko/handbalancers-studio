import { ApiError, NetworkError } from '../api/client.js';

function stateForError(error) {
  if (error instanceof NetworkError) return 'offline';
  if (error instanceof ApiError && error.status === 409) return 'conflict';
  if (error instanceof ApiError && error.status === 401) return 'unauthorized';
  return 'error';
}

export function createSaveStatus() {
  let value = Object.freeze({ state: 'idle', error: null });

  return {
    get value() {
      return value;
    },
    setSaving() {
      value = Object.freeze({ state: 'saving', error: null });
    },
    setSaved() {
      value = Object.freeze({ state: 'saved', error: null });
    },
    setFailure(error) {
      value = Object.freeze({ state: stateForError(error), error });
    },
    reset() {
      value = Object.freeze({ state: 'idle', error: null });
    },
  };
}