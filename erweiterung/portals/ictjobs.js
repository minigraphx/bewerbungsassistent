// ictjobs.ch: result pages rendered on the server; the full text comes from the JobPosting data of the ad.
(function () {
  const common = globalThis.bewerbungsassistentCommon || require('./common.js');
  const ORIGIN = 'https://ictjobs.ch';

  function toHit(card) {
    const anchor = card.querySelector('a.job-card__link');
    const title = common.textOf(anchor);
    if (!anchor || !title) return null;
    const url = new URL(anchor.getAttribute('href'), ORIGIN);
    const link = `${url.origin}${url.pathname}`;
    const slug = url.pathname.split('/').filter(Boolean).pop();
    if (!slug) return null;
    const tags = [...card.querySelectorAll('.job-card__tags .tag')].map(common.textOf);
    return {
      portal: 'ictjobs',
      portal_id: url.pathname,
      stelle: title,
      firma: common.textOf(card.querySelector('.job-card__company .job-card__text')),
      ort: common.textOf(card.querySelector('.job-card__map_link .job-card__text')),
      pensum: tags.find((t) => /%|zeit/i.test(t) && !/CHF/.test(t)) || '',
      link,
      alter_tage: common.ageFromText(common.textOf(card.querySelector('.job-card__time'))),
    };
  }

  function parseList(doc, page) {
    if (!doc.querySelector('#top-list')) throw new common.PortalChanged('Die Trefferliste wurde nicht gefunden.');
    const cards = [...doc.querySelectorAll('article.job-card')];
    const hits = cards.map(toHit).filter(Boolean);
    if (cards.length && !hits.length) throw new common.PortalChanged('Die Treffer haben eine unbekannte Form.');
    const pages = [...doc.querySelectorAll('ul.paging a')].map((a) => Number(common.textOf(a))).filter(Boolean);
    return { hits, more: pages.some((n) => n > page) };
  }

  async function list(query, page) {
    const params = new URLSearchParams({ fs: query.keyword });
    if (query.region) params.set('fltr_location', query.region);
    const path = page > 1 ? `/page/${page}/` : '/';
    return parseList(await common.fetchPage(`${path}?${params}`), page);
  }

  function posting(doc) {
    for (const script of doc.querySelectorAll('script[type="application/ld+json"]')) {
      try {
        const data = JSON.parse(script.textContent);
        const items = Array.isArray(data['@graph']) ? data['@graph'] : [data];
        const found = items.find((item) => item && item['@type'] === 'JobPosting');
        if (found) return found;
      } catch (error) {
        // other structured data on the page; not ours
      }
    }
    return null;
  }

  async function details(hit) {
    const doc = await common.fetchPage(new URL(hit.link).pathname);
    const found = posting(doc);
    if (found) return { text: common.htmlToText(found.description || '') };
    const body = doc.querySelector('[class*="job-text__description"]');
    return { text: body ? common.htmlToText(body.innerHTML) : '' };
  }

  const adapter = { name: 'ictjobs', start: `${ORIGIN}/`, list, details, toHit, parseList };
  globalThis.bewerbungsassistentPortals = globalThis.bewerbungsassistentPortals || {};
  globalThis.bewerbungsassistentPortals.ictjobs = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
