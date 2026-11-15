// Type area (G51, #304): every page leaves its own margins, so the check before sending measures text against the
// margins the design drew, not against a guess. Set as the page foreground, it runs once on every page and draws
// nothing. `footer` is the line below which the design prints in the bottom margin on purpose: its page footer, or
// a band at the foot of the page that carries text (`foot`, its height from the bottom edge); none without either.
#import "page-fill.typ": margin-of

#let length-of(value, base) = {
  if type(value) == relative { value.ratio * base + value.length } else if type(value) == ratio { value * base } else { value }
}

#let type-area(foot: none) = context {
  let m = page.margin
  let bottom = margin-of(m, "bottom")
  let has-footer = page.footer != none and (page.footer != auto or page.numbering != none)
  let lines = ()
  if has-footer { lines.push(page.height - bottom + length-of(page.footer-descent, bottom)) }
  if foot != none { lines.push(page.height - foot) }
  let footer = if lines == () { none } else { calc.min(..lines).pt() }
  [#metadata((page: here().page(), width: page.width.pt(), height: page.height.pt(),
    left: margin-of(m, "left").pt(), right: margin-of(m, "right").pt(), top: margin-of(m, "top").pt(),
    bottom: bottom.pt(), footer: footer))<type-area>]
}
