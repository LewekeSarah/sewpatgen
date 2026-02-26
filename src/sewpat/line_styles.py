from sewpat.render import StyleOptions


def get_grainline_style() -> StyleOptions:
    return StyleOptions(
        stroke_color="grey",
        stroke_width=0.3,
        arrow_start=True,
        dash_array=[3, 2]
    )


def get_fold_style() -> StyleOptions:
    # Note that fold of fabric should always be parallel to grainline
    return StyleOptions(
        dash_array=[7.0, 1.0, 1.0, 1.0],
        stroke_color="grey",
        stroke_width=0.8,
    )

def get_hem_style() -> StyleOptions:
    # Note that fold of fabric should always be parallel to grainline
    return StyleOptions(
        stroke_color="black",
        stroke_width=3,
    )

def get_seam_style() -> StyleOptions:
    return StyleOptions(dash_array=[5.0, 2.0], stroke_width=1)

