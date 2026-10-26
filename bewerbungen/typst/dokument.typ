// Markdown-Dateien als PDF (textdokument.py). Die Struktur kommt als JSON; alle Texte werden als Text
// eingesetzt (#knoten.text), nie als Markup.

#let daten = json(sys.inputs.data)
#let grau = rgb("#6b7a8c")

#set document(title: daten.titel)
#set page(paper: "a4", margin: (x: 2.2cm, y: 2cm),
  header: context if counter(page).get().first() > 1 { text(size: 8pt, fill: grau)[#daten.titel] },
  footer: context align(right, text(size: 8pt, fill: grau)[#counter(page).display()]))
#set text(font: "DM Sans", size: 10.5pt, fill: rgb("#38495d"), lang: "de")
#set par(leading: 0.65em, spacing: 1em)
#set heading(numbering: none)
#show heading: set text(weight: 700)
#show heading.where(level: 1): set text(size: 18pt)
#show heading.where(level: 2): set text(size: 13.5pt)
#show heading.where(level: 3): set text(size: 11.5pt)
#show raw: set text(size: 9pt)
#show link: set text(fill: rgb("#1f5fa8"))

#let knoten(n) = {
  let inhalt = n.at("k", default: ()).map(knoten).sum(default: [])
  let t = n.t
  if t == "text" [#n.text]
  else if t == "softbreak" [ ]
  else if t == "hardbreak" { linebreak() }
  else if t == "strong" { strong(inhalt) }
  else if t == "em" { emph(inhalt) }
  else if t == "s" { strike(inhalt) }
  else if t == "code_inline" { raw(n.text) }
  else if t == "link" { if n.href == none { inhalt } else { link(n.href, inhalt) } }
  else if t == "image" [\[Bild: #inhalt\]]
  else if t == "heading" { heading(level: calc.min(n.stufe, 6), inhalt) }
  else if t == "paragraph" { block(inhalt) }
  else if t == "bullet_list" { list(..n.k.map(knoten)) }
  else if t == "ordered_list" { enum(start: n.start, ..n.k.map(knoten)) }
  else if t == "list_item" { inhalt }
  else if t == "blockquote" { block(inset: (left: 10pt), stroke: (left: 2pt + grau), inhalt) }
  else if t in ("fence", "code_block") {
    block(fill: luma(245), inset: 8pt, radius: 3pt, width: 100%, raw(n.text, block: true))
  }
  else if t == "hr" { line(length: 100%, stroke: 0.5pt + grau) }
  else if t == "table" {
    let zelle(teile) = teile.map(knoten).sum(default: [])
    table(
      columns: n.spalten,
      stroke: 0.5pt + luma(200),
      inset: 6pt,
      ..n.kopf.map(z => strong(zelle(z))),
      ..n.zeilen.map(zeile => zeile.map(zelle)).flatten(),
    )
  }
  else { inhalt }
}

#text(size: 8pt, fill: grau)[#daten.titel]
#v(0.4em)
#for b in daten.bloecke { knoten(b) }
