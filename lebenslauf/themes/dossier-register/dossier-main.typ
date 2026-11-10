// The dossier of the design "Register" as one PDF: cover with contents, letter, CV, optional Beilagen and
// Referenzen. The parts are the same functions as in the single files; this file only calls them in turn.
#import "../dossier.typ": document-wrapper, labels-for
#import "anschreiben.typ": letter-part
#import "theme.typ": cv-part
#import "teile.typ": cover, attachments-page, references-page
#let d = json(sys.inputs.at("data", default: "/build/dossier.json"))
#let title = (labels-for(d).bewerbung, d.letter.heading.position, d.letter.heading.company).filter(x => x != none)
#document-wrapper(d, title.join(" · ") + " – " + d.person.name, {
  cover(d)
  letter-part(d)
  cv-part(d)
  attachments-page(d)
  references-page(d)
})
