from sewpat.render import StyleOptions, LineEndStyle


def get_grainline_style() -> StyleOptions:
    return StyleOptions(stroke_color="grey", stroke_width=0.8, marker_end=LineEndStyle.arrow.name)


def get_fold_style() -> StyleOptions:
    return StyleOptions(dash_array=[5.0, 2.0], stroke_color="grey", stroke_width=0.8)