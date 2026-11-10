// Shared foundation of the dossier designs (docs/design/dossier.md). The data comes prepared from
// dossier.py as one JSON: cv, letter, pages, person and the read data extensions. Strings from the
// data are always inserted as text, never evaluated as markup.
#import "tokens.typ": palette, space, radius
#import "common.typ": beschriftungen-fuer

#let labels = (
  de: (
    kurz-vorgestellt: "Kurz vorgestellt",
    danke: "Danke",
    bewerbung: "Bewerbung",
    anschreiben: "Anschreiben",
    lebenslauf: "Lebenslauf",
  ),
  en: (
    kurz-vorgestellt: "A short introduction",
    danke: "Thank you",
    bewerbung: "Application",
    anschreiben: "Cover letter",
    lebenslauf: "Curriculum vitae",
  ),
)

#let default-accent = "#38495d"

// Colours for this dossier: the design-system palette with the chosen accent colour
#let colours-for(d) = palette(d.at("style", default: (:)).at("farbe-akzent", default: default-accent))

#let labels-for(d) = labels.at(d.language) + (cv: beschriftungen-fuer(d.cv, d.language))

// Wrapper for the whole file: only the wrapper sets metadata and the base text; parts set their pages
#let document-wrapper(d, title, body) = {
  set document(title: title, author: d.person.name)
  set text(font: "DM Sans", lang: d.language, number-type: "lining", number-width: "tabular")
  body
}

// A level graphic leaves a marker, so tests see which levels were drawn (none = empty dashed form)
#let level-marker(level) = [#metadata((level: level))<dossier-level>]

// A Lucide icon (stroke="currentColor") drawn in the given colour
#let icon(path, name, colour, size) = {
  let svg = read(path).replace("currentColor", colour.to-hex())
  [#metadata((icon: name))<dossier-icon>]
  image(bytes(svg), format: "svg", width: size, height: size)
}
