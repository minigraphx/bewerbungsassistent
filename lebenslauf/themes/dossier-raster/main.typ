// The CV of the design "Raster" alone, for portals that want separate uploads. Data from dossier.py.
#import "../dossier.typ": document-wrapper, labels-for
#import "theme.typ": cv-part
#let d = json(sys.inputs.at("data", default: "/build/dossier.json"))
#document-wrapper(d, labels-for(d).lebenslauf + " – " + d.person.name, cv-part(d, single: true))
