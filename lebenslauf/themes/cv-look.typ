// Colour and mark of one CV (G77, #295), chosen in „Lebenslauf erstellen“. build.py writes them into cv.json as
// `x-aussehen` only for --akzent and --zeichen (cv_look.py); without them a CV keeps its design's colour and no mark.
// The mark is the dossier's (zeichen.typ), drawn small in the footer of every page.
#import "zeichen.typ": chosen-mark, fitting
#import "tokens.typ": palette

#let look-of(cv) = cv.at("x-aussehen", default: (:))

// The chosen accent colour, otherwise the design's own
#let accent-of(cv, own) = {
  let chosen = look-of(cv).at("akzent", default: none)
  if chosen == none { own } else { rgb(chosen) }
}

// Leaves the accent the CV is drawn in, for the tests
#let accent-marker(accent) = [#metadata(accent.to-hex())<cv-accent>]

// Whether the CV carries a mark at all
#let has-mark(cv) = look-of(cv).at("zeichen", default: none) != none

// The mark at `size`; a logo gets up to three times as much width
#let footer-mark(cv, accent, size) = {
  let m = look-of(cv).at("zeichen", default: none)
  if m != none and m.variant != fitting {
    let d = (person: (mark: (variant: m.variant, logo: m.logo), monogram: m.monogram))
    chosen-mark(d, palette(accent), size, size * 3, size, "cv-footer")
  }
}
