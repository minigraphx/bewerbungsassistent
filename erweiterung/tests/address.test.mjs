// These modules know nothing of the text set, so their messages stay neutral for people who chose du.
import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';

for (const name of ['sites.js', 'progress.js']) {
  test(`${name} does not use the formal address`, () => {
    const source = readFileSync(new URL(`../lib/${name}`, import.meta.url), 'utf8');
    assert.doesNotMatch(source, /\b(Sie|Ihr|Ihre|Ihrem|Ihren|Ihrer|Ihnen)\b/);
  });
}
