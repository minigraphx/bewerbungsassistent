// Anschreiben im Design des Themes "zweispaltig": Farben und Schriften wie im Lebenslauf.
#import "../brief.typ": brief
#import "theme.typ": standard-stil

#let anschreiben(daten, stil: (:)) = brief(daten, stil: (
  farbe-text: standard-stil.farbe-text,
  farbe-akzent: standard-stil.farbe-text,
  farbe-hintergrund: standard-stil.farbe-hintergrund,
  schrift-name: standard-stil.schrift-titel,
  schrift-text: standard-stil.schrift-text,
  groesse-name: 22pt,
  linie: 1.3pt,
  name-gross: true,
) + stil)
