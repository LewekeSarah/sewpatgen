"""Tests for style.py — StyleOptions.__eq__, __repr__, as_dict."""

from sewpat.style import STYLE_STITCH, StyleOptions

# ---------------------------------------------------------------------------
# StyleOptions.__eq__
# ---------------------------------------------------------------------------


def test_style_options_eq_same_defaults():
    """Two default StyleOptions instances are equal."""
    assert StyleOptions() == StyleOptions()


def test_style_options_eq_same_values():
    """Two instances with the same non-default values are equal."""
    a = StyleOptions(stroke_color="red", stroke_width=2.0)
    b = StyleOptions(stroke_color="red", stroke_width=2.0)
    assert a == b


def test_style_options_eq_different_values():
    """Instances with different values are not equal."""
    assert StyleOptions(stroke_color="red") != StyleOptions(stroke_color="blue")


def test_style_options_eq_non_style_returns_not_implemented():
    """Comparing with a non-StyleOptions object returns NotImplemented (line 105)."""
    result = StyleOptions().__eq__("not a style")
    assert result is NotImplemented


def test_style_options_eq_non_style_via_operator():
    """Using != against a non-StyleOptions object does not raise."""
    assert StyleOptions() != "not a style"


# ---------------------------------------------------------------------------
# StyleOptions.__repr__  (lines 110-115)
# ---------------------------------------------------------------------------


def test_style_options_repr_default_is_empty():
    """Default StyleOptions repr shows no attributes."""
    r = repr(StyleOptions())
    assert r == "StyleOptions()"


def test_style_options_repr_shows_non_default_fields():
    """Non-default fields appear in repr."""
    s = StyleOptions(stroke_color="red")
    r = repr(s)
    assert "stroke_color='red'" in r


def test_style_options_repr_multiple_non_default_fields():
    """Multiple non-default fields all appear in repr."""
    s = StyleOptions(stroke_color="blue", stroke_width=3.0, fill_color="green")
    r = repr(s)
    assert "stroke_color='blue'" in r
    assert "stroke_width=3.0" in r
    assert "fill_color='green'" in r


def test_style_options_repr_only_changed_fields():
    """Fields that match the default are omitted from repr."""
    s = StyleOptions(stroke_color="red")  # only stroke_color differs
    r = repr(s)
    assert "stroke_width" not in r


def test_named_presets_have_stable_repr():
    """Named style presets have a non-empty repr (regression guard)."""
    r = repr(STYLE_STITCH)
    assert r.startswith("StyleOptions(")
    assert len(r) > len("StyleOptions()")


# ---------------------------------------------------------------------------
# StyleOptions.as_dict
# ---------------------------------------------------------------------------


def test_style_options_as_dict_contains_stroke():
    """as_dict() always includes a 'stroke' key."""
    d = StyleOptions().as_dict()
    assert "stroke" in d


def test_style_options_as_dict_dash_array_included_when_set():
    """as_dict() includes stroke-dasharray when dash_array is set."""
    s = StyleOptions(dash_array=[5, 3])
    d = s.as_dict()
    assert "stroke-dasharray" in d
    assert d["stroke-dasharray"] == "5,3"


def test_style_options_as_dict_no_dash_array_key_when_not_set():
    """as_dict() omits stroke-dasharray when dash_array is None."""
    d = StyleOptions().as_dict()
    assert "stroke-dasharray" not in d
