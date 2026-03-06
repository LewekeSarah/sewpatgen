from pathlib import Path

from sewpat import (
    STYLE_HEM,
    STYLE_STITCH,
    STYLE_WAISTBAND,
    ConstructionGrid,
    Pattern,
    PatternPart,
    Segment,
)
from sewpat.geometry import (
    Circle,
    CubicBezier,
    Point,
    Ray,
    intersect,
)
from sewpat.measurements import (
    TrouserEase,
    TrouserConfig,
    TrouserMeasurements,
    make_measurements_trouser,
)
from sewpat.pages import DinA1
from sewpat.person import Gender, Person
from sewpat.render import export_pattern_svg_mm
from sewpat.style import StyleOptions
from sewpat.units import CM


def make_person() -> Person:
    henri = Person(
        height=116 * CM,
        bust=63 * CM,
        waist=62.5 * CM,
        hip=71 * CM,
        body_rise=19.6 * CM,  ## 18.5 * CM,
        inseam=51.5 * CM,
        gender=Gender.boy,
    )  # gemessen 2025-09-15
    # return Person(
    #     height=122 * CM,
    #     bust=63 * CM,
    #     waist=60 * CM,
    #     hip=67 * CM,
    #     hip_depth=0 * CM,
    #     bust_depth=15.6 * CM,
    #     back_length=29.2 * CM,
    #     body_rise=20.4 * CM,  # body_rise / Sitzhöhe
    #     inseam=55 * CM,       # inseam / Schritthöhe
    #     gender=Gender.boy,
    # )
    return henri


def make_ease() -> TrouserEase:
    return TrouserEase(
        body_rise_ease=3 * CM,   # baby 4.5 * CM,
        inseam_ease=-3 * CM,     # baby -2 * CM,
        hip_ease=5.5 * CM,       # baby 4 * CM,
    )


def make_config() -> TrouserConfig:
    return TrouserConfig(
        length=48.75 * CM,
        front_trouser_ease=0.5 * CM,
        hem_width=14 * CM,  # baby 1 * CM  # 35/2
    )


