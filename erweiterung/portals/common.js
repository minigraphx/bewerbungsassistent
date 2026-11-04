// Shared helpers of the portal adapters. Injected into the portal tab before the adapter (isolated world)
// and loaded by the tests in Node. Adapters register under globalThis.bewerbungsassistentPortals.
(function () {
  const DAY_MS = 24 * 60 * 60 * 1000;
  const ENTITIES = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'", nbsp: ' ', shy: '' };

  /** The portal answered, but not in the expected form: its pages or interface changed. */
  class PortalChanged extends Error {
    constructor(message) {
      super(message);
      this.changed = true;
    }
  }

  /** @param {string} text */
  function decodeEntities(text) {
    return text
      .replace(/&#(\d+);/g, (_, n) => String.fromCodePoint(Number(n)))
      .replace(/&#x([0-9a-f]+);/gi, (_, n) => String.fromCodePoint(parseInt(n, 16)))
      .replace(/&([a-z]+);/gi, (match, name) => (name.toLowerCase() in ENTITIES ? ENTITIES[name.toLowerCase()] : match));
  }

  /**
   * HTML of an ad as plain text: blocks become lines, list items get a dash; scripts and styles are dropped.
   * @param {string} html
   * @returns {string}
   */
  function htmlToText(html) {
    const text = String(html || '')
      .replace(/<(script|style|noscript)[\s\S]*?<\/\1>/gi, ' ')
      .replace(/<li[^>]*>/gi, '\n- ')
      .replace(/<br\s*\/?>/gi, '\n')
      .replace(/<\/(p|h[1-6]|ul|ol)>/gi, '\n\n')
      .replace(/<\/(div|section|article|tr)>/gi, '\n')
      .replace(/<[^>]+>/g, ' ');
    return decodeEntities(text)
      .replace(/[​-‍⁠﻿]/g, '')
      .split('\n')
      .map((line) => line.replace(/[ \t ]+/g, ' ').trim())
      .filter((line, i, lines) => line || (i > 0 && lines[i - 1]))
      .join('\n')
      .trim();
  }

  /** Days since an ISO date, or null. */
  function ageFromDate(iso, today = new Date()) {
    const time = Date.parse(iso);
    if (Number.isNaN(time)) return null;
    return Math.max(0, Math.floor((today.getTime() - time) / DAY_MS));
  }

  /** Days from short texts like "1 T", "2 W", "1+M" (jobscout24) or "vor 3 Wochen", "vor 5 Stunden" (ictjobs). */
  function ageFromText(text) {
    const value = String(text || '').trim();
    if (/heute|neu|stunde|minute/i.test(value)) return 0;
    if (/gestern/i.test(value)) return 1;
    const match = value.match(/(\d+)\s*\+?\s*(T|W|M|J|Tag|Woche|Monat|Jahr)/i);
    if (!match) return null;
    const factor = { T: 1, W: 7, M: 30, J: 365 }[match[2][0].toUpperCase()];
    return factor ? Number(match[1]) * factor : null;
  }

  /** Workload like "80–100 %" from a minimum and maximum. */
  function workload(min, max) {
    const low = Number(min) || 0;
    const high = Number(max) || 0;
    if (!low && !high) return '';
    if (!low || !high || low === high) return `${high || low} %`;
    return `${low}–${high} %`;
  }

  async function fetchJson(url, options = {}) {
    const response = await fetch(url, { credentials: 'include', ...options });
    if (!response.ok) throw new Error(`Antwort ${response.status}`);
    try {
      return await response.json();
    } catch (error) {
      throw new PortalChanged('Die Antwort ist kein JSON mehr.');
    }
  }

  async function fetchPage(url) {
    const response = await fetch(url, { credentials: 'include' });
    if (!response.ok) throw new Error(`Antwort ${response.status}`);
    return new DOMParser().parseFromString(await response.text(), 'text/html');
  }

  /** Text of an element of a parsed page, collapsed to one line. */
  function textOf(element) {
    return element ? element.textContent.replace(/\s+/g, ' ').trim() : '';
  }

  const FILLER_WORDS = new Set(['fachrichtung', 'schwerpunkt', 'und', 'mit', 'im', 'der', 'die', 'das']);

  /** One word of a profession without its gender form: Fachfrau, Fachmann → fach; Assistentin → assistent. */
  function neutralWord(word) {
    return word
      .replace(/^köchin$/, 'koch')
      .replace(/euse$/, 'eur')
      .replace(/(frau|mann)$/, '')
      .replace(/(er|ent|ant|ist|eur|or)in$/, '$1');
  }

  /**
   * The words of a profession, so that the name in the search profile and the name on a portal can be compared:
   * „Fachfrau Betreuung EFZ, Fachrichtung Kinder“ and „Fachmann/-frau Betreuung (Kinder) EFZ“ give the same.
   * search_plan.profession_words in the app follows the same rules; profession_words.json holds the cases of both.
   * @param {string} name
   * @returns {Set<string>}
   */
  function professionWords(name) {
    const words = String(name || '').toLowerCase()
      .replace(/\/-?(in|frau|mann|euse|r)\b/g, '')
      .split(/[\s,;()/]+/)
      .filter((word) => word && !FILLER_WORDS.has(word))
      .map(neutralWord);
    return new Set(words.filter(Boolean));
  }

  /**
   * The option of a portal for a profession: it has all wanted words and as few others as possible, so the plain
   * profession wins over its specialisations. The first one wins a tie.
   * @template T
   * @param {string} wanted
   * @param {T[]} options
   * @param {(option: T) => string} labelOf
   * @returns {T|null}
   */
  function bestProfession(wanted, options, labelOf) {
    const words = professionWords(wanted);
    if (!words.size) return null;
    let best = null;
    let fewest = Infinity;
    for (const option of options) {
      const label = professionWords(labelOf(option));
      const extra = label.size - words.size;
      if (extra < fewest && [...words].every((word) => label.has(word))) {
        best = option;
        fewest = extra;
      }
    }
    return best;
  }

  const common = {
    PortalChanged, htmlToText, ageFromDate, ageFromText, workload, fetchJson, fetchPage, textOf, professionWords, bestProfession,
  };
  globalThis.bewerbungsassistentCommon = common;
  globalThis.bewerbungsassistentPortals = globalThis.bewerbungsassistentPortals || {};
  if (typeof module !== 'undefined') module.exports = common;
})();
