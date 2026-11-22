"use strict";
// The application's page, known jobs (G109, #385): an info notice below the head when the job came again with a new
// ad. The entry's own link and stelle.md stay as they were; the words come from wieder-logik.js.
(() => {
  const { el } = window.App;

  function zeige(bewerbung) {
    const notice = window.WiederLogik.applicationNotice(bewerbung);
    const box = document.getElementById("wieder-hinweis");
    box.hidden = !notice;
    if (!notice) return;
    document.getElementById("wieder-titel").textContent = notice.title;
    document.getElementById("wieder-text").replaceChildren(`${notice.text} `,
      el("a", { href: notice.link, target: "_blank", rel: "noopener" }, notice.linkText));
  }

  window.BewerbungWieder = { zeige };
})();
