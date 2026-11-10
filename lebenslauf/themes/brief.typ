// Gemeinsames Layout für Anschreiben. Die Themes setzen nur ihren Stil (Farben, Schriften, Grössen).
// Daten kommen fertig aufbereitet aus anschreiben.py; alle Texte werden als Text eingesetzt, nie als Markup.

#let brief-standard-stil = (
  farbe-text: black,
  farbe-akzent: black,
  farbe-hintergrund: white,
  schrift-name: "DM Sans",
  schrift-text: "DM Sans",
  groesse-name: 20pt,
  groesse-kontakt: 8.5pt,
  groesse-text: 10pt,
  zeilen-text: 0.62em,
  abstand-absatz: 0.85em,
  rand: (left: 2.5cm, right: 2cm, top: 1.5cm, bottom: 1.5cm),
  linie: none,             // z.B. 1.3pt: Linie unter dem Kopf
  name-gross: false,       // Name in Grossbuchstaben
  abstand-kopf: 1.1cm,
  abstand-empfaenger: 0.9cm,
  abstand-unterschrift: 1.6em,
)

// The letter as a part: sets only its own page style and no document metadata, so a dossier can
// put it between other parts (docs/design/dossier.md). `kopf` replaces name and contact line,
// `betreff-block` replaces the subject with a strong heading, `fuss` is the page footer.
#let brief-teil(daten, stil: (:), kopf: auto, betreff-block: none, fuss: none) = {
  let s = brief-standard-stil + stil
  let absender = daten.absender
  page(paper: "a4", margin: s.rand, fill: s.farbe-hintergrund, footer: fuss, {
    set text(font: s.schrift-text, size: s.groesse-text, fill: s.farbe-text, lang: daten.sprache)
    set par(leading: s.zeilen-text, spacing: s.abstand-absatz)

    // Kopf: Name und Kontaktzeile
    if kopf != auto { kopf } else { block(below: 0pt, {
      text(font: s.schrift-name, weight: 700, size: s.groesse-name, fill: s.farbe-akzent,
        if s.name-gross [#upper(absender.name)] else [#absender.name])
      v(0.3em)
      text(size: s.groesse-kontakt)[#absender.zeile]
      if s.linie != none {
        v(0.2em)
        line(length: 100%, stroke: s.linie + s.farbe-akzent)
      }
    }) }
    v(s.abstand-kopf)

    // Empfänger
    block(below: 0pt, {
      set par(spacing: 0pt)
      for zeile in daten.empfaenger [#zeile \ ]
    })
    v(s.abstand-empfaenger)

    [#daten.ort_datum]
    v(1.2em)
    if betreff-block != none { betreff-block } else { text(weight: 700)[#daten.betreff] }
    v(0.9em)
    [#daten.anrede]
    v(0.4em)
    for absatz in daten.absaetze [#absatz #parbreak()]
    // Gruss und Unterschrift nie getrennt
    block(breakable: false, above: 1.3em, {
      [#daten.gruss]
      v(s.abstand-unterschrift)
      [#daten.unterschrift]
    })
  })
}

#let brief(daten, stil: (:)) = {
  set document(title: daten.betreff, author: daten.absender.name)
  brief-teil(daten, stil: stil)
}
