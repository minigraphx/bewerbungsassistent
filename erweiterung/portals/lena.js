// LENA on berufsberatung.ch, the apprenticeship register of the cantons: the page fills its result list in the browser,
// so the list is read from the open page, after search.js opened the address from searchUrl. The ids of professions
// and places come from the suggestions of the search form; the details pages are rendered on the server.
(function () {
  const common = globalThis.bewerbungsbegleiterCommon || require('./common.js');
  const ORIGIN = 'https://www.berufsberatung.ch';
  const SEARCH = '/de/suche/lehrstellen';
  const TRIAL_SEARCH = '/de/suche/schnupperadressen'; // same form, same ids; the results are addresses (MIN-373)
  const TRIAL_ID = 'schnupperlehre-';
  const PROFESSION_FIELD = 'input[aria-label^="Beruf"]';
  const PLACE_FIELD = 'input[aria-label^="Ort oder PLZ"]';
  const OPTION = '[data-combobox-option]';
  const SUGGESTIONS_MS = 4000;
  const RESULTS_MS = 12000;
  const YEAR_IN_TITLE = /\s*\((20\d\d)\)\s*$/;
  const PLACE_IN_TEXT = /([A-ZÄÖÜÉÈ][^()]*?\([A-Z]{2}\))/; // „Biel/Bienne (BE)“, right after company and title
  const MORE = /Mehr anzeigen/;

  /** Resolves with the first truthy result of check, as soon as the page changes accordingly; null after the time. */
  function waitFor(check, timeoutMs) {
    return new Promise((resolve) => {
      const first = check();
      if (first) {
        resolve(first);
        return;
      }
      let observer = null;
      const timer = setTimeout(() => {
        observer.disconnect();
        resolve(check() || null);
      }, timeoutMs);
      observer = new MutationObserver(() => {
        const result = check();
        if (result) {
          clearTimeout(timer);
          observer.disconnect();
          resolve(result);
        }
      });
      observer.observe(document.body, { childList: true, subtree: true, characterData: true });
    });
  }

  function options() {
    return [...document.querySelectorAll(OPTION)].map((option) => ({
      value: option.getAttribute('value'),
      label: common.textOf(option).replace(/\s+\d+$/, ''),
    }));
  }

  /**
   * Type into a field of the page, which React notices through the input event. A tab in the background has no
   * focus and fires no focus event by itself, but the suggestions only open with one.
   */
  function typeInto(field, text) {
    field.focus();
    field.dispatchEvent(new FocusEvent('focusin', { bubbles: true }));
    field.value = text;
    field.dispatchEvent(new Event('input', { bubbles: true }));
  }

  /**
   * What to type for a profession: the whole name first, then less, because the suggestions search loosely.
   * A name in two forms („… / …“) types each form, since LENA suggests nothing for the pair.
   */
  function searchTerms(name) {
    return [...new Set(common.professionForms(name).flatMap((form) => {
      const clean = form.replace(/[(),]/g, ' ').replace(/\bFachrichtung\b/gi, ' ').replace(/\s+/g, ' ').trim();
      const short = clean.replace(/\b(EFZ|EBA)\b/g, ' ').replace(/\s+/g, ' ').trim();
      return [clean, short];
    }))];
  }

  async function suggestion(selector, terms, pick) {
    const field = document.querySelector(selector);
    if (!field) throw new common.PortalChanged('Das Suchformular wurde nicht gefunden.');
    for (const term of terms) {
      typeInto(field, term);
      const found = await waitFor(() => pick(options(), term), SUGGESTIONS_MS);
      if (found) {
        typeInto(field, '');
        return found;
      }
    }
    typeInto(field, '');
    return null;
  }

  function pickPlace(found, term) {
    const wanted = term.toLowerCase();
    if (/^\d{4}$/.test(term)) return found[0] || null;
    return found.find((option) => option.label.toLowerCase() === wanted) || null;
  }

  /** The address of the result list. Runs on the search page, whose form knows the ids. */
  async function searchUrl(query) {
    const profession = await suggestion(PROFESSION_FIELD, searchTerms(query.keyword),
      (found) => common.bestProfession(query.keyword, found, (option) => option.label));
    if (!profession) throw new Error(`Den Beruf „${query.keyword}“ kennt LENA nicht unter diesem Namen.`);
    const params = new URLSearchParams();
    if (query.place) {
      const place = await suggestion(PLACE_FIELD, [query.place], pickPlace);
      if (!place) throw new Error(`Den Ort „${query.place}“ kennt LENA nicht.`);
      params.set('mode', 'city');
      params.set('location', place.value);
      params.set('radius', String(query.radius));
    } else {
      params.set('canton', query.canton);
    }
    params.set('profession', profession.value);
    return `${ORIGIN}${searchPath(query)}?${params}`;
  }

  function searchPath(query) {
    return query.trial ? TRIAL_SEARCH : SEARCH;
  }

  function trialHit(card, query) {
    const link = card.querySelector('a[href*="/schnupperlehren/"]');
    const id = link && (link.getAttribute('href').match(/\/schnupperlehren\/(\d+)/) || [])[1];
    const title = common.textOf(card.querySelector('.search-result-title'));
    if (!id || !title) return null;
    const company = common.textOf(card.querySelector('.search-result-sup-title, .text-overline-small'));
    const place = (common.textOf(card).replace(company, '').replace(title, '').match(PLACE_IN_TEXT) || [])[1] || '';
    return {
      portal: 'LENA',
      portal_id: `${TRIAL_ID}${id}`,
      stelle: title,
      firma: company,
      ort: place.trim(),
      link: `${ORIGIN}/de/schnupperlehren/${id}`,
      art: 'Schnupperlehre',
      beruf: query.keyword,
    };
  }

  /** @returns {object|null} null when the title is unknown or the year is not wanted */
  function toHit(card, query) {
    if (query.trial) return trialHit(card, query);
    const link = card.querySelector('a[href*="/lehrstellen/"]');
    const id = link && (link.getAttribute('href').match(/\/lehrstellen\/(\d+)/) || [])[1];
    const title = common.textOf(card.querySelector('.search-result-title'));
    if (!id || !title) return null;
    const year = (title.match(YEAR_IN_TITLE) || [])[1] || '';
    if (query.years && query.years.length && year && !query.years.includes(Number(year))) return null;
    const company = common.textOf(card.querySelector('.search-result-sup-title, .text-overline-small'));
    const place = (common.textOf(card).replace(company, '').replace(title, '').match(PLACE_IN_TEXT) || [])[1] || '';
    const hit = {
      portal: 'LENA',
      portal_id: id,
      stelle: title.replace(YEAR_IN_TITLE, ''),
      firma: company,
      ort: place.trim(),
      link: `${ORIGIN}/de/lehrstellen/${id}`,
      art: 'Lehrstelle',
      beruf: query.keyword,
    };
    return year ? { ...hit, lehrbeginn: year } : hit;
  }

  function parseList(root, query) {
    const cards = [...root.querySelectorAll('.search-result')];
    const hits = cards.map((card) => toHit(card, query)).filter(Boolean);
    if (cards.length && !hits.length && !(query.years && query.years.length)) {
      throw new common.PortalChanged('Die Treffer haben eine unbekannte Form.');
    }
    const more = [...root.querySelectorAll('button')].some((button) => MORE.test(button.textContent));
    return { hits, more };
  }

  const cardCount = () => document.querySelectorAll('.search-result').length;

  /** Page 1 waits for the first results; each further page presses the button below the list. */
  async function list(query, page) {
    if (page === 1) {
      const shown = await waitFor(() => cardCount() > 0, RESULTS_MS);
      if (!shown && !document.querySelector(PROFESSION_FIELD)) {
        throw new common.PortalChanged('Die Trefferliste wurde nicht gefunden.');
      }
      return parseList(document, query);
    }
    const before = cardCount();
    const button = [...document.querySelectorAll('button')].find((candidate) => MORE.test(candidate.textContent));
    if (!button) return { hits: [], more: false };
    button.click();
    await waitFor(() => cardCount() > before, RESULTS_MS);
    return parseList(document, query);
  }

  function parseDetails(doc) {
    const main = doc.querySelector('main');
    if (!main) return { text: '' };
    const copy = main.cloneNode(true);
    copy.querySelectorAll('nav, button, script, style, form').forEach((node) => node.remove());
    return { text: common.htmlToText(copy.innerHTML) };
  }

  async function details(hit) {
    return parseDetails(await common.fetchPage(new URL(hit.link).pathname));
  }

  const adapter = {
    name: 'LENA', start: `${ORIGIN}${SEARCH}`, list, details, searchUrl, searchPath, toHit, parseList, parseDetails, searchTerms, pickPlace,
  };
  globalThis.bewerbungsbegleiterPortals = globalThis.bewerbungsbegleiterPortals || {};
  globalThis.bewerbungsbegleiterPortals.LENA = adapter;
  if (typeof module !== 'undefined') module.exports = adapter;
})();
