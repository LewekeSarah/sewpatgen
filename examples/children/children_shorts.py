from sewpat import Segment, PatternPart, Pattern
from sewpat.geometry import (
    Point,
    intersect,
    Ray,
    Circle,
    CubicBezier,
)
from sewpat.units import CM
from sewpat.measurments import (
    ModelConfig,
    Allowance,
    make_measurements_trouser,
    TrouserMeasurements,
)
from sewpat.pages import DinA1
from sewpat.person import Gender, Person
from sewpat.render import export_pattern_svg_mm
from sewpat.style import StyleOptions


def make_person() -> Person:
    henri = Person(
        KöH=116 * CM,
        BrU=63 * CM,
        TaU=62.5 * CM,
        HüU=71 * CM,
        SiH=19.6 * CM,  ## 18.5 * CM,
        SrH=51.5 * CM,
        gender=Gender.boy,
    )  # gemessen 2025-09-15
    # return Person(
    #     KöH=122 * CM,
    #     BrU=63 * CM,
    #     TaU=60 * CM,
    #     HüU=67 * CM,
    #     HüT=0 * CM,
    #     BrT=15.6 * CM,
    #     RüL=29.2 * CM,
    #     SiH=20.4 * CM,  # SiH = body_rise / Sitzhöhe
    #     SrH=55 * CM,  # SrH = inside leg / Schritthöhe
    #     gender=Gender.boy,
    # )
    return henri


def make_allowance() -> Allowance:
    return Allowance(
        SiH=3 * CM,  # baby 4.5 * CM,
        SrH=-3 * CM,  # baby-2 * CM,
        HüU=5.5 * CM,  # baby 4 * CM,
    )


def make_model_config() -> ModelConfig:
    return ModelConfig(
        MoL=48.75 * CM, ZuvHoB=0.5 * CM, SaW=14 * CM  # baby 1 * CM  # 35/2
    )


