// The dossier of the design "Siegel" as one PDF: cover, optional page before, letter, CV, optional page after.
// The parts are the same functions as in the single files; this file only calls them in turn.
#import "../dossier.typ": document-wrapper, labels-for
#import "anschreiben.typ": letter-part
#import "theme.typ": cv-part
#import "teile.typ": cover, greeting-page, thanks-page
#let d = json(sys.inputs.at("data", default: "/build/dossier.json"))
#let title = (labels-for(d).bewerbung, d.letter.heading.position, d.letter.heading.company).filter(x => x != none)
#document-wrapper(d, title.join(" · ") + " – " + d.person.name, {
  cover(d)
  greeting-page(d)
  letter-part(d)
  cv-part(d)
  thanks-page(d)
})
