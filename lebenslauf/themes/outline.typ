// One label drawn as glyph outlines: the SVG export of Typst has no text, so a design can show the label
// without text extraction reading it (tabs of the design Register). The colour is replaced when drawn.
#set page(width: auto, height: auto, margin: 0pt, fill: none)
#text(font: "DM Sans", size: 9pt, weight: 500, fill: rgb("#010203"))[#sys.inputs.at("label", default: "")]
