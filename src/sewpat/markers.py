"""
SVG marker definitions for sewing pattern rendering.

Each marker is defined in ``markerUnits="userSpaceOnUse"`` so sizes stay in
the same mm-based coordinate space as the rest of the drawing (Inkscape-safe).

Public names
------------
ARROW_DEFS              -- the complete ``<defs>`` SVG block to embed once per file.
SCISSOR_BLADE_OVERHANG  -- mm to shorten a segment endpoint when using the
                           scissor marker so the line terminates at the blade tips.
"""

# ---------------------------------------------------------------------------
# Arrow / grainline markers
# ---------------------------------------------------------------------------

# Colour used for the arrowhead fill (e.g. on grainlines).
_ARROW_FILL_COLOR = "grey"

# Right-pointing triangle: tip at (8,3), base at (0,0)-(0,6).
# refX=8 places the tip on the line endpoint.
# orient="auto-start-reverse" flips the marker 180° at marker-start so the
# tip still points outward (away from the line start).
_MARKER_ARROW_START = (
    '<marker id="arrow" markerWidth="8" markerHeight="6" '
    'refX="8" refY="3" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
    f'<path d="M0,0 L0,6 L8,3 Z" fill="{_ARROW_FILL_COLOR}" />'
    "</marker>"
)

_MARKER_ARROW_END = (
    '<marker id="arrow-end" markerWidth="8" markerHeight="6" '
    'refX="8" refY="3" orient="auto" markerUnits="userSpaceOnUse">'
    f'<path d="M0,0 L0,6 L8,3 Z" fill="{_ARROW_FILL_COLOR}" />'
    "</marker>"
)

# ---------------------------------------------------------------------------
# Scissor marker
# ---------------------------------------------------------------------------

# Inkscape "Scissors" stock path (U+2702 ✂), scaled and flipped.
#
# Transform pipeline (applied right-to-left by SVG):
#   1. scale(-1,1)  — flips horizontally so blade tips point left (into the line)
#                     and pivot rings face right (away from the line end).
#   2. translate(13,7) — shifts everything into the positive viewport.
#
# Key points in marker space after the transform (x_marker = 13 − x_path):
#   Blade tips   x_path ≈  9.09  →  x_marker ≈  3.91
#   Blade cross  x_path ≈  0.00  →  x_marker = 13.00
#   Pivot rings  x_path ≈ −12.61 →  x_marker ≈ 25.61
#
# refX=13, refY=7 places the blade crossing exactly on the segment endpoint.
# The segment is then shortened by SCISSOR_BLADE_OVERHANG (≈9.09 mm) so the
# visible line terminates at the blade tips rather than the crossing.
# With refX=13 the blade crossing sits at the segment endpoint.
# The blade tips are at x_marker ≈ 3.91, which is 9.09 mm back along the line.
# _render_segment shortens the segment by this amount so the visible line
# terminates at the blade tips rather than the crossing.
_BLADE_TIP_X: float = round(
    13.0 - 9.0898857, 4
)  # marker-space x of the blade tips ≈ 3.91
SCISSOR_BLADE_OVERHANG: float = round(13.0 - _BLADE_TIP_X, 4)  # ≈ 9.09 mm

