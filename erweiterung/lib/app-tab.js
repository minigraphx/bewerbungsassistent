// „Treffer in der App ansehen“ (MIN-405): no pile of tabs. Only pages where nothing can be half typed get replaced;
// the others do not all guard unsaved input, so a new tab is the safe choice there.
const APP_TABS = 'http://127.0.0.1/*';
const HITS_PAGE = 'treffer';
const REPLACEABLE_PATHS = ['/treffer', '/'];

function pageOf(tab, origin) {
  try {
    const address = new URL(tab.url);
    return address.origin === origin ? address.pathname : null;
  } catch {
    return null;  // no address visible, or none to read
  }
}

/**
 * @param {string} appUrl address of the running app, ending in a slash
 * @param {string} [entryUrl] the same with the token: this browser may not have a session of the app yet
 */
export async function showHits(appUrl, { tabs, windows }, entryUrl) {
  const target = new URL(HITS_PAGE, appUrl);
  if (entryUrl) target.search = new URL(entryUrl).search;
  const open = await tabs.query({ url: APP_TABS });
  const tab = REPLACEABLE_PATHS.map((path) => open.find((t) => pageOf(t, target.origin) === path)).find(Boolean);
  if (!tab) {
    await tabs.create({ url: target.href });
    return;
  }
  await tabs.update(tab.id, { url: target.href, active: true });
  await windows.update(tab.windowId, { focused: true });
}
