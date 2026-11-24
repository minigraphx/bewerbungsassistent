// jobs.ch: the semantic search the website runs by default (G124), the classic public API as fallback, 20 per page.
(function () {
  const common = globalThis.bewerbungsbegleiterCommon || require('./common.js');
  const ROWS = 20;
  const ORIGIN = 'https://www.jobs.ch';
  // Not a documented API: the website's own search. It answers pages of www.jobs.ch (CORS), so no host permission.
  const SEMANTIC_URL = 'https://job-search-api.jobs.ch/search/semantic';

  function grades(values) {
    const numbers = (values || []).map(Number).filter((n) => n > 0);
    return numbers.length ? common.workload(Math.min(...numbers), Math.max(...numbers)) : '';
  }

  function link(id) {
    return `${ORIGIN}/de/stellenangebote/detail/${encodeURIComponent(id)}/`;
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
      link: link(doc.job_id),
      alter_tage: age,
    };
  }

  /** A hit of the semantic search; its id is the job_id of the classic API, so details load the same way. */
  function semanticHit(doc, today = new Date()) {
    if (!doc || !doc.id || !doc.title) return null;
    const [location] = Array.isArray(doc.locations) ? doc.locations : [];
    return {
      portal: 'jobs.ch',
      portal_id: String(doc.id),
      stelle: doc.title,
      firma: (doc.company && doc.company.name) || '',
      ort: doc.place || (location && location.city) || '',
      pensum: grades(doc.employmentGrades),
      link: link(doc.id),
      alter_tage: common.ageFromDate(doc.publicationDate, today),
    };
  }

  /** Hits of a page, whether more pages follow and the age of its oldest ad. */
  function page(documents, toHitOf, more) {
    if (!Array.isArray(documents)) throw new common.PortalChanged('Die Suche liefert keine Liste mehr.');
    const hits = documents.map(toHitOf).filter(Boolean);
    if (documents.length && !hits.length) throw new common.PortalChanged('Die Treffer haben eine unbekannte Form.');
    // G123: jobs.ch has no ads pinned above the date order, so every hit counts towards the oldest age of the page.
    const ages = hits.map((hit) => hit.alter_tage).filter(Number.isInteger);
    const oldest = ages.length ? Math.max(...ages) : null;
    return { hits, more, oldest };
  }

  function parseList(data, number) {
    return page(data && data.documents, (doc) => toHit(doc), number < (Number(data && data.num_pages) || 0));
  }

  function parseSemantic(data, number, today = new Date()) {
    return page(data && data.documents, (doc) => semanticHit(doc, today), number < (Number(data && data.numPages) || 0));
  }

  /** The search parameters both engines share: newest first (#395), so a query's pages hold the ads since the last run. */
  function searchParams(query, number) {
    const params = new URLSearchParams({ rows: String(ROWS), page: String(number), query: query.keyword, sort: 'date' });
    if (query.place) params.set('location', query.place);
    return params;
  }

  /** Why the semantic search failed, in words the run can show; a network error says nothing useful. */
  function fallbackReason(error) {
    const message = String((error && error.message) || '');
    return (error && error.changed) || /^Antwort \d+$/.test(message) ? message : 'keine Antwort';
  }

  async function list(query, number) {
    const params = searchParams(query, number);
    try {
      // Without cookies: the semantic search needs none, and the person's jobs.ch session stays on jobs.ch.
      return parseSemantic(await common.fetchJson(`${SEMANTIC_URL}?${params}`, { credentials: 'omit' }), number);
    } catch (error) {
      const classic = parseList(await common.fetchJson(`/api/v1/public/search?${params}`), number);
      return { ...classic, fallback: fallbackReason(error) };
    }
  }

  async function details(hit) {
    const data = await common.fetchJson(`/api/v1/public/search/job/${encodeURIComponent(hit.portal_id)}`);
    if (!data || typeof data !== 'object') throw new common.PortalChanged('Das Inserat hat eine unbekannte Form.');
    return { text: common.htmlToText(data.template_text || data.preview || '') };
  }

  const adapter = { name: 'jobs.ch', start: `${ORIGIN}/de/`, list, details, toHit, parseList, parseSemantic };
  globalThis.bewerbungsbegleiterPortals = globalThis.bewerbungsbegleiterPortals || {};
  globalThis.bewerbungsbegleiterPortals['jobs.ch'] = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
