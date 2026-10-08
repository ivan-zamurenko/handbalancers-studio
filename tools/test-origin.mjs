// A dedicated numeric loopback endpoint, distinct from the normal dev server.
export const TEST_ORIGIN = 'http://127.0.0.1:8765';

export function assertLocalTestOrigin(value = TEST_ORIGIN) {
  if (value !== TEST_ORIGIN && value !== `${TEST_ORIGIN}/`) {
    // Do not echo user-supplied URLs: they may contain credentials.
    throw new Error('Unsafe test origin: use only http://127.0.0.1:8765');
  }
  return TEST_ORIGIN;
}