def boy_shorts(meas: TrouserMeasurements, model: TrouserConfig) -> Pattern:
    pattern_boy_trousers = Pattern(
        name="Flat Boy Trousers", anchor=Point(5 * CM, 7 * CM)
    )
    pt0 = pattern_boy_trousers.anchor

    # -----------------------------------------------------------------------
    # KONSTRUKTIONSGITTER — zuerst erstellen, dann daraus konstruieren
    # -----------------------------------------------------------------------
    # Front grid: anchor = pt0 (Hintermitte / Taillenlinie)
    grid = ConstructionGrid(
        anchor=pt0,
        verticals=[
            ("Hintermitte", 0),
            ("Vorderhosenbreite", meas.front_trouser_width),
        ],
        horizontals=[
            ("Taillenlinie", 0),
            ("Sitzhöhe", meas.body_rise),
            ("Knielinie", meas.body_rise + meas.knee_height),
            ("Saumlinie", meas.body_rise + meas.inseam),
            ("Modellänge", model.length),
        ],
    ).build()

    # Named grid lines — looked up once and reused throughout construction
    g_hm = grid.get_element("Hintermitte").geometry
    g_vhb = grid.get_element("Vorderhosenbreite").geometry
    g_tai = grid.get_element("Taillenlinie").geometry
    g_sih = grid.get_element("Sitzhöhe").geometry
    g_kni = grid.get_element("Knielinie").geometry
    g_sau = grid.get_element("Saumlinie").geometry
    g_mol = grid.get_element("Modellänge").geometry

    # Base construction points derived directly from grid intersections
    pt0 = intersect(g_hm, g_tai)[0]  # Hintermitte  × Taillenlinie  (= anchor)
    pt1 = intersect(g_hm, g_sih)[0]  # Hintermitte  × Sitzhöhe
    pt2 = intersect(g_hm, g_sau)[0]  # Hintermitte  × Saumlinie
    pt3 = intersect(g_hm, g_kni)[0]  # Hintermitte  × Knielinie
    pt4 = intersect(g_vhb, g_sih)[0]  # Vorderbreite × Sitzhöhe
    pt5 = intersect(g_vhb, g_tai)[0]  # Vorderbreite × Taillenlinie

    # Back grid: same measurements, anchor shifted right of the front piece
    back_pt0 = pt5.translate(10 * CM, 0)
    back_grid = ConstructionGrid(
        anchor=back_pt0,
        verticals=[
            ("Hintermitte", 0),
            ("Vorderhosenbreite", meas.front_trouser_width),
        ],
        horizontals=[
            ("Taillenlinie", 0),
            ("Sitzhöhe", meas.body_rise),
            ("Knielinie", meas.body_rise + meas.knee_height),
            ("Saumlinie", meas.body_rise + meas.inseam),
            ("Modellänge", model.length),
        ],
    ).build()

    bg_hm = back_grid.get_element("Hintermitte").geometry
    bg_vhb = back_grid.get_element("Vorderhosenbreite").geometry
    bg_sih = back_grid.get_element("Sitzhöhe").geometry
    bg_kni = back_grid.get_element("Knielinie").geometry
    bg_mol = back_grid.get_element("Modellänge").geometry

    back_pt1 = intersect(bg_hm, bg_sih)[0]  # Hintermitte  × Sitzhöhe
    back_pt4 = intersect(bg_vhb, bg_sih)[0]  # Vorderbreite × Sitzhöhe

    # Grids are not added to the pattern — pass them explicitly to the renderer
    # when you want to see them (see export calls below).
    pattern_boy_trousers.add_part(grid)
    pattern_boy_trousers.add_part(back_grid)

    # -----------------------------------------------------------------------
    # VORDERTEIL
    # -----------------------------------------------------------------------
    front = PatternPart(name="Vorderteil")
    pattern_boy_trousers.add_part(front)

    # Leg-grid midpoints (not on grid lines, keep as computed)
    pt9 = Point(pt0.x + 0.5 * meas.front_trouser_width, pt1.y)  # grain centre at body_rise
    pt10 = Point(pt0.x + 0.5 * meas.front_trouser_width, pt3.y)  # grain centre at knee_height
    pt11 = Point(pt0.x + 0.5 * meas.front_trouser_width, pt2.y)  # grain centre at inseam
    pt12 = Point(pt11.x - (model.hem_width / 2 + 0.5 * CM), pt11.y)  # side hem
    pt13 = Point(pt11.x + (model.hem_width / 2 + 0.5 * CM), pt11.y)  # inner hem

    # Bund
    pt6 = pt5.translate(-1 * CM, 0)

    # Hosenausschnitt
    pt7 = pt4.translate(0, -0.25 * meas.body_rise)
    pt8 = pt4.translate((0.25 * meas.front_trouser_width - model.front_trouser_ease), 0)
    bz_control2 = Segment(pt7, pt8).point_perpendicular(0.5 * CM, t=0.75)
    bz_control3 = pt7.translate(0.2 * CM, 2.5 * CM)

    front.append(Segment(pt6, pt0, name="Bund"), style=STYLE_WAISTBAND, is_outline=True)
    front_size_top = front.append(
        Segment(pt0, pt1), style=STYLE_STITCH, is_outline=True
    )

    # Seitennaht & Innennaht
    side = Segment(pt1, pt12)
    pt14 = intersect(side, g_kni)[0]  # Seitennaht × Knielinie (grid reuse)
    pt15 = Point(pt10.x + (pt10.x - pt14.x), pt10.y)
    front_seam_aux = Segment(pt8, pt15)
    bz_control = front_seam_aux.point_perpendicular(1.6 * CM, t=0.5)
    inner_seam = Segment(pt13, pt15)

    # Modellänge — intersect with the Modellänge grid line directly
    pt32 = intersect(g_mol, inner_seam)[0]  # grid reuse
    pt33 = intersect(g_mol, side)[0]  # grid reuse

    # Outline
    front_side_upper = front.append(
        Segment(pt1, pt14), style=STYLE_STITCH, is_outline=True
    )
    front_side_lower = front.append(
        Segment(pt14, pt33), style=STYLE_STITCH, is_outline=True
    )
    front.append(Segment(pt33, pt32), style=STYLE_HEM, is_outline=True)
    front.append(Segment(pt32, pt15), style=STYLE_STITCH, is_outline=True)
    front_inner_leg = front.append(
        CubicBezier(pt8, bz_control, pt15.translate(0.1 * CM, -2 * CM), pt15),
        style=STYLE_STITCH,
        is_outline=True,
    )
    front_curve = front.append(
        CubicBezier(pt7, bz_control3, bz_control2, pt8),
        style=STYLE_STITCH,
        is_outline=True,
    )
    front.append(Segment(pt6, pt7), style=STYLE_STITCH, is_outline=True)

    grain_end = intersect(Segment(pt9, pt11), g_mol)
    front.add_grainline(start=pt9, end=grain_end[0])
    front.add_info_box(
        notes=[
            f"Modellänge {model.length / CM:.1f} cm",
            f"Sitzhöhe {meas.body_rise / CM:.1f} cm",
            "1× Stoff (gegengleich)",
        ]
    )
    front.add_seam_allowance(model.seam_allowance)

    # -----------------------------------------------------------------------
    # RÜCKTEIL
    # -----------------------------------------------------------------------
    back = PatternPart(name="Rückteil")
    pattern_boy_trousers.add_part(back)

    # Leg-grid midpoints for back
    back_pt9 = Point(back_pt0.x + 0.5 * meas.front_trouser_width, back_pt1.y)
    back_pt10 = Point(back_pt0.x + 0.5 * meas.front_trouser_width, intersect(bg_hm, bg_kni)[0].y)
    back_pt11 = Point(back_pt0.x + 0.5 * meas.front_trouser_width, intersect(bg_hm, bg_mol)[0].y)
    back_pt12 = Point(back_pt11.x - (model.hem_width / 2 + 0.5 * CM), back_pt11.y)
    back_pt13 = Point(back_pt11.x + (model.hem_width / 2 + 0.5 * CM), back_pt11.y)

    # Hosenbund
    back_pt6 = intersect(bg_vhb, back_grid.get_element("Taillenlinie").geometry)[0]
    pt16 = back_pt6.translate(-3.5 * CM, 0)
    pt17 = pt16.translate(0, -3 * CM)
    pt18 = back_pt0.translate(-2 * CM, 0)

    # Hinternaht
    pt19 = back_pt4.translate(0, -0.5 * meas.body_rise)
    pt20 = back_pt4.translate(
        (2 * (pt8.x - intersect(g_vhb, g_sih)[0].x) + 0.5 * CM), 0
    )
    pt21 = pt20.translate(0, 1 * CM)
    bz_contol4 = back_pt4.translate(3.05 * CM, -3.05 * CM)

    # Seitennähte / Innenbeinnähte
    pt22 = back_pt12.translate(-1 * CM, 0)
    side_back = Segment(pt18, pt22)
    pt23 = intersect(side_back, bg_kni)[0]  # grid reuse
    pt24 = back_pt13.translate(1 * CM, 0)
    back_shift = back_pt0.x - intersect(g_hm, g_tai)[0].x
    back_pt14 = pt14.translate(back_shift, 0)
    pt25 = pt15.translate(back_shift + (pt23.x - back_pt14.x), 0)
    back_aux = Segment(pt21, pt25)
    bz_control5 = back_aux.point_perpendicular(2.5 * CM, t=0.5)
    back_inner_seam_geom = Segment(pt24, pt25)

    # Modellänge Rückteil — reuse back Modellänge grid line
    pt30 = intersect(bg_mol, back_inner_seam_geom)[0]  # grid reuse
    pt31 = intersect(bg_mol, side_back)[0]  # grid reuse

    # Outline
    back.append(Segment(pt17, pt19), style=STYLE_STITCH, is_outline=True)
    back.append(
        CubicBezier(pt19, bz_contol4, bz_contol4, pt21),
        style=STYLE_STITCH,
        is_outline=True,
    )
    back_inner_seam = back.append(
        CubicBezier(pt21, bz_control5, pt25.translate(0.1 * CM, -2 * CM), pt25),
        style=STYLE_STITCH,
        is_outline=True,
    )
    back.append(Segment(pt25, pt30), style=STYLE_STITCH, is_outline=True)
    back.append(Segment(pt30, pt31), style=STYLE_HEM, is_outline=True)
    back_side_seam = back.append(
        Segment(pt18, pt31), style=STYLE_STITCH, is_outline=True
    )
    back.append(Segment(pt17, pt18), style=STYLE_WAISTBAND, is_outline=True)

    grain_end_back = intersect(Segment(back_pt9, back_pt11), bg_mol)
    back.add_grainline(start=back_pt9, end=grain_end_back[0])
    back.add_info_box(
        notes=[
            f"Modellänge {model.length / CM:.1f} cm",
            f"Sitzhöhe {meas.body_rise / CM:.1f} cm",
            "1× Stoff (gegengleich)",
        ]
    )
    back.add_seam_allowance(model.seam_allowance)

    # -----------------------------------------------------------------------
    # Nahtlängen-Kontrolle
    # -----------------------------------------------------------------------
    front_side_len = front.seam_length(
        [front_size_top, front_side_upper, front_side_lower]
    )
    back_side_len = back.seam_length([back_side_seam])
    diff_side = back_side_len - front_side_len
    print(
        f"Seitennaht  Vorderteil: {front_side_len / CM:.1f} cm  |  "
        f"Rückteil: {back_side_len / CM:.1f} cm  |  "
        f"Δ = {diff_side / CM:+.1f} cm"
    )

    # Automated grid notches (after manual ones so dedup sees them)
    front.add_grid_notches(grid)
    back.add_grid_notches(back_grid, is_back=True)

    # -----------------------------------------------------------------------
    # KONSTRUKTION (Hilfsgeometrie)
    # -----------------------------------------------------------------------
    aux = PatternPart(name="Konstruktion")
    pattern_boy_trousers.add_part(aux)

    _dash = StyleOptions(dash_array=[3, 2], stroke_color="lightgrey")
    _dash_red = StyleOptions(dash_array=[3, 2], stroke_color="red")

    aux.append(Segment(pt0, pt1, name="Grundgerüst: Taillenlinie"), style=_dash)
    aux.append(Segment(pt0, pt6, name="Grundgerüst: Bundlinie"), style=_dash)
    aux.append(Circle(pt4, 2.5 * CM), style=_dash)
    aux.append(Ray(pt2, (pt10.x, 0), name="Saumlinie"), style=_dash)
    aux.append(Segment(pt12, pt13), style=_dash)
    aux.append(side, style=_dash)
    aux.append(inner_seam, style=_dash)
    aux.append(front_seam_aux, style=StyleOptions(dash_array=[3, 2]))
    aux.append(Segment(back_pt9, back_pt11), style=_dash)
    aux.append(Circle(back_pt4, 4.5 * CM), style=_dash)
    aux.append(back_aux, style=_dash)
    aux.append(side_back, style=_dash)
    aux.append(back_inner_seam, style=_dash_red)
    aux.append(Segment(pt22, pt24), style=_dash)

    # -----------------------------------------------------------------------
    # Referenzquadrat
    # -----------------------------------------------------------------------
    pattern_boy_trousers.add_reference_square(
        origin=front.centroid.translate(-5 * CM, -17 * CM)
    )

    return pattern_boy_trousers


# base_grid_trouser and get_leg_grid have been inlined into boy_trousers
# using grid intersections directly and are no longer needed.


if __name__ == "__main__":
    DEBUG = True
    person = make_person()
    ease = make_ease()
    measurements = make_measurements_trouser(person, ease)
    model_config = make_config()
    pattern = boy_shorts(measurements, model_config)

    parts = ["Vorderteil", "Rückteil"]
    if DEBUG:
        parts += ["Konstruktionsgitter"]  # , "Konstruktion"

    # Without seam allowance
    export_pattern_svg_mm(
        pattern,
        filename=str(
            Path(__file__).parent / f"boys_shorts{'_grid' if DEBUG else ''}.svg"
        ),
        height_mm=DinA1.width,
        width_mm=DinA1.height,
        parts=parts,
        show_seam_allowance=False,
    )

    # With seam allowance
    export_pattern_svg_mm(
        pattern,
        filename=str(
            Path(__file__).parent / f"boys_shorts_sa{'_grid' if DEBUG else ''}.svg"
        ),
        height_mm=DinA1.width,
        width_mm=DinA1.height,
        parts=parts,
        show_seam_allowance=True,
    )
