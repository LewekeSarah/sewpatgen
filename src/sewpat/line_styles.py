from sewpat.style import StyleOptions, DEFAULT_STROKE_WIDTH_GRAIN


def get_grainline_style() -> StyleOptions:
    return StyleOptions(
        stroke_color="grey",
        stroke_width=DEFAULT_STROKE_WIDTH_GRAIN,
        arrow_start=True,
        dash_array=[3, 2],
    )


def get_fold_style() -> StyleOptions:
    return StyleOptions(
        dash_array=[7.0, 1.0, 1.0, 1.0],
        stroke_color="grey",
    )


def get_hem_style() -> StyleOptions:
    return StyleOptions(
        stroke_color="black",
    )


def get_seam_style() -> StyleOptions:
    return StyleOptions(dash_array=[5.0, 2.0])
