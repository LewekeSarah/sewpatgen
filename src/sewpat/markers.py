"""SVG marker definitions used by the pattern renderer.

All markers use ``markerUnits="userSpaceOnUse"`` so dimensions stay in the
mm-based coordinate space of the drawing (Inkscape-compatible).

Public names:
    ARROW_DEFS: Complete ``<defs>`` SVG block to embed once per output file.
    SCISSOR_BLADE_OVERHANG: mm to shorten a segment endpoint when the scissor
        marker is active so the line terminates at the blade tips.
"""

_ARROW_FILL_COLOR = "grey"

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

_BLADE_TIP_X: float = round(13.0 - 9.0898857, 4)  # marker-space x ≈ 3.91
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

_MARKER_DOT = (
    '<marker id="dot" markerWidth="6" markerHeight="6" '
    'refX="3" refY="3" orient="auto" markerUnits="userSpaceOnUse">'
    '<circle cx="3" cy="3" r="2" fill="black" stroke="black" stroke-width="0.5" />'
    "</marker>"
)

_MARKER_STOP = (
    '<marker id="stop" markerWidth="4" markerHeight="12" '
    'refX="2" refY="6" orient="auto" markerUnits="userSpaceOnUse">'
    '<path d="M 2,0 L 2,12" fill="none" stroke="black" stroke-width="1.5" />'
    "</marker>"
)

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
