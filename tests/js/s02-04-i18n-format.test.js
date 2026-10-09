import assert from 'node:assert/strict';
import test from 'node:test';
import { formatDate, formatNumber } from '../../server/static/js/i18n/format.js';

test('number and date formatting use Intl for the selected locale', () => {
  const amount = 1234.5;
  const instant = new Date('2026-10-09T12:00:00Z');

  assert.equal(formatNumber(amount, 'en'), new Intl.NumberFormat('en').format(amount));
  assert.equal(formatNumber(amount, 'uk'), new Intl.NumberFormat('uk').format(amount));
  assert.equal(formatDate(instant, 'en'), new Intl.DateTimeFormat('en').format(instant));
  assert.equal(formatDate(instant, 'uk'), new Intl.DateTimeFormat('uk').format(instant));
  assert.equal(amount, 1234.5);
  assert.equal(instant.toISOString(), '2026-10-09T12:00:00.000Z');
});

test('unsupported locale falls back to Ukrainian formatting', () => {
  const amount = 1234.5;
  assert.equal(formatNumber(amount, 'fr-CA'), new Intl.NumberFormat('uk').format(amount));
});