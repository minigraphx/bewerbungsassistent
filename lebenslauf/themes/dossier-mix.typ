// The dossier with a design per page (G39): cover, letter, CV and the optional pages each from the design chosen
// for them (`designs` in dossier.json). The parts are those of the designs; this file only picks and calls them.
// Colours and fonts come from dossier.typ for every design, so a mixed dossier keeps one accent colour and DM Sans.
#import "dossier.typ": document-wrapper, labels-for
#import "dossier-siegel/teile.typ" as siegel-pages
#import "dossier-siegel/anschreiben.typ" as siegel-letter
#import "dossier-siegel/theme.typ" as siegel-cv
#import "dossier-raster/teile.typ" as raster-pages
#import "dossier-raster/anschreiben.typ" as raster-letter
#import "dossier-raster/theme.typ" as raster-cv
#import "dossier-register/teile.typ" as register-pages
#import "dossier-register/anschreiben.typ" as register-letter
#import "dossier-register/theme.typ" as register-cv

// Per design: its parts, and its optional pages before the letter and after the CV
#let parts = (
  "dossier-siegel": (cover: siegel-pages.cover, letter: siegel-letter.letter-part, cv: siegel-cv.cv-part,
    before: (siegel-pages.greeting-page,), after: (siegel-pages.thanks-page,)),
  "dossier-raster": (cover: raster-pages.cover, letter: raster-letter.letter-part, cv: raster-cv.cv-part,
    before: (raster-pages.glance-page,), after: (raster-pages.back-page,)),
  "dossier-register": (cover: register-pages.cover, letter: register-letter.letter-part, cv: register-cv.cv-part,
    before: (), after: (register-pages.attachments-page, register-pages.references-page)),
)

// Which design drew a part, for tests; and where letter and CV begin, for a contents table of another design
#let drawn(part, design) = [#metadata((part: part, design: design))<dossier-design>]
#let start(part) = [#metadata((part: part))<dossier-part>]

#let d = json(sys.inputs.at("data", default: "/build/dossier.json"))
#let designs = d.designs
#let title = (labels-for(d).bewerbung, d.letter.heading.position, d.letter.heading.company).filter(x => x != none)
#document-wrapper(d, title.join(" · ") + " – " + d.person.name, {
  drawn("cover", designs.cover)
  (parts.at(designs.cover).cover)(d)
  drawn("pages", designs.pages)
  for optional in parts.at(designs.pages).before { optional(d) }
  drawn("letter", designs.letter)
  if designs.letter != "dossier-register" { start("anschreiben") }
  (parts.at(designs.letter).letter)(d)
  drawn("cv", designs.cv)
  if designs.cv != "dossier-register" { start("lebenslauf") }
  (parts.at(designs.cv).cv)(d)
  for optional in parts.at(designs.pages).after { optional(d) }
})
