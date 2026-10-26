// Anschreiben im Design des Themes "einspaltig": schlicht, Akzentfarbe nur im Namen.
#import "../brief.typ": brief
#import "theme.typ": standard-stil

#let anschreiben(daten, stil: (:)) = brief(daten, stil: (
  farbe-akzent: standard-stil.farbe-akzent,
  schrift-name: standard-stil.schrift,
  schrift-text: standard-stil.schrift,
) + stil)
