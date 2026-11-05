// jobscout24.ch: result pages rendered on the server, read with DOMParser, as in the skill `jobsuche`.
(function () {
  const common = globalThis.bewerbungsbegleiterCommon || require('./common.js');
  const PAGE_SIZE = 20;
  const ORIGIN = 'https://www.jobscout24.ch';

  function toHit(item) {
    const id = item.getAttribute('data-job-id');
    const detail = item.getAttribute('data-job-detail-url');
    const title = common.textOf(item.querySelector('a.job-title, .job-title'));
    if (!id || !detail || !title) return null;
    const [company, place] = [...item.querySelectorAll('p.job-attributes span')].map(common.textOf);
    const tags = [...item.querySelectorAll('.job-tags .tag')].map(common.textOf);
    return {
      portal: 'jobscout24',
      portal_id: id,
      stelle: title,
      firma: company || '',
      ort: place || '',
      pensum: (tags.find((t) => /\d+\s*(-|–|%)/.test(t)) || '').replace(/\s*-\s*/, '–'),
      link: new URL(detail, ORIGIN).href,
      alter_tage: common.ageFromText(common.textOf(item.querySelector('.job-date'))),
    };
  }

  function parseList(doc) {
    const items = [...doc.querySelectorAll('li.job-list-item')];
    // The heading ("24 Python Stellen in Bern gefunden", also "0 … gefunden") shows the page is still known.
    if (!items.length && !/gefunden/i.test(common.textOf(doc.querySelector('h1')))) {
      throw new common.PortalChanged('Die Trefferliste wurde nicht gefunden.');
    }
    const hits = items.map(toHit).filter(Boolean);
    if (items.length && !hits.length) throw new common.PortalChanged('Die Treffer haben eine unbekannte Form.');
    return { hits, more: items.length >= PAGE_SIZE };
  }

  async function list(query, page) {
    const params = new URLSearchParams({ ft: query.keyword });
    if (query.postalCode) params.set('psz', query.postalCode);
    if (page > 1) params.set('p', String(page));
    return parseList(await common.fetchPage(`/de/jobs/?${params}`));
  }

  async function details(hit) {
    const doc = await common.fetchPage(new URL(hit.link).pathname);
    const body = doc.querySelector('.job-description') || doc.querySelector('.job-details');
    // Some companies show their ad in a frame that cannot be read; then the text stays empty.
    return { text: body ? common.htmlToText(body.innerHTML) : '' };
  }

  const adapter = { name: 'jobscout24', start: `${ORIGIN}/de/jobs/`, list, details, toHit, parseList };
  globalThis.bewerbungsbegleiterPortals = globalThis.bewerbungsbegleiterPortals || {};
  globalThis.bewerbungsbegleiterPortals.jobscout24 = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
