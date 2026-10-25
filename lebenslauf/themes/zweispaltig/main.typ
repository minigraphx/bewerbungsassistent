#import "theme.typ": lebenslauf
#let cv = json(sys.inputs.at("data", default: "/build/cv.json"))
#lebenslauf(
  cv,
  sprache: sys.inputs.at("lang", default: "de"),
  stand: sys.inputs.at("stand", default: none),
)