def boy_trousers(meas: TrouserMeasurements, model: ModelConfig) -> Pattern:
    pattern_boy_trousers = Pattern(name="Flat Boy Trousers", anchor=Point(5 * CM, 5 * CM))
    pt0 = pattern_boy_trousers.anchor

    # -----------------------------------------------------------------------
    # Gemeinsame Hilfsgrößen (Modellänge / Saum-Hilfslinie)
    # -----------------------------------------------------------------------
    seam = Ray(pt0.translate(0, model.MoL), (1, 0))

    # -----------------------------------------------------------------------
    # VORDERTEIL
    # -----------------------------------------------------------------------
    front = PatternPart(name="Vorderteil")
    pattern_boy_trousers.add_part(front)

    # STEP 1: Grundgerüst Vorderteil (Konstruktionspunkte)
    pt1, pt2, pt3, pt4, pt5, pt6 = base_grid_trouser(meas, pt0, anchor_left=True)

    # STEP 2: Hosenausschnitt
    pt7 = pt4.translate(0, -0.25 * meas.SiH)
    pt8 = pt4.translate((0.25 * meas.vHoB - model.ZuvHoB), 0)  # von links
    bz_control2 = Segment(pt7, pt8).point_perpendicular(0.5 * CM, rel_pos_on_obj=0.75)
    bz_control3 = pt7.translate(0.2 * CM, 2.5 * CM)
    front.append(CubicBezier(pt6, pt6, pt7, pt7))
    front.append(CubicBezier(pt7, bz_control3, bz_control2, pt8))
    # Hilfsgeometrie Hosenausschnitt

    front.append(pt7)
    front.append(Segment(pt6, pt0, name="Bund"))
    front.append(Segment(pt0, pt1))

    # STEP 3: Hosenbeingitter
    pt9, pt10, pt11, pt12, pt13 = get_leg_grid(meas, model, pt0, anchor_left=True)
    knee = Ray(pt3, (pt10.x, 0), name="Knielinie")

    # STEP 4: Seitennaht & Innennaht
    side = CubicBezier(pt1, pt1, pt12, pt12)
    pt14 = intersect(side, knee)[0]
    pt15 = pt10.translate(pt10.x - pt14.x, 0)
    front_seam_aux = Segment(pt8, pt15)
    bz_control = front_seam_aux.point_perpendicular(1.6 * CM, rel_pos_on_obj=0.5)
    inner_seam = Segment(pt13, pt15)

    front.append(Point(pt14.x, pt14.y, "pt14"))
    front.append(CubicBezier(pt1, pt1, pt14, pt14))
    front.append(front_seam_aux.point_perpendicular(0.8 * CM, rel_pos_on_obj=0.5))
    front.append(CubicBezier(pt8, bz_control, pt15.translate(0.1 * CM, -2 * CM), pt15))

    # STEP 9a: Modellänge Vorderteil
    pt32 = intersect(seam, inner_seam)[0]
    pt33 = intersect(seam, side)[0]
    front.append(Segment(pt14, pt33))
    front.append(Segment(pt32, pt15))
    front.append(Segment(pt32, pt33))

    # Fadenlauf Vorderteil
    grain_end = intersect(Segment(pt9, pt11), seam)
    front.add_grainline(start=pt9, end=grain_end[0])

    # Kerben
    front.add_notches(pt14, segment=Segment(pt14, pt33))  # Seitennaht am Knie
    front.add_notches(pt15, segment=inner_seam)  # Innenbeinnaht am Saum
    front.add_notches(pt7)  # Hosenausschnitt (Kurve)

    # Info-Box
    front.add_info_box(
        notes=[
            f"Modellänge {model.MoL / CM:.1f} cm",
            f"SiH {meas.SiH / CM:.1f} cm",
            "1× Stoff (gegengleich)",
        ]
    )

    # -----------------------------------------------------------------------
    # RÜCKTEIL
    # -----------------------------------------------------------------------
    back = PatternPart(name="Rückteil")
    pattern_boy_trousers.add_part(back)

    # STEP 5: Grundgerüst Rückteil
    back_pt0 = pt5.translate(10 * CM, 0)  # von links
    back_pt1, back_pt2, back_pt3, back_pt4, back_pt5, back_pt6 = base_grid_trouser(
        meas, back_pt0, anchor_left=True
    )
    back_pt9, back_pt10, back_pt11, back_pt12, back_pt13 = get_leg_grid(
        meas, model, back_pt0, anchor_left=True
    )

    # STEP 6: Hosenbund
    pt16 = back_pt6.translate(-3.5 * CM, 0)
    pt17 = pt16.translate(0, -3 * CM)
    pt18 = back_pt0.translate(-2 * CM, 0)
    back.append(Segment(pt17, pt18))

    # STEP 7: Hinternaht
    pt19 = back_pt4.translate(0, -0.5 * meas.SiH)
    pt20 = back_pt4.translate((2 * (pt8.x - pt4.x) + 0.5 * CM), 0)
    pt21 = pt20.translate(0, 1 * CM)
    bz_contol4 = back_pt4.translate(3.05 * CM, -3.05 * CM)
    back.append(Segment(pt17, pt19))
    back.append(CubicBezier(pt19, bz_contol4, bz_contol4, pt21))

    # STEP 8: Seitennähte / Innenbeinnähte
    pt22 = back_pt12.translate(-1 * CM, 0)
    side_back = Segment(pt18, pt22)
    pt23 = intersect(side_back, knee)[0]
    pt24 = back_pt13.translate(1 * CM, 0)
    back_shift = back_pt0.x - pt0.x
    back_pt14 = pt14.translate(back_shift, 0)
    pt25 = pt15.translate(back_shift + (pt23.x - back_pt14.x), 0)
    back_aux = Segment(pt21, pt25)
    bz_control5 = back_aux.point_perpendicular(2.5 * CM, rel_pos_on_obj=0.5)
    back_inner_seam = Segment(pt24, pt25)

    back.append(back_aux.point_perpendicular(1.2 * CM, rel_pos_on_obj=0.5))
    back.append(CubicBezier(pt21, bz_control5, pt25.translate(0.1 * CM, -2 * CM), pt25))

    # STEP 9b: Modellänge Rückteil
    pt30 = intersect(seam, back_inner_seam)[0]
    pt31 = intersect(seam, side_back)[0]
    back.append(Segment(pt18, pt31))
    back.append(Segment(pt30, pt25))
    back.append(Segment(pt30, pt31))

    # Fadenlauf Rückteil
    grain_end_back = intersect(Segment(back_pt10, back_pt11), seam)
    back.add_grainline(start=back_pt9, end=grain_end_back[0])

    # Kerben
    back.add_notches(pt23, segment=side_back)  # Seitennaht am Knie
    back.add_notches(pt25, segment=back_inner_seam)  # Innenbeinnaht am Saum
    back.add_notches(pt19, segment=Segment(pt17, pt19))  # Hinternaht

    # Info-Box
    back.add_info_box(
        notes=[
            f"Modellänge {model.MoL / CM:.1f} cm",
            f"SiH {meas.SiH / CM:.1f} cm",
            "1× Stoff (gegengleich)",
        ]
    )

    # -----------------------------------------------------------------------
    # KONSTRUKTION (Hilfsgeometrie — wird standardmäßig nicht gerendert)
    # -----------------------------------------------------------------------
    aux = PatternPart(name="Konstruktion")
    pattern_boy_trousers.add_part(aux)

    _dash = StyleOptions(dash_array=[3, 2], stroke_color="lightgrey")
    _dash_red = StyleOptions(dash_array=[3, 2], stroke_color="red")

    # Vorderteil Grundgerüst
    aux.append(Segment(pt0, pt1), style=_dash, name="Grundgerüst: Taillenlinie")
    aux.append(Segment(pt0, pt6), style=_dash, name="Grundgerüst: Bundlinie")

    # Hosenausschnitt Hilfsgeometrie
    aux.append(Circle(pt4, 2.5 * CM), style=_dash)

    # Hosenbeingitter Vorderteil
    aux.append(Ray(pt2, (pt10.x, 0), name="Saumlinie"), style=_dash)
    aux.append(knee, style=_dash)
    aux.append(Segment(pt12, pt13), style=_dash)

    # Seitennaht / Innennaht Vorderteil
    aux.append(side, style=_dash)
    aux.append(inner_seam, style=_dash)
    aux.append(front_seam_aux, style=StyleOptions(dash_array=[3, 2]))
    aux.append(seam, style=_dash)

    # Rückteil Grundgerüst
    aux.append(Segment(back_pt9, back_pt11), style=_dash)

    # Hinternaht Hilfsgeometrie
    aux.append(Circle(back_pt4, 4.5 * CM), style=_dash)

    # Seitennaht / Innennaht Rückteil
    aux.append(back_aux, style=_dash)
    aux.append(side_back, style=_dash)
    aux.append(back_inner_seam, style=_dash_red)
    aux.append(Segment(pt22, pt24), style=_dash)

    # -----------------------------------------------------------------------
    # Maßkontrollkästchen & Referenzquadrat
    # -----------------------------------------------------------------------
    pattern_boy_trousers.set_reference_square(origin=pt0)

    return pattern_boy_trousers


