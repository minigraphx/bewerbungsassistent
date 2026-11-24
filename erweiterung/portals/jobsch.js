// jobs.ch: public search API on the same page, as in the skill `jobsuche` (20 per page at most).
(function () {
  const common = globalThis.bewerbungsbegleiterCommon || require('./common.js');
  const ROWS = 20;
  const ORIGIN = 'https://www.jobs.ch';

  function grades(values) {
    const numbers = (values || []).map(Number).filter((n) => n > 0);
    return numbers.length ? common.workload(Math.min(...numbers), Math.max(...numbers)) : '';
  }

  function toHit(doc, today = new Date()) {
    if (!doc || !doc.job_id || !doc.title) return null;
    const age = Number.isInteger(doc.age) ? doc.age : common.ageFromDate(doc.publication_date, today);
    return {
      portal: 'jobs.ch',
      portal_id: String(doc.job_id),
      stelle: doc.title,
      firma: doc.company_name || '',
      ort: doc.place || '',
      pensum: grades(doc.employment_grades),
      link: `${ORIGIN}/de/stellenangebote/detail/${encodeURIComponent(doc.job_id)}/`,
      alter_tage: age,
    };
  }

  function parseList(data, page) {
    if (!data || !Array.isArray(data.documents)) throw new common.PortalChanged('Die Suche liefert keine Liste mehr.');
    const hits = data.documents.map((doc) => toHit(doc)).filter(Boolean);
    if (data.documents.length && !hits.length) throw new common.PortalChanged('Die Treffer haben eine unbekannte Form.');
    // G123: jobs.ch has no ads pinned above the date order, so every hit counts towards the oldest age of the page.
    const ages = hits.map((hit) => hit.alter_tage).filter(Number.isInteger);
    const oldest = ages.length ? Math.max(...ages) : null;
    return { hits, more: page < (Number(data.num_pages) || 0), oldest };
  }

  async function list(query, page) {
    // Newest first (#395): a broad search has more pages than a query reads, and by relevance new ads sit past them.
    const params = new URLSearchParams({ rows: String(ROWS), page: String(page), query: query.keyword, sort: 'date' });
    if (query.place) params.set('location', query.place);
    return parseList(await common.fetchJson(`/api/v1/public/search?${params}`), page);
  }

  async function details(hit) {
    const data = await common.fetchJson(`/api/v1/public/search/job/${encodeURIComponent(hit.portal_id)}`);
    if (!data || typeof data !== 'object') throw new common.PortalChanged('Das Inserat hat eine unbekannte Form.');
    return { text: common.htmlToText(data.template_text || data.preview || '') };
  }

  const adapter = { name: 'jobs.ch', start: `${ORIGIN}/de/`, list, details, toHit, parseList };
  globalThis.bewerbungsbegleiterPortals = globalThis.bewerbungsbegleiterPortals || {};
  globalThis.bewerbungsbegleiterPortals['jobs.ch'] = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
