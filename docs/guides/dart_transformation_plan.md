# Implementation Plan: Triangle Dart Transformation

## Goal

Temporarily remove or transfer a shoulder dart from the armscye for correct sleeve
construction, and support full dart transfer as a general pattern-making operation.

---

## Review of the current state (2026-06-02)

Steps 1–3 of the previous plan were marked done, but the review revealed three
blocking issues that must be fixed before the rotation can be built on top:

**Issue A — Wrong pivot in `_element_is_between()`.**
The method uses the *start point of the dart leg segment* as the angular reference
origin.  The correct pivot for dart transfer is `dart.tip`.  Because the dart leg
has non-zero length, these points differ, and the angular sector is computed around
the wrong origin.  The method is also completely untested (`# pragma: no cover`).

**Issue B — Dart leg added as cutline in the example.**
`dart_toy_reference_point.py` calls `part.add_cutline(legs[closer_idx].geometry)`,
which treats the existing stitch-leg segment as a new cutline.  `add_cutline()`
then re-splits elements against that segment and appends it as a construction
element, corrupting the element list.  The dart leg must not be added as a cutline;
it already defines the sector boundary by its direction from `dart.tip`.

**Issue C — `transform()` only marks elements red.**
No rotation is applied.  `intake_angle` is not passed to the function, so the
correct rotation angle is never available.  The function is a stub.

**Issue D — Cutting line passes through wrong point.**
The issue specification says the cutting line must pass through the **dart tip**
(anchor point).  The example constructs `Ray(dart.center, ...)`, using the mouth
midpoint instead.

---

## Review of the current state (2026-06-13)

Running `dart_toy_reference_point.py` and comparing the result against the
classic *pivot method* (cut a new dart line from the tip → close the old dart
by rotating its inner leg onto its outer leg → the cut line opens into the new
dart at the same intake angle) revealed two more issues, in Step 3a and 3d–3g.

**Issue E — Wrong rotation angle in `transfer_dart` (3a).**
The implementation computes `rotation_angle = signed_angle(inner_leg_dir,
cut_dir)` and rotates the inner dart leg **onto the cut line**. In the pivot
method the rotation must instead **close the old dart** — rotate the inner leg
onto the *outer* leg — while the cut line, being part of the same rotating
sector, sweeps away from its original position by that same angle and opens
the *new* dart in the gap it leaves behind.

The bug is visible in the toy example's own output:

```
Original intake angle: 21.15°
New intake angle:      79.43°
```

Dart transfer relocates the intake angle, it does not change it:
`new_dart.intake_angle` should equal `dart.intake_angle` (21.15°). The 79.43°
that is actually produced is the angle between the inner leg and the cut
line — confirming the rotation is computed relative to the wrong target
direction.

Steps 3b/3c (split the outline with `add_cutline`; rotation sector =
`[inner_leg_dir, cut_dir]`) and the structure of 3e (new dart legs = cut line
∩ outline, before and after rotation) are conceptually correct and unchanged.
Only the rotation-angle formula (3a) and its knock-on description in 3d/3e and
the Step 4 validation table need correcting — see the revised sections below.

**Issue F — Stale old-dart artefacts orphan the outline after rotation.**
With Issue E fixed, `transfer_dart` now closes the old dart correctly (its two
`dart_stitch` legs land on the same segment). But the old dart's other visual
elements — `dart_roof`, `dart_fold`, `dart_center_notch`, `dart_notch`,
`dart_tip` — are never rotated or removed. Their representative points fall
outside the rotation sector `[inner_leg_dir, cut_dir]`, so 3c never selects
them and they stay at their original positions.

For the toy example this leaves the two `dart_roof` segments — the folded
"point" at `(135,94)–(140.415,80)–(135,66)` — behind as a disconnected
fragment: `(135,94)` is no longer shared with any other outline segment once
the rotated edge stub lands on `(135,66)` instead. The outline is no longer a
single closed loop, and `part.area_cm2` changes from **216.76 cm² to
187.65 cm²** — not because of any area-*accounting* problem, but because the
polygon itself is broken (an orphaned fragment is excluded from the shoelace
sum). The fix must restore a single closed outline; see the revised Step 4
validation below for what "correct" area accounting looks like once that
holds.

This is distinct from the gap that (correctly) opens at `new_dart.leg_a` /
`new_dart.leg_b` — that gap is *expected*; it is where the new dart's mouth
belongs. The fix for Issue F is therefore **not** "rotate the leftovers" but
"remove the old dart's elements and add the new dart's elements as a single
atomic operation" (see the new step 3f below).