def base_grid_trouser(
    meas: TrouserMeasurements, start_point: Point, anchor_left: bool = False
) -> tuple[Point, Point, Point, Point, Point, Point]:
    pt1 = start_point.translate(0, meas.SiH)
    pt2 = pt1.translate(0, meas.SrH)
    pt3 = pt1.translate(0, meas.KnH)
    if anchor_left:
        pt4 = pt1.translate(meas.vHoB, 0)
        pt5 = start_point.translate(meas.vHoB, 0)
        pt6 = pt5.translate(-1 * CM, 0)
    else:
        pt4 = pt1.translate(-meas.vHoB, 0)
        pt5 = start_point.translate(-meas.vHoB, 0)
        pt6 = pt5.translate(1 * CM, 0)
    return pt1, pt2, pt3, pt4, pt5, pt6


def get_leg_grid(
    meas: TrouserMeasurements,
    model: ModelConfig,
    start_point: Point,
    anchor_left: bool = False,
) -> tuple[Point, Point, Point, Point, Point]:
    base_grid = base_grid_trouser(meas, start_point, anchor_left=anchor_left)
    if anchor_left:
        pt9 = base_grid[0].translate(0.5 * meas.vHoB, 0)
        pt10 = base_grid[2].translate(0.5 * meas.vHoB, 0)
        pt11 = base_grid[1].translate(0.5 * meas.vHoB, 0)
        pt12 = pt11.translate(-(model.SaW / 2 + 0.5 * CM), 0)
        pt13 = pt11.translate((model.SaW / 2 + 0.5 * CM), 0)
    else:
        pt9 = base_grid[0].translate(-0.5 * meas.vHoB, 0)
        pt10 = base_grid[2].translate(-0.5 * meas.vHoB, 0)
        pt11 = base_grid[1].translate(-0.5 * meas.vHoB, 0)
        pt12 = pt11.translate(model.SaW / 2 + 0.5 * CM, 0)
        pt13 = pt11.translate(-(model.SaW / 2 + 0.5 * CM), 0)
    return pt9, pt10, pt11, pt12, pt13


if __name__ == "__main__":
    person = make_person()
    allowance = make_allowance()
    measurements = make_measurements_trouser(person, allowance)
    model_config = make_model_config()
    pattern = boy_trousers(measurements, model_config)
    export_pattern_svg_mm(
        pattern,
        filename="children/boy_shorts.svg",
        height_mm=DinA1.width,
        width_mm=DinA1.height,
        parts=[
            "Vorderteil",
            "Rückteil",
        ],  #  weglassen zum Debuggen entfernen
    )
