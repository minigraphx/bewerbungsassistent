// The cover letter of the design "Siegel" alone. Data from dossier.py.
#import "../dossier.typ": document-wrapper
#import "anschreiben.typ": letter-part
#let d = json(sys.inputs.at("data", default: "/build/dossier.json"))
#document-wrapper(d, d.letter.betreff, letter-part(d, single: true))
