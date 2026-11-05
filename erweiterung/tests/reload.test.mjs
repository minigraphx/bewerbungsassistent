import assert from 'node:assert/strict';
import { test } from 'node:test';

import { reloadForAppVersion, siteAccessControl } from '../lib/reload.js';

function access({ granted = true, busy = false, failing = false, removed = true } = {}) {
  const log = [];
  const control = siteAccessControl({
    has: async () => granted,
    remove: async () => {
      log.push('remove');
      if (failing) throw new Error('kaputt');
      return removed;
    },
    forget: async () => log.push('forget'),
    busy: async () => busy,
    restart: () => log.push('restart'),
  });
  return { control, log };
}

test('giving back the access reloads, because Chrome takes the portals of the manifest along', async () => {
  const { control, log } = access();
  assert.deepEqual(await control.release(), { abgegeben: true });
  assert.deepEqual(log, ['remove', 'forget', 'restart']);
});

test('without a grant nothing is removed: removing would still take the portals away', async () => {
  const { control, log } = access({ granted: false });
  assert.deepEqual(await control.release(), { abgegeben: true });
  assert.deepEqual(log, ['forget']);
});

test('during a search or an open form it waits and keeps the mark, so a later contact tries again', async () => {
  const { control, log } = access({ busy: true });
  assert.deepEqual(await control.release(), { abgegeben: false, spaeter: true });
  assert.deepEqual(log, []);
});

test('if Chrome keeps the access, the mark stays and a later contact tries again', async () => {
  const { control, log } = access({ removed: false });
  assert.deepEqual(await control.release(), { abgegeben: false, spaeter: true });
  assert.deepEqual(log, ['remove']);
});

test('a failed removal keeps the mark and does not reload', async () => {
  const { control, log } = access({ failing: true });
  await assert.rejects(control.release(), /kaputt/);
  assert.deepEqual(log, ['remove']);
});

function versions({ tried = null, busy = false, ...rest } = {}) {
  const log = [];
  const run = () => reloadForAppVersion({
    appVersion: '0.3.0', appRunning: true, ownVersion: '0.2.1', unpacked: true,
    busy: async () => busy,
    tried: async () => tried,
    remember: async (version) => { tried = version; log.push(`remember ${version}`); },
    restart: () => log.push('restart'),
    ...rest,
  });
  return { run, log };
}

test('another version in the app reloads the extension once per version', async () => {
  const { run, log } = versions();
  assert.equal(await run(), true);
  assert.equal(await run(), false, 'the folder did not change: no loop');
  assert.deepEqual(log, ['remember 0.3.0', 'restart']);
});

test('a newer version after that reloads again', async () => {
  const { run, log } = versions({ tried: '0.2.9' });
  assert.equal(await run(), true);
  assert.deepEqual(log, ['remember 0.3.0', 'restart']);
});

for (const [name, change] of [
  ['the same version', { appVersion: '0.2.1' }],
  ['no version from the app', { appVersion: undefined }],
  ['an app that does not run: the folder may still be old', { appRunning: false }],
  ['a version from the store: the store updates it', { unpacked: false }],
  ['a search or an open form', { busy: async () => true }],
]) {
  test(`no reload with ${name}`, async () => {
    const { run, log } = versions(change);
    assert.equal(await run(), false);
    assert.deepEqual(log, []);
  });
}
