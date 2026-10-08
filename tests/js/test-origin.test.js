import assert from 'node:assert/strict';
import test from 'node:test';
import { assertLocalTestOrigin, TEST_ORIGIN } from '../../tools/test-origin.mjs';

test('only dedicated loopback origin is accepted', () => {
  assert.equal(assertLocalTestOrigin(), TEST_ORIGIN);
  assert.equal(assertLocalTestOrigin('http://127.0.0.1:8765/'), TEST_ORIGIN);
});

for (const origin of [
  '', 'https://production.example', 'https://staging.example',
  'http://127.0.0.1:8000', 'http://localhost:8765', 'http://127.0.0.1.evil.example:8765',
  'http://127.0.0.1:8765@evil.example', 'http://user:password@127.0.0.1:8765',
  'http://127.0.0.1:8765/path', 'http://127.0.0.1:8765?redirect=external',
  'http://127.0.0.1:8765#fragment', 'file:///tmp/test', 'http://2130706433:8765',
]) {
  test(`refuses unsafe or ambiguous origin ${origin}`, () => {
    assert.throws(() => assertLocalTestOrigin(origin), /Unsafe test origin/);
  });
}
