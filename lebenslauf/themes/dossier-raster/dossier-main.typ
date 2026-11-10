// The dossier of the design "Raster" as one PDF: cover, optional "Auf einen Blick", letter, CV, optional back page.
// The parts are the same functions as in the single files; this file only calls them in turn.
#import "../dossier.typ": document-wrapper, labels-for
#import "anschreiben.typ": letter-part
#import "theme.typ": cv-part
#import "teile.typ": cover, glance-page, back-page
#let d = json(sys.inputs.at("data", default: "/build/dossier.json"))
#let title = (labels-for(d).bewerbung, d.letter.heading.position, d.letter.heading.company).filter(x => x != none)
#document-wrapper(d, title.join(" · ") + " – " + d.person.name, {
  cover(d)
  glance-page(d)
  letter-part(d)
  cv-part(d)
  back-page(d)
})
