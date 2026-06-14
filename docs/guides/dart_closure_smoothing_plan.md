# Plan: Smoothing the Source Edge After Dart Closure in `transfer_dart`

## Goal

When `transfer_dart` (`src/sewpat/pattern/_dart_transform.py`) relocates a dart,
the *old* dart's mouth on the source edge is closed by rotating one side of
the outline onto the other (the classic pivot method). After closure, the two
outline pieces that used to be separated by the dart's `dart_roof` no longer
line up perfectly:

* a small **positional jump** (gap or overlap) remains between them, and
* the curve direction (**tangent**) is discontinuous at the join — a visible
  kink.

This plan describes how to detect that junction and replace it with a short,
smooth, G1-continuous transition, so the resulting edge (e.g. the back
armscye after the shoulder-dart transfer in
`examples/women/top_waisted_dart.py`) is a single clean curve again.

---

## Reproducing the problem

Using `examples/women/top_waisted_dart.py`'s `create_block(...)`, before
`transfer_dart` is called, `block.back.shoulder_dart` has:

```
leg_a = (239.849, 164.25)   tip = (140.162, 164.25)
leg_b = (239.059, 149.142)
stitch_line_a.length = 99.6875
stitch_line_b.length = 100.0441   # diff ≈ 0.357 mm  ← "0.3 mm" from the issue
intake_angle ≈ 8.69°
```

`leg_a`/`leg_b` are the mouth of the dart cut into
`back.armscye_upper` (a `CubicBezier`, "Armscye Back Upper").
Projected onto that curve:

```
leg_a  → on-curve point (237.796, 164.089)   distance from leg_a ≈ 2.06 mm
leg_b  → on-curve point (239.059, 149.142)   distance from leg_b ≈ 0.00 mm
```

i.e. `leg_b` lies exactly on the curve, but `leg_a` does not — it is ~2 mm
"outside" it. `_split_edge_at_dart_mouth` (in
`src/sewpat/pattern/_dart_integration.py`) splits the curve at the *projected*
points, so the original `dart_edge_stub` pair already has a small gap between
the projected `leg_a` and the actual `leg_a`. Before `transfer_dart`, that gap
is bridged by the dart's `dart_roof` segment (`leg_a → roof`).

After `transfer_dart`:

```
new_dart.stitch_line_a.length = 136.728295456...65
new_dart.stitch_line_b.length = 136.728295456...68   # diff ≈ 3e-8 mm — fine

Armscye Back Upper, dart_edge_stub pieces:
  stub 1 (untouched):  (234.849, 213.875)  →  (237.796, 164.089)
  stub 2 (rotated):    (240.206, 164.25)   →  (261.862,  79.161)
```

`stub 2`'s start point is `leg_b` rotated by `rotation_angle` (≈ 8.69°)
around `tip` — by construction it sits at distance `|tip‑leg_b| = 100.044 mm`
from `tip`, along the direction of the old `leg_a`. `leg_a` itself sits at
`|tip‑leg_a| = 99.6875 mm` along that same direction. The two points are
therefore **2.42 mm apart** (the 2.06 mm pre-existing curve gap *plus* the
0.357 mm leg-length difference), and `dart_roof` — which used to bridge this
— has just been deleted as part of `_STALE_DART_ROLES`. That 2.42 mm gap,
plus the tangent jump described below, is the "jump" reported in the issue.

---

## Root cause analysis

### A. A pure rotation cannot reconcile two unequal leg lengths (fundamental)

`transfer_dart` step 3a picks one leg as `outer_leg_dir` (stays fixed) and
rotates the other (`inner_leg_dir`) by `rotation_angle =
signed_angle(inner_leg_dir, outer_leg_dir)` so it points the same direction as
the outer leg. Rotation preserves distance from the pivot (`dart.tip`), so the
rotated inner leg ends up at distance `|tip‑inner_leg|` along the outer leg's
direction — coinciding with the outer leg's endpoint **only if**
`|tip‑leg_a| == |tip‑leg_b|`.

`Dart.__init__` already warns when these two stitch-line lengths differ by
more than 1 mm (`src/sewpat/geometry/_dart.py:308‑318`, via `lengths_match`).
Below that threshold no warning fires, but the residual difference still
becomes a positional gap once the dart is closed. **This is inherent to the
pivot method**, not a one-off bug in this example — any dart whose two legs
aren't exactly equidistant from its tip will leave a sub-mm-to-few-mm gap when
closed.

