// job-room.ch (Arbeitsmarktplattform des Bundes): JSON API on the same page, as in the skill `jobsuche`.
(function () {
  const common = globalThis.bewerbungsbegleiterCommon || require('./common.js');
  const PAGE_SIZE = 100;
  const ORIGIN = 'https://www.job-room.ch';

  /** job-room keeps ads as Markdown with escaped characters ("\\-", "**"); the AI and the person want plain text. */
  function markdownToText(text) {
    return String(text || '').replace(/\\([\\`*_{}[\]()#+\-.!|])/g, '$1').replace(/\*\*|__/g, '');
  }

  function description(content) {
    const texts = (content && content.jobDescriptions) || [];
    return texts.find((d) => d.languageIsoCode === 'de') || texts[0] || {};
  }

  /** One result of the search API as hit; null when the shape is unknown. */
  function toHit(item, today = new Date()) {
    const ad = item && item.jobAdvertisement;
    const content = ad && ad.jobContent;
    if (!ad || !ad.id || !content) return null;
    const location = content.location || {};
    const employment = content.employment || {};
    return {
      portal: 'job-room',
      portal_id: String(ad.id),
      stelle: description(content).title || '',
      firma: (content.company && content.company.name) || '',
      ort: [location.postalCode, location.city].filter(Boolean).join(' '),
      pensum: common.workload(employment.workloadPercentageMin, employment.workloadPercentageMax),
      link: `${ORIGIN}/job-search/${encodeURIComponent(ad.id)}`,
      alter_tage: common.ageFromDate((ad.publication && ad.publication.startDate) || ad.createdTime, today),
    };
  }

  function parseList(data, page) {
    if (!Array.isArray(data)) throw new common.PortalChanged('Die Suche liefert keine Liste mehr.');
    const hits = data.map((item) => toHit(item)).filter(Boolean);
    if (data.length && !hits.length) throw new common.PortalChanged('Die Treffer haben eine unbekannte Form.');
    return { hits, more: data.length === PAGE_SIZE && page < 10 };
  }

  async function list(query, page) {
    const body = {
      workloadPercentageMin: 0, workloadPercentageMax: 100, permanent: null, companyName: null,
      onlineSince: query.maxAge, displayRestricted: false, professionCodes: [], keywords: [query.keyword],
      communalCodes: [], cantonCodes: query.cantons || [],
    };
    const url = `/jobadservice/api/jobAdvertisements/_search?page=${page - 1}&size=${PAGE_SIZE}&sort=date_desc`;
    const data = await common.fetchJson(url, {
      method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
    });
    return parseList(data, page);
  }

  async function details(hit) {
    const data = await common.fetchJson(`/jobadservice/api/jobAdvertisements/${encodeURIComponent(hit.portal_id)}`);
    if (!data || !data.jobContent) throw new common.PortalChanged('Das Inserat hat eine unbekannte Form.');
    return { text: common.htmlToText(markdownToText(description(data.jobContent).description)) };
  }

  const adapter = { name: 'job-room', start: `${ORIGIN}/home/job-seeker`, list, details, toHit, parseList, markdownToText };
  globalThis.bewerbungsbegleiterPortals = globalThis.bewerbungsbegleiterPortals || {};
  globalThis.bewerbungsbegleiterPortals['job-room'] = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
