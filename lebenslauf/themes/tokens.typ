// Values of the design system (docs/design/system/tokens.json, light theme), so theme and app stay alike.
// tests/test_dossier_siegel.py compares them with tokens.json; px of the app become pt on paper.

#let colours = (
  bg: rgb("#fdfcfa"),
  surface: rgb("#ffffff"),
  surface-subtle: rgb("#f4f2ee"),
  accent-subtle: rgb("#e8edf3"),
  line: rgb("#d9dde3"),
  line-strong: rgb("#7c8794"),
  text-strong: rgb("#27333f"),
  text: rgb("#38495d"),
  text-muted: rgb("#5a6879"),
  accent: rgb("#38495d"),
  on-accent: rgb("#ffffff"),
)

#let space = (
  space-1: 4pt,
  space-2: 8pt,
  space-3: 12pt,
  space-4: 16pt,
  space-5: 24pt,
  space-6: 32pt,
  space-7: 48pt,
)

#let radius = (
  radius-sm: 4pt,
  radius-md: 6pt,
  radius-lg: 10pt,
)

// WCAG relative luminance and contrast, to choose text on a chosen accent colour
#let luminance(c) = {
  let channel(v) = {
    let x = v / 100%
    if x <= 0.04045 { x / 12.92 } else { calc.pow((x + 0.055) / 1.055, 2.4) }
  }
  let (r, g, b, ..) = rgb(c).components()
  0.2126 * channel(r) + 0.7152 * channel(g) + 0.0722 * channel(b)
}

#let contrast(a, b) = {
  let (la, lb) = (luminance(a), luminance(b))
  (calc.max(la, lb) + 0.05) / (calc.min(la, lb) + 0.05)
}

// Text on accent areas: white or text-strong, whichever reads better; never fixed white
#let on-accent(accent) = {
  let light = colours.on-accent
  let dark = colours.text-strong
  if contrast(accent, light) >= contrast(accent, dark) { light } else { dark }
}

// The accent as text colour only with at least 4.5:1 on the paper
#let accent-text(accent) = if contrast(accent, colours.bg) >= 4.5 { accent } else { colours.text-strong }

#let accent-subtle(accent) = color.mix((rgb(accent), 12%), (white, 88%))

// The palette of a theme for one accent colour (stil.farbe-akzent)
#let palette(accent) = colours + (
  accent: rgb(accent),
  on-accent: on-accent(accent),
  accent-text: accent-text(accent),
  accent-subtle: if rgb(accent) == colours.accent { colours.accent-subtle } else { accent-subtle(accent) },
)
