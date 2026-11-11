// Page fill (G49, G50, #236): no nearly empty last page. The build (page_fill.py) picks a density level per part
// from sys.inputs ("density-cv", "density-letter"): 0 is the design as drawn, a positive level tightens spacing,
// leading and the body size (never below 9 pt, never above the design's own size), a negative level widens the
// spacing between blocks so content flows onto the last page. The parts leave markers so the build can measure.

#let density(part) = int(sys.inputs.at("density-" + part, default: "0"))

// Spacing between blocks, headings and entries: 0.92 … 0.60 tighter, 1.12 … 1.60 wider
#let spacing(part) = {
  let level = density(part)
  if level >= 0 { 1 - 0.08 * level } else { 1 - 0.12 * level }
}

// Leading only tightens; wider lines would look loose rather than calm
#let leading(part) = 1 - 0.04 * calc.max(density(part), 0)

// Body text a little smaller when tightening, never below 9 pt or below the design's own size
#let body-size(size, part) = {
  let level = density(part)
  if level <= 0 { size } else { calc.max(size - 0.12pt * level, calc.min(size, 9pt)) }
}

#let margin-of(m, side) = {
  let value = if type(m) == dictionary { m.at(side) } else { m }
  if value == auto { 2.5cm } else if type(value) == relative { value.length } else { value }
}

// Where a part begins: its first page
#let part-start(part) = context [#metadata((part: part, edge: "start", page: here().page()))<page-fill>]

// Where a part's content ends, with the page's content area; a part with columns leaves one per column
#let part-end(part) = context {
  let m = page.margin
  [#metadata((part: part, edge: "end", page: here().page(), y: here().position().y.pt(),
    top: margin-of(m, "top").pt(), bottom: margin-of(m, "bottom").pt(), height: page.height.pt()))<page-fill>]
}