### B. The dart's mouth point doesn't lie on the source edge (this example)

Independently of (A), `back.shoulder_dart_notch` (`leg_a`) is a construction
point that is *not* exactly on `armscye_upper`
(`src/sewpat/_blocks_geometry.py` — `dart_notch` is derived from
`Segment(armscye_shoulder_dropped, armscye_chest)`, a different line, then
translated). `_split_edge_at_dart_mouth` splits the curve at the *projection*
of `leg_a`, not at `leg_a` itself, so even the original (pre-transfer) outline
has a ~2 mm gap between the curve and the dart mouth — invisibly patched by
`dart_roof`. Once `dart_roof` is removed, this gap is exposed too.

This contributes most of the 2.42 mm seen above, but is specific to how
`shoulder_dart_back` is constructed. **It should ideally be fixed at the
source** (place `shoulder_dart_notch` exactly on `armscye_upper`, e.g. via
`armscye_upper.point_along_from(...)`), see [Open
questions](#open-questions--follow-ups). However, *any* general healing step
in `transfer_dart` must tolerate this kind of pre-existing slack too — we
can't assume future dart placements will always be perfectly on-curve.

### C. Tangent discontinuity ("not smooth") is also fundamental

Closing the dart rotates one side of the curve by `rotation_angle ≈ dart's
intake angle` (here ≈ 8.69°) relative to the other side. The two
`dart_edge_stub` pieces are sub-curves of the *same original* Bézier, so their
tangents at the cut points were nearly identical *before* the rotation — and
therefore differ by ≈ `rotation_angle` *after* it. A kink of several degrees
is exactly what a pattern-maker "trues" away by hand with a ruler/curve after
physically closing a paper dart. This is the second symptom in the issue
("the armscye curve is not so smooth") and needs to be addressed even in the
hypothetical case where (A) and (B) are both zero.

---

## Goals / Non-goals

**Goals**

* After `transfer_dart` closes the old dart, the source edge is a single
  geometrically continuous curve: no gap (G0) and no visible kink (G1) at the
  former dart mouth.
* The fix is local — it only touches the small region around the former dart
  mouth, and changes the total seam length by a negligible amount (well
  inside the existing 2 mm / 12 mm seam-pair tolerances).
* Works for both `Segment` and `CubicBezier` source edges, and regardless of
  which leg is "inner"/"outer".
* Degrades gracefully (warns, no-op) when the source edge isn't tracked
  (`dart._edge_element is None`) or the geometry is unsupported — consistent
  with `_split_edge_at_dart_mouth`'s existing behaviour.

**Non-goals (for this plan)**

* Rhombus dart closure (no outline mouth/`dart_edge_stub` is involved).
* Multi-dart edges (two darts cut from the *same* source element).
* Fixing root cause (B) at the construction site
  (`_blocks_geometry.py`) — tracked separately, see [Open
  questions](#open-questions--follow-ups).

---

## Proposed approach: trim-and-blend the healed junction

### Where it fits in `transfer_dart`

A new step runs **after 3d (rotation)** and **before 3f (remove stale dart
roles / add the new dart)** — call it **3e.5**, since it needs
`rotation_angle` (3a) and the post-rotation geometry (3d), but must run while
the old dart's `dart_edge_stub` pair is still identifiable (before 3f rewrites
`part.elements`).

```
3a  determine inner/outer leg + rotation_angle
3b  add_cutline
3c  collect elements to rotate
3d  rotate them
3e  construct new_dart
3e.5  ← NEW: heal the old dart's mouth on the source edge
3f  remove stale dart-role elements, add_dart(new_dart)
3g  regenerate seam allowance
```

### 3e.5 — Identify the healed pair

1. If `dart._edge_element is None`, skip (no outline mouth to heal).
2. Find the (at most two) `PatternElement`s with `role == "dart_edge_stub"`
   and `get_name() == dart._edge_element.get_name()`. If there are not
   exactly two, warn and skip (multi-dart-edge case, out of scope).
3. For each stub, find which endpoint (`start`/`end`) is the "facing"
   endpoint — the one nearest to `dart.leg_a` **or** to
   `dart.leg_b.rotate(dart.tip, rotation_angle)` (the rotated inner leg).
   Exactly one stub should face each of these two points (one stub was inside
   the rotation sector and got rotated in 3d, the other wasn't — see the
   worked example above). Re-orient each stub with `_reverse_geom` (already
   in `_algorithms.py`) if necessary so that its facing endpoint is `.end`
   for the "outer" stub (`ga`) and `.start` for the "inner"/rotated stub
   (`gb`).
4. The other endpoints of `ga`/`gb` connect onward to the rest of the outline
   and must not move.

### 3e.5 — Build the blend

Add a new helper in `src/sewpat/geometry/_algorithms.py`, next to
`round_corner`/`miter_corner`:

```python
def blend_join(
    ga: Segment | CubicBezier,
    gb: Segment | CubicBezier,
    blend_length: float = 5.0,
) -> tuple[Segment | CubicBezier, CubicBezier, Segment | CubicBezier]:
    """Trim *ga* and *gb* near their facing ends and join them with a
    G1-continuous CubicBezier.

    Returns ``(ga_trimmed, blend, gb_trimmed)``. ``blend`` runs from the new
    end of ``ga_trimmed`` to the new start of ``gb_trimmed``, with handle
    lengths chosen so its start/end tangents match ``edge_tangent(ga,
    at_end=True)`` / ``edge_tangent(gb, at_end=False)`` (standard cubic
    Hermite-to-Bézier construction, handle length = |gap| / 3).
    """
```

Why a dedicated helper rather than reusing `round_corner`:
`round_corner` models a **true circular arc** and falls back to a bare
`Point` (no smoothing at all) whenever the two radii differ by >1%, the
tangent lines don't intersect, or the angle is near 0°/180°. Those fallbacks
are common for the small, near-flat junctions produced by dart closure — e.g.
in the worked example above the "kink" is only ~8.7°, very close to the
"nearly straight" rejection threshold. `blend_join` always produces a valid
G1 (tangent-matched) cubic, independent of curvature/radius — closer to
"make this anchor point's handles symmetric" in a vector editor, which is
exactly the "true the seam with a curve ruler" operation a pattern-maker would
do by hand.

Algorithm for `blend_join`:

1. Let `gap = ga.end.distance_to(gb.start)`.
2. Trim `blend_length` mm off the end of `ga` (using `point_at_length` +
   `split` for both `Segment` and `CubicBezier`) → `ga_trimmed`, with new end
   point `Pa` and tangent `Ta = edge_tangent(ga, at_end=True)` (tangent
   direction near the original end is a good-enough approximation for a small
   trim).
3. Symmetrically trim `blend_length` off the start of `gb` → `gb_trimmed`,
   new start point `Pb`, tangent `Tb = edge_tangent(gb, at_end=False)`.
4. `h = Pa.distance_to(Pb) / 3`
5. `blend = CubicBezier(Pa, Pa + h*Ta, Pb - h*Tb, Pb)`
6. Clamp `blend_length` to `0.4 * min(ga.length, gb.length)` so very short
   stubs aren't over-trimmed; if both `ga` and `gb` are shorter than a few mm,
   warn and skip (fall back to a plain bevel — `with_endpoints` snapping `Pa`
   to `Pb`'s midpoint, no tangent fix).

This handles both failure modes from the diagnosis uniformly:

* **Pure positional gap, matching tangents** (hypothetical, root cause A/B
  with C=0): `blend` is a short, nearly-straight cubic connecting `Pa` to
  `Pb` — visually a tiny smoothing of the existing curve direction.
* **Zero gap, tangent kink** (root cause C alone): `Pa ≈ Pb` but `Ta ≠ Tb`;
  `blend`'s control points still diverge by `h*Ta` / `h*Tb`, producing a
  short S-curve that eases between the two directions instead of a sharp
  corner.
* **Both** (the realistic case, A+B+C): `blend` is a short curve that closes
  the gap *and* eases the direction change — both symptoms fixed by one
  operation.

### 3e.5 — Splice the result back in

Replace `ga` and `gb` in `part.elements` with `ga_trimmed`, `blend`,
`gb_trimmed` (3 elements replacing 2), preserving each original element's
`role="dart_edge_stub"`, `name`, `style`, and any `_sa_center` / `_leg_pt`
attributes (copy onto `ga_trimmed`/`gb_trimmed`; `blend` gets no special
attributes — it's pure outline). `_reverse_geom` orientation from the
identification step must be undone before re-insertion so the chain still
flows in the original direction.

---

## Implementation plan

1. **`_algorithms.py`**: add `blend_join` (+ small private helper to trim a
   `Segment`/`CubicBezier` by arc length from either end — likely factored out
   of `point_at_length`/`split`). Export if needed for tests.
2. **`_dart_transform.py`**: add a private `_heal_dart_mouth(part, dart,
   rotation_angle)` implementing the identification + splice logic above; call
   it as step 3e.5 inside `transfer_dart`.
3. **`transfer_dart` signature**: add `smooth_closure: bool = True` and
   `smooth_blend_length: float = 5.0` kwargs; thread through
   `PatternPart.transfer_dart` in `part.py`. Setting `smooth_closure=False`
   restores today's behaviour (useful for tests that assert the *unhealed*
   geometry, and as an escape hatch).
4. **`examples/women/top_waisted_dart.py`**: no code change expected — the
   existing `transfer_dart(...)` call picks up the new default.
5. **Docs**: extend `docs/guides/darts.md`'s dart-transfer section with a short
   note on automatic mouth healing and the new kwargs.

---

## Testing & validation plan

* **Unit tests for `blend_join`** (new `tests/geometry/test_blend_join.py`):
  * Two collinear segments with a gap → `blend` is (near-)degenerate /
    straight, total length ≈ original + gap.
  * Two segments meeting at a point but at an angle (pure kink, gap=0) →
    `blend` is a short S-curve; `edge_tangent` at both ends matches `ga`/`gb`.
  * Two `CubicBezier`s (gap + kink) → both G0 and G1 continuity hold at both
    splice points within 1e-6.
  * Degenerate/too-short inputs → falls back to a bevel with a `UserWarning`,
    doesn't raise.
* **`transfer_dart` integration tests** (extend
  `tests/pattern/part/test_transfer_dart.py`): the current 120×180 mm
  rectangle fixture has `tip` on the perpendicular bisector of `leg_a`/`leg_b`
  (equal leg lengths) — it won't exercise this fix. Add a variant fixture
  where `tip` is *off* the bisector (unequal leg lengths, like the real
  shoulder dart) and assert:
  * the post-transfer outline is a single closed, simple polygon
    (`outline_polygon` / `part._outline_polygon()`), as already checked;
  * **no gap**: consecutive outline elements share endpoints within, say,
    0.01 mm (tighter than the original 0.5 mm `split_at_points` tolerance);
  * **no kink**: `edge_tangent` agrees within a small angular tolerance
    (e.g. 2°) across every outline join, including the healed one.
* **Example/integration smoke test**: re-run
  `examples/women/top_waisted_dart.py` and re-check the existing
  `validate_seam_pairs`/`validate_widths` assertions still pass — `blend_join`
  changes seam length by `O(blend_length)` ≈ a few mm at most, well inside the
  2 mm / 12 mm tolerances already in use. Optionally add a direct check on
  `block.back.armscye_upper`-derived outline length before/after.

---

## Open questions / follow-ups

* **Fix root cause (B) at the source.** `back.shoulder_dart_notch` /
  `back.shoulder_dart` (`src/sewpat/_blocks_geometry.py`,
  `_build_darts` in the same file) should probably place `leg_a` exactly on
  `armscye_upper` (e.g. derive it via `armscye_upper.point_along_from(...)`
  from a point that *is* on the curve, the way `leg_b` already is). This
  would shrink the gap healed by 3e.5 from ~2.4 mm down to the ~0.36 mm purely
  attributable to (A), but does **not** remove the need for 3e.5 — (A) and (C)
  are inherent to dart closure for *any* dart, not just this one. Worth a
  follow-up issue regardless of whether 3e.5 lands first.
* **Default `smooth_blend_length`.** 5 mm is a guess; depends on how visible
  the kink is for typical intake angles (a few degrees to ~20°). May want to
  scale it with `dart.intake_angle` (bigger angle → longer blend) rather than
  a fixed constant.
* **Multi-dart source edges.** If a future block cuts two darts from the same
  curve, step 3e.5's "exactly two `dart_edge_stub`s with this name" assumption
  breaks. Needs a more specific identification key (e.g. tag stubs with the
  dart's identity, not just the source edge's name) before that scenario is
  supported.
