// yousty.ch: result pages rendered on the server, read with DOMParser. The professions have fixed ids, which the
// suggestions of the search form list; the text of a place is what the form itself sends.
(function () {
  const common = globalThis.bewerbungsassistentCommon || require('./common.js');
  const ORIGIN = 'https://www.yousty.ch';
  const SEARCH = '/de-CH/lehrstellen';
  const PROFESSIONS = `${SEARCH}/apprenticeship_jobs/for_autocomplete`;
  const PROFILE = /\/lehrstellen\/profile\/(\d+)/;
  const FOUND = /[\d’']+ Lehrstellen? gefunden/;
  const NONE = /Keine Lehrstelle/;
  const YEAR = /20\d\d/; // the chip reads „2027verfügbar“
  let professions = null;

  /** Open years of a result, e.g. ['2027', '2028']; a trial apprenticeship (Schnupperlehre) is not one of them. */
  function openYears(item) {
    return [...item.querySelectorAll('.availability.available')]
      .map((chip) => (common.textOf(chip).match(YEAR) || [])[0])
      .filter(Boolean);
  }

  /** @returns {object|null} null for offers that are no apprenticeship (school offers) or not in the wanted years */
  function toHit(item, query) {
    const link = item.querySelector('a[href*="/lehrstellen/profile/"]');
    const id = link && (link.getAttribute('href').match(PROFILE) || [])[1];
    const title = common.textOf(item.querySelector('.title'));
    if (!id || !title) return null;
    const years = openYears(item);
    const wanted = query.years && query.years.length ? years.filter((year) => query.years.includes(Number(year))) : years;
    if (!wanted.length) return null;
    const [company, place] = [...item.querySelectorAll('.company-info strong')].map(common.textOf);
    const url = new URL(link.getAttribute('href'), ORIGIN);
    return {
      portal: 'yousty',
      portal_id: id,
      stelle: title,
      firma: company || '',
      ort: place || '',
      link: `${ORIGIN}${url.pathname}`,
      art: 'Lehrstelle',
      beruf: query.keyword,
      lehrbeginn: wanted.join(', '),
    };
  }

  function parseList(doc, query, page) {
    const text = doc.body ? doc.body.textContent : '';
    const counted = FOUND.test(text);
    // Later pages have no count. Without any hit the page offers other apprenticeships instead: not what was asked for.
    if (page === 1 && !counted) {
      if (NONE.test(text)) return { hits: [], more: false };
      throw new common.PortalChanged('Die Trefferliste wurde nicht gefunden.');
    }
    const items = [...doc.querySelectorAll('.result')];
    if (counted && !items.length) throw new common.PortalChanged('Die Treffer wurden nicht gefunden.');
    const hits = items.map((item) => toHit(item, query)).filter(Boolean);
    const more = [...doc.querySelectorAll('a')].some((a) => /^nächste/i.test(common.textOf(a)));
    return { hits, more };
  }

  async function professionList() {
    if (professions) return professions;
    const ask = (eba) => common.fetchJson(`${PROFESSIONS}?${new URLSearchParams({
      eba: String(eba), with_specializations: 'true', include_blank: 'false', with_organization: 'true',
    })}`);
    const answers = await Promise.all([ask(false), ask(true)]);
    if (!answers.every(Array.isArray)) throw new common.PortalChanged('Die Liste der Berufe hat eine unbekannte Form.');
    professions = answers.flat();
    return professions;
  }

  async function knownPlace(place) {
    const found = await common.fetchJson(`/places/for_autocomplete?${new URLSearchParams({ locale: 'de-CH', term: place })}`);
    if (!Array.isArray(found)) throw new common.PortalChanged('Die Orte haben eine unbekannte Form.');
    return found.some((option) => String(option.label).toLowerCase() === place.toLowerCase());
  }

  function searchUrl(query, job, page) {
    const params = new URLSearchParams();
    if (query.place) {
      params.set('place', query.place);
      params.set('job', job);
      params.set('distance', String(query.radius));
    }
    if (query.years && query.years.length === 1) params.set('year', String(query.years[0]));
    if (page > 1) params.set('page', String(page));
    const path = query.place ? SEARCH : `${SEARCH}/${encodeURIComponent(query.canton)}/${encodeURIComponent(job)}`;
    return `${path}?${params}`;
  }

  async function list(query, page) {
    const job = common.bestProfession(query.keyword, await professionList(), (option) => option.label);
    if (!job) throw new Error(`Den Beruf „${query.keyword}“ kennt yousty nicht unter diesem Namen.`);
    if (query.place && page === 1 && !(await knownPlace(query.place))) {
      throw new Error(`Den Ort „${query.place}“ kennt yousty nicht.`);
    }
    return parseList(await common.fetchPage(searchUrl(query, job.id, page)), query, page);
  }

  /** The ad is in the page as structured data (schema.org JobPosting). */
  function parseDetails(doc) {
    const postings = [...doc.querySelectorAll('script[type="application/ld+json"]')].map((script) => {
      try {
        return JSON.parse(script.textContent);
      } catch {
        return null;
      }
    });
    const posting = postings.find((entry) => entry && entry['@type'] === 'JobPosting');
    return { text: posting ? common.htmlToText(posting.description) : '' };
  }

  async function details(hit) {
    return parseDetails(await common.fetchPage(new URL(hit.link).pathname));
  }

  const adapter = { name: 'yousty', start: `${ORIGIN}${SEARCH}`, list, details, toHit, parseList, parseDetails, searchUrl };
  globalThis.bewerbungsassistentPortals = globalThis.bewerbungsassistentPortals || {};
  globalThis.bewerbungsassistentPortals.yousty = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