_SCISSOR_PATH = (
    "M 9.0898857,-3.6061018 C 8.1198849,-4.7769976 6.3697607,-4.7358294 "
    "5.0623558,-4.2327734 L -3.1500488,-1.1548705 C -5.5383421,-2.4615840 "
    "-7.8983361,-2.0874077 -7.8983361,-2.7236578 C -7.8983361,-3.2209742 "
    "-7.4416699,-3.1119800 -7.5100293,-4.4068519 C -7.5756648,-5.6501286 "
    "-8.8736064,-6.5699315 -10.100428,-6.4884954 C -11.327699,-6.4958500 "
    "-12.599867,-5.5553341 -12.610769,-4.2584343 C -12.702194,-2.9520479 "
    "-11.603560,-1.7387447 -10.304005,-1.6532027 C -8.7816644,-1.4265411 "
    "-6.0857470,-2.3487593 -4.8210600,-0.082342643 C -5.7633447,1.6559151 "
    "-7.4350844,1.6607341 -8.9465707,1.5737277 C -10.201445,1.5014928 "
    "-11.708664,1.8611256 -12.307219,3.0945882 C -12.885586,4.2766744 "
    "-12.318421,5.9591904 -10.990470,6.3210002 C -9.6502788,6.8128279 "
    "-7.8098011,6.1912892 -7.4910978,4.6502760 C -7.2454393,3.4624530 "
    "-8.0864637,2.9043186 -7.7636052,2.4731223 C -7.5199917,2.1477623 "
    "-5.9728246,2.3362771 -3.2164999,1.0982979 L 5.6763468,4.2330688 C "
    "6.8000164,4.5467672 8.1730685,4.5362646 9.1684433,3.4313614 L "
    "-0.051640930,-0.053722219 L 9.0898857,-3.6061018 z "
    "M -9.2179159,-5.5066058 C -7.9233569,-4.7838060 -8.0290767,-2.8230356 "
    "-9.3743431,-2.4433169 C -10.590861,-2.0196559 -12.145370,-3.2022863 "
    "-11.757521,-4.5207817 C -11.530373,-5.6026336 -10.104134,-6.0014137 "
    "-9.2179159,-5.5066058 z "
    "M -9.1616516,2.5107591 C -7.8108215,3.0096239 -8.0402087,5.2951947 "
    "-9.4138723,5.6023681 C -10.324932,5.9187072 -11.627422,5.4635705 "
    "-11.719569,4.3902287 C -11.897178,3.0851737 -10.363484,1.9060805 "
    "-9.1616516,2.5107591 z"
)

_MARKER_SCISSOR = (
    '<marker id="scissor" markerWidth="26" markerHeight="14" '
    'refX="13" refY="7" orient="auto" markerUnits="userSpaceOnUse">'
    f'<path transform="translate(13,7) scale(-1,1)" style="marker-start:none" '
    f'fill="black" d="{_SCISSOR_PATH}" />'
    "</marker>"
)

# ---------------------------------------------------------------------------
# Distance / dimension markers
# ---------------------------------------------------------------------------

# Arrowhead with a perpendicular stop-bar at the tip, as used in technical
# drawing for dimension/measurement annotations.
# auto-start-reverse on the start variant makes it point outward at p1.
_MARKER_DISTANCE_START = (
    '<marker id="distance-start" markerWidth="15" markerHeight="10" '
    'refX="0" refY="5" orient="auto-start-reverse" markerUnits="userSpaceOnUse">'
    '<path d="M 13,4 L 0,5 L 13,6" fill="none" stroke="black" stroke-width="1" />'
    '<path d="M 0,1 L 0,9" fill="none" stroke="black" stroke-width="1" />'
    "</marker>"
)

_MARKER_DISTANCE_END = (
    '<marker id="distance-end" markerWidth="15" markerHeight="10" '
    'refX="13" refY="5" orient="auto" markerUnits="userSpaceOnUse">'
    '<path d="M 0,4 L 13,5 L 0,6" fill="none" stroke="black" stroke-width="1" />'
    '<path d="M 13,1 L 13,9" fill="none" stroke="black" stroke-width="1" />'
    "</marker>"
)

# ---------------------------------------------------------------------------
# Dot marker
# ---------------------------------------------------------------------------

# Small filled circle — useful for button positions or match points.
_MARKER_DOT = (
    '<marker id="dot" markerWidth="6" markerHeight="6" '
    'refX="3" refY="3" orient="auto" markerUnits="userSpaceOnUse">'
    '<circle cx="3" cy="3" r="2" fill="black" stroke="black" stroke-width="0.5" />'
    "</marker>"
)

# ---------------------------------------------------------------------------
# Stop marker
# ---------------------------------------------------------------------------

# Short perpendicular bar — useful for hem lines or dart ends.
_MARKER_STOP = (
    '<marker id="stop" markerWidth="4" markerHeight="12" '
    'refX="2" refY="6" orient="auto" markerUnits="userSpaceOnUse">'
    '<path d="M 2,0 L 2,12" fill="none" stroke="black" stroke-width="1.5" />'
    "</marker>"
)

# ---------------------------------------------------------------------------
# Combined <defs> block
# ---------------------------------------------------------------------------

ARROW_DEFS: str = (
    "<defs>"
    + _MARKER_ARROW_START
    + _MARKER_ARROW_END
    + _MARKER_SCISSOR
    + _MARKER_DISTANCE_START
    + _MARKER_DISTANCE_END
    + _MARKER_DOT
    + _MARKER_STOP
    + "</defs>"
)
