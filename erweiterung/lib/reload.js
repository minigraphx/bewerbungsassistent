// When the extension loads itself anew. It ends the service worker and clears storage.session, so never during work.

/**
 * The access to all pages goes with the own key (MIN-348), but Chrome's permissions.remove of <all_urls> also takes
 * the portals of the manifest away until the extension is loaded again. Hence the reload right after it.
 * Without a grant there is nothing to give back, and removing would still do that damage.
 */
export function siteAccessControl({ has, remove, forget, busy, restart }) {
  return {
    async release() {
      if (!(await has())) {
        await forget();
        return { abgegeben: true };
      }
      if (await busy()) return { abgegeben: false, spaeter: true };
      await remove();
      await forget();
      restart();
      return { abgegeben: true };
    },
  };
}

/**
 * The app replaces the folder of an unpacked extension when it starts with a new version (MIN-382), and Chrome only
 * reads that folder on a reload. Once per version: if the folder holds something else, a loop would help nobody.
 * @returns {Promise<boolean>} whether a reload was started
 */
export async function reloadForAppVersion({ appVersion, appRunning, ownVersion, unpacked, busy, tried, remember, restart }) {
  if (!appVersion || !appRunning || !unpacked || appVersion === ownVersion) return false;
  if (await busy() || await tried() === appVersion) return false;
  await remember(appVersion);
  restart();
  return true;
}
