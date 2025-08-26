from sewpat.render import StyleOptions, LineEndStyle


def get_grainline_style() -> StyleOptions:
    return StyleOptions(
        stroke_color="grey",
        stroke_width=0.8,
        marker_end=LineEndStyle.arrow.name,
        font_size=9,
        text_anchor="middle",
    )


def get_fold_style() -> StyleOptions:
    # Note that fold of fabric should always be parallel to grainline
    return StyleOptions(
        dash_array=[7.0, 1.0, 1.0, 1.0],
        stroke_color="grey",
        stroke_width=0.8,
        font_size=9,
        text_anchor="middle",
    )

def get_hem_style() -> StyleOptions:
    # Note that fold of fabric should always be parallel to grainline
    return StyleOptions(
        stroke_color="black",
        stroke_width=3,
        font_size=9,
        text_anchor="middle",
    )

def get_seam_style() -> StyleOptions:
    return StyleOptions(dash_array=[5.0, 2.0], stroke_width=1, text_anchor="middle")