This also settles the open design question from the previous discussion:
`transfer_dart` itself calls `part.add_dart(new_dart, ...)` — the caller does
not, and must not, call `add_dart` again afterwards.

**Invariant:** a part has the same number of darts before and after
`transfer_dart` — the old one is removed and the new one is added together,
or neither happens (the function should not leave a part with zero or two
darts where it had one).

**Note on area:** once the outline is a single closed polygon again,
`part.area_cm2` is still *not* equal before and after `transfer_dart` in
general — see the revised Step 4 validation table for the invariant that
actually holds.

**Issue G — `new_leg_b` lookup in 3e was numerically fragile at the exact
vertex it should land on.**
Writing the Step 5 test suite on a minimal rectangle (corners at the origin
instead of the toy example's `ANCHOR=(15,15)`) made `transfer_dart` raise
`ValueError: could not find outline intersection for the new dart legs` —
for geometry that differs from the toy example only by a translation. The
old 3e computed `new_leg_b` by intersecting `rotated_cut_ray` (the cut
direction rotated by `rotation_angle`) against the post-rotation outline.
Mathematically this intersection lands *exactly* on the rotated image of
`new_leg_a` — already a vertex of the post-rotation outline — but the two
values are computed via independent floating-point paths (one via rotating
a *point*, the other via rotating a *direction*, scaling, and adding to
`tip`), so the "intersection" can fall a hair outside the target segment's
`[0, 1]` parameter range depending on absolute coordinates, and
`_cutline_outline_intersection` then returns `None`. The toy example's
`ANCHOR=(15,15)` happened to round the right way; `ANCHOR=(0,0)` did not.

**Fix:** per the existing 3e description ("`new_leg_b = new_leg_a.rotate(dart.tip,
rotation_angle)`"), compute `new_leg_b` directly by rotating the `new_leg_a`
*point* — no second intersection search is needed (the discarded element from
the old `hit_b` was never used). This removes `_rotate_direction` and the
`rotated_cut_ray`/`hit_b` computation entirely. Verified: the toy example
still prints identical results (`New dart: leg_a=Point(x=60, y=195),
leg_b=Point(x=101.488, y=187.256)`, `New intake angle: 21.15°`), and the new
origin-anchored rectangle from the Step 5 test suite now succeeds.

---

## Corrected step-by-step plan

### Step 1 — Foundation (done, keep)

- [x] `PatternPart.get_dart(name)` returns legs and tip.
- [x] `Dart` properties: `tip`, `leg_a`, `leg_b`, `intake_angle`, `fold_line`,
  `rotate(pivot, angle)`.
- [x] `PatternPart.add_cutline(geometry)` appends a cut-line element and splits
  all existing elements at the intersection.

### Step 2 — Fix `_element_is_between()` (pivot bug) ✓

- [x] Replaced the old method with `_element_is_between(pivot, leg_direction,
  cut_direction, elem) -> bool` (static method, no longer `# pragma: no cover`).
  Pivot is now an explicit `Point`; both directions are 2-D unit vectors (any
  `Sequence[float]`).  The signed-angle comparison is done with `atan2(cross, dot)`
  relative to *pivot*, so the result is independent of where the dart leg starts.
- [x] Added `_rep_point(g)` static helper that extracts the representative point
  for all geometry types (Segment → midpoint, CubicBezier → `point_at_t(0.5)`,
  Circle/Dart → `.center`, InfoBox → `.position`, Rect → bbox centre, Triangle →
  centroid, Ray/Line/unknown → `None`).
- [x] Updated `transform()` to compute the pivot from the intersection of the two
  cut-line geometries and call `_element_is_between` with the corrected signature.
  Removed the debug `print()` statements and fixed the typo "excactly".
- [x] 29 unit tests in `tests/pattern/part/test_element_is_between.py` covering:
  `_rep_point` for every geometry type; CCW and CW sectors; inside, outside, both
  boundaries; point at pivot; no representative point; parallel and anti-parallel
  (degenerate) directions; `PatternElement` unwrapping; offset pivot.

### Step 3 — Implement `transfer_dart(part, dart, cut_line)` ✓ (Issue F fixed — atomic dart replacement, 3f/3g)

- [x] Added `rotate(center, angle_rad)` to `Segment`, `Circle`, `Triangle`,
  `InfoBox` in `_primitives.py` and to `CubicBezier` in `_bezier.py`.
- [x] Created `src/sewpat/pattern/_dart_transform.py` with the full
  `transfer_dart` implementation (precondition check, 3a–3g).
- [x] Wired `PatternPart.transfer_dart(dart, cut_line, *, sa_distance)` as a
  thin wrapper in `part.py`.
- [x] Updated `dart_toy_reference_point.py` to call `part.transfer_dart`
  directly and print the resulting dart geometry.
- [x] **Fix Issue E**: in `_dart_transform.transfer_dart`, change the 3a
  `rotation_angle` computation from `signed_angle(inner_leg_dir, cut_dir)` to
  `signed_angle(inner_leg_dir, outer_leg_dir)` per the revised 3a below, and
  re-verify the toy example now prints `New intake angle: 21.15°`. Done —
  verified against the toy example (21.15° == 21.15°, old dart legs coincide).
- [x] **Fix Issue F**: add a new step 3f that, in one atomic operation, (1)
  removes the old dart's `dart_stitch`, `dart_fold`, `dart_roof`,
  `dart_center_notch`, `dart_notch`, and `dart_tip` elements (keeping
  `dart_edge_stub`), and (2) calls `part.add_dart(new_dart, ...)` to draw the
  new dart. Renumber the old seam-allowance step to 3g (it now runs after the
  new dart's roof exists). Extend `transfer_dart`'s signature with
  `add_dart`'s style/notch kwargs and forward them in 3f. Update
  `PatternPart.transfer_dart`'s wrapper in `part.py` to accept and forward
  the same new kwargs. Done — verified against the toy example: the part
  still has exactly one dart named "Toy Dart", `new_dart.intake_angle` is
  still 21.15°, `part._outline_polygon()` is valid and simple (single closed
  loop, no orphaned fragments), and the full test suite (762 passed, 1
  skipped) shows no regressions. `part.area_cm2` changes from **216.76 cm² to
  231.08 cm²** — this is *expected*, not a bug: the new dart's depth
  (113.05 mm) differs from the old dart's depth (75.0 mm), because it is now
  measured to wherever the cut line meets the outline, and `area_cm2`
  includes each dart's `dart_roof` protrusion, whose area scales with depth.
  See the revised Step 4 validation below for the invariant that replaces the
  original "area unchanged" expectation.
- [x] **Remove the auxiliary cutline (3f.3)**: `transfer_dart` no longer
  leaves `cut_elem` — the "Cut Line" construction element added in 3b — in
  `part.elements`. It was only needed transiently to locate `new_leg_a` /
  `new_leg_b` in 3e and has no role in the final pattern; 3f now removes it
  by identity alongside the stale dart-role elements. Verified: the red
  "Cut Line" no longer appears in the transferred part's SVG output.
- [x] **Side-by-side display for the toy example**: added
  `PatternPart.translated(offset, name=None) -> PatternPart`, a
  general-purpose copy-and-translate method (generalises the previous
  `OverlayPart.explode`, which now delegates to it). `dart_toy_reference_point.py`
  now places the transferred part next to the original via
  `new_part.translated(...)` instead of at the same anchor — a part has
  either the original dart and outline, or the transferred ones, never both,
  so overlaying the two at the same position was misleading. The export
  canvas was widened to `2 * _A4_W × _A4_H` (A3-landscape) to fit both pieces
  side by side.

Replace the current `transform(cut_lines: list[str])` with a single well-typed
function that owns the full transformation.  Keep `transform()` as a deprecated
thin wrapper if backwards compatibility is needed, but the real logic lives here.

```
transfer_dart(
    part: PatternPart,
    dart: Dart,
    cut_line: Ray | Segment,
    *,
    sa_distance: float | None = None,
    stitch_style: StyleOptions | None = None,
    fold_style: StyleOptions = STYLE_DART_FOLD,
    precision_style: StyleOptions = STYLE_PRECISION_POINT,
    notches: bool = True,
    precision_tip: bool = True,
    notch_length: float | None = None,
    notch_width: float | None = None,
) -> Dart
```

The `stitch_style` … `notch_width` kwargs mirror `PatternPart.add_dart`'s
parameters exactly (same names, same defaults) and are forwarded verbatim to
the internal `part.add_dart(new_dart, ...)` call in step 3f — `transfer_dart`
does not interpret them itself.

**Precondition:** `cut_line` passes through `dart.tip`.  Raise `ValueError` if the
distance from `dart.tip` to the line is greater than a small tolerance (e.g. 1 mm).

#### 3a — Determine inner and outer leg

Compute the signed angle from each stitch-leg direction to the cut-line direction,
both measured from `dart.tip`.  The *inner leg* is the one with the smaller
unsigned angle to the cut line — i.e. the leg on the same side as the new cut.
The other leg is the *outer leg*: it stays put and becomes the stationary
boundary onto which the old dart closes.

```
dir_a, dir_b = dart.tip → dart.leg_a, dart.tip → dart.leg_b   # unit vectors
angle_a = signed_angle(dir_a, cut_direction)
angle_b = signed_angle(dir_b, cut_direction)

inner_leg_dir, outer_leg_dir = (dir_a, dir_b) if |angle_a| < |angle_b| else (dir_b, dir_a)

rotation_angle = signed_angle(inner_leg_dir, outer_leg_dir)   # |rotation_angle| ≈ dart.intake_angle
```

Rotating the sector `[inner_leg_dir, cut_direction]` (3c) by `rotation_angle`
around `dart.tip`:

- moves the **inner leg onto the outer leg**, closing the old dart — both legs
  now coincide and the old dart collapses to a single line, matching the
  "after" panel of the reference pivot-method diagram, and
- moves the **cut line** by the same angle, away from its original position,
  opening a new wedge of width `|rotation_angle| ≈ dart.intake_angle` where the
  cut line used to be — this wedge becomes the new dart (3e).

Verify: after rotation, the rotated inner-leg direction coincides with the
**outer-leg** direction within floating-point tolerance, and
`abs(rotation_angle) ≈ dart.intake_angle`.

#### 3b — Split outline at the cut line

Call `part.add_cutline(cut_line)` to split all existing outline elements where they
cross the cut line.  Do **not** add the dart leg as a cutline.

#### 3c — Identify elements to rotate

Collect every `PatternElement` (except the cut-line element itself) whose
representative point lies in the angular sector:

```
sector = (inner_leg direction from dart.tip) to (cut_line direction from dart.tip)
         taking the shorter arc (≤ π)
```

Use the fixed `_element_is_between(pivot=dart.tip, ...)`.  For elements that were
split in 3b, both halves are already in the list — only the half inside the sector
will be collected.

Include in the rotation set:
- outline segments inside the sector
- dart stitch/fold elements inside the sector
- construction elements inside the sector
- a **copy** of the cut-line segment (the copy will become one leg of the new dart)

#### 3d — Apply rotation

For each collected element rotate its geometry by `rotation_angle` around `dart.tip`:

```python
new_geom = elem.geometry.rotate(pivot=dart.tip, angle_rad=rotation_angle)
elem.geometry = new_geom          # PatternElement.geometry is mutable
```

All geometry types (`Segment`, `CubicBezier`, `Point`, `Circle`, etc.) already
implement `.rotate(pivot, angle_rad)`.

The original cut-line element remains in place at `cut_direction` — it forms
one edge of the new dart. A rotated *copy* of it now points along
`cut_direction` rotated by `rotation_angle`, forming the other edge (3e).
Meanwhile the rotated inner dart leg now coincides with the outer dart leg —
the old dart has closed.

#### 3e — Construct the new dart

The new dart occupies the triangular gap between the original cut line and the
rotated copy of it:

```
new_dart.tip   = dart.tip
new_dart.leg_a = intersection of original cut_line with the outline
new_dart.leg_b = new_leg_a.rotate(dart.tip, rotation_angle)
```

Find `new_leg_a` by calling `intersect(cut_line, outline_boundary)` against the
**post-rotation** outline (3d has already run). Record which outline element it
was found on — call it `mouth_elem`. `new_leg_b` is *not* found via a second
intersection (see Issue G) — it is the rotated image of `new_leg_a`, computed
directly by rotating the point.

Construct the dart with `Dart.from_edge_at_legs(edge=mouth_elem,
leg_a=new_leg_a, leg_b=new_leg_b, tip=tip, dart_type=dart.dart_type,
name=dart.name)` — **not** `Dart.from_tip_and_legs(...)`. This sets
`new_dart._edge_element = mouth_elem`, which 3f's call to
`part.add_dart(new_dart, ...)` needs in order to split `mouth_elem` into the
two `dart_edge_stub` pieces that close the new dart's mouth in the outline
(`_split_edge_at_dart_mouth`). Without `_edge_element`, `add_dart` silently
skips that split and the new dart's roof would overlay the still-intact
`mouth_elem`, breaking the outline polygon again.

`new_leg_a` and `new_leg_b` are generally on **different** outline elements —
this is the normal case, not an edge case. `new_leg_a` is the vertex created
by 3b's split of the outline at the original cut line, and sits on
`mouth_elem`, the *stationary* side of that split. `new_leg_b =
new_leg_a.rotate(dart.tip, rotation_angle)` is the *rotated image* of that
same vertex, and belongs to whichever element on the *rotating* side of the
split shares it — 3d already moved that element into place.

Because of this, `_split_edge_at_dart_mouth` only ever needs to split
`mouth_elem` at `new_leg_a`. In the toy example `new_leg_a` already coincides
with one of `mouth_elem`'s endpoints (it *is* the 3b split point), so the
split is a no-op that just relabels `mouth_elem` as `dart_edge_stub`.
`new_leg_b` is never split out of any element — it is already present as a
vertex on the post-rotation outline (the rotated endpoint described above),
and the new dart's roof (3f) simply connects to it.

Because `rotation_angle ≈ dart.intake_angle` (3a), the wedge between
`cut_line` and its rotated copy has width `dart.intake_angle`, so
`new_dart.intake_angle ≈ dart.intake_angle` falls out automatically —
matching the Step 4 validation check below.

#### 3f — Replace the old dart with the new dart (atomic)

The old dart has closed (3a/3d) and must be removed; the new dart (3e) must be
added. These two steps always happen together, in this order, so a part never
ends up with zero or two darts where it should have one:

1. Remove every element whose `role` is one of `{"dart_stitch", "dart_fold",
   "dart_roof", "dart_center_notch", "dart_notch", "dart_tip"}`. **Do not**
   remove `role="dart_edge_stub"` elements — these are the split remainders of
   the part's main outline created when *dart* was originally added
   (`_dart_integration.add_dart`), and after rotation (3d) they now meet at a
   single point, healing the seam where the old dart used to be. (A
   role-only filter is correct for single-dart parts, the current scope —
   see "Not yet in scope".)
2. Call `part.add_dart(new_dart, stitch_style=stitch_style,
   fold_style=fold_style, precision_style=precision_style, notches=notches,
   precision_tip=precision_tip, notch_length=notch_length,
   notch_width=notch_width)`, forwarding the kwargs `transfer_dart` received,
   to draw the new dart's stitch legs, fold line, roof, notches, and tip
   marker — and to split `mouth_elem` (3e) into the new dart's
   `dart_edge_stub` pieces.
3. Remove `cut_elem` (3b) — the "Cut Line" construction element used to find
   `new_leg_a`/`new_leg_b`. It was only a development aid for locating the
   new dart's mouth and has no role in the final pattern. `cut_elem.geometry`
   was already captured by reference for 3e, so removing the element from
   `part.elements` at this point is safe.

After this step the part again has exactly one dart — the new one — and the
outline is a single closed polygon, with no leftover construction elements
from the transfer itself.

#### 3g — Update seam allowance

If seam-allowance elements exist on the part, they were generated from the old
outline, which has now changed (3a–3f) — including the new dart's
`dart_roof` added in 3f. The SA must be regenerated against the **new**
outline:

- Remove all elements with `is_seam_allowance=True`.
- Re-run `part.add_seam_allowance(distance)` with the original distance
  (`sa_distance`).

### Step 4 — Return value and validation

`transfer_dart` returns the newly constructed `Dart` object for reference
(e.g. to look it up later or pass to further transfers). Its visual elements
have **already been added** to `part` by 3f — callers must not call
`part.add_dart(new_dart)` again, as that would leave the part with two darts
where it should have one.

Internal assertions (raise `AssertionError` in debug builds, log warnings otherwise):

| Check | How to test | When |
|---|---|---|
| Stitch length preserved | Sum of split-element lengths on cut line == original outline arc length at that crossing | after 3b |
| Old dart closed | After rotation, the rotated inner-leg endpoint coincides with the outer dart leg's endpoint within 1 mm | after 3d, before 3f |
| New dart valid | `new_dart.width > 0` and `new_dart.depth > 0` and `new_dart.intake_angle ≈ dart.intake_angle` | after 3e |
| Dart count invariant | Exactly one dart named `dart.name` exists on `part`, both before and after `transfer_dart` (same name — it was relocated, not renamed) | after 3f |
| Outline area accounting | `part.area_cm2` is **not** invariant in general — 3d's rotation is itself area-preserving, but `area_cm2` also includes each dart's `dart_roof` protrusion, whose area depends on dart depth. The only invariant is `area_after - area_before == roof_area(new_dart) - roof_area(dart)`. (Toy example: `231.08 - 216.76 == 25.58 - 11.26 == 14.32` cm².) | after 3f (and 3g, if SA regenerated) |

### Step 5 — Unit tests ✓

- [x] `_element_is_between` with pivot at tip: inside, outside, boundary,
  no-midpoint cases — covered by the existing 29 tests in
  `tests/pattern/part/test_element_is_between.py` (Step 2).
- [x] `tests/pattern/part/test_transfer_dart.py` — 13 tests on a 120x180mm
  rectangle with a triangle dart on the right edge (the toy example's
  geometry, anchored at the origin), transferred via `cut_direction=(0, 1)`:
  - `transfer_dart` raises `ValueError` when `cut_line` misses `dart.tip` by
    >1mm, and accepts it within the 1mm tolerance.
  - Returned `Dart` has the correct `tip` (unchanged), `name`, `dart_type`,
    `intake_angle ≈ dart.intake_angle`, `width > 0`, `depth > 0`, and both
    `leg_a`/`leg_b` lie on the post-transfer outline boundary.
  - Dart-count invariant (`get_dart` returns 2 legs + a tip before and
    after), the `cutline` element is removed, and the old dart's tip markers
    are removed and replaced 1:1 by the new dart's.
  - Outline area accounting: `area_after - area_before ==
    roof_area(new_dart) - roof_area(dart)`.
  - Old dart closed: rotating the inner leg by `rotation_angle` lands on the
    outer leg within 1mm, and `|rotation_angle| ≈ dart.intake_angle`.
  - Stitch length preserved: `add_cutline` (3b) does not change the total
    outline length.
  - Seam allowance: `sa_distance=10` regenerates a valid SA polygon that
    encloses the new outline and differs from the stale one; without
    `sa_distance`, the leftover SA is no longer valid/simple (motivating the
    kwarg).
  - This also surfaced and fixed Issue G (see above).
- Full suite: `python -m pytest tests/pattern/ tests/geometry/ -q --no-cov`
  → 775 passed, 1 skipped (was 762 passed before Step 5's 13 new tests).

---

## Not yet in scope

- Rhombus dart transformation (four-point diamond): deferred, noted in issue.
- Multi-dart parts: a part with two darts where one is transferred.
- Curved stitch lines (`stitch_curve_a/b`): rotation of CubicBezier control points
  is supported by the geometry layer but the integration path is untested.
- `new_leg_a` not landing on an existing outline vertex: 3e's `mouth_elem`
  split is a no-op relabel whenever `new_leg_a` already coincides with one of
  `mouth_elem`'s endpoints — true whenever the original cut line crosses the
  outline exactly at the 3b split point (the normal case, see 3e). If
  `mouth_elem` is instead a single long edge that the cut line crosses
  *mid-segment*, `_split_edge_at_dart_mouth` performs a real two-way split,
  and the `outer_subs` selection of which piece(s) remain as
  `dart_edge_stub` has not been exercised or tested for that case.
- `_cutline_outline_intersection`'s "farthest intersection from `dart.tip`"
  heuristic assumes the outline is star-shaped from `dart.tip` (the cut line
  crosses the post-rotation outline exactly once beyond the rotation
  sector). For concave outlines with multiple crossings, this heuristic may
  pick the wrong intersection for `new_leg_a` (since Issue G, `new_leg_b` no
  longer uses this helper — it is `new_leg_a.rotate(dart.tip,
  rotation_angle)`).

---

## Key API changes from the previous stub

| Before | After |
|---|---|
| `transform(cut_lines: list[str])` | `transfer_dart(dart, cut_line)` |
| pivot = dart leg start | pivot = `dart.tip` |
| cut line passes through `dart.center` | cut line must pass through `dart.tip` |
| dart leg added as cutline | dart leg defines sector boundary only, never added as cutline |
| marks elements red (debug) | rotates elements in place, returns new `Dart` |
| rotation aligns inner leg with cut line | rotation closes the old dart (inner leg → outer leg); cut line sweeps open into the new dart |
| caller calls `part.add_dart(new_dart)` after transfer | `transfer_dart` removes the old dart's elements and adds the new dart's elements atomically (3f) — dart count is invariant; callers must not call `add_dart` again |
