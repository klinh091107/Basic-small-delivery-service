import test from 'node:test';
import assert from 'node:assert/strict';
import { normalizePhone, totalQuantity } from './validation.js';

test('international numbers normalize consistently', () => {
  assert.equal(normalizePhone('+84 90 123 4567'), '+84901234567');
  assert.equal(normalizePhone('+44 20 7946 0018'), '+442079460018');
  assert.equal(normalizePhone('+1 (202) 555-0123'), '+12025550123');
  for (const phone of ['0901234567', '+123', '+84abc901234567']) assert.throws(() => normalizePhone(phone));
});
test('quantity sums all lines without decimal boundary errors', () => {
  assert.equal(totalQuantity([{quantity:49.9},{quantity:0.1}]).toString(), '50');
  assert.equal(totalQuantity([{quantity:25},{quantity:25.01}]).greaterThan(50), true);
});
