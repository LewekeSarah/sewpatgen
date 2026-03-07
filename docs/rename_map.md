# Abbreviation rename map — German → English

Adopted in the refactor of 2026-03-05.
All source identifiers were renamed to English; the original German
abbreviation is preserved as an inline comment on every field definition.

---

## `Person` — body measurements

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `KöH` | `height` | Körperhöhe |
| `BrU` | `bust` | Brustumfang |
| `TaU` | `waist` | Taillenumfang |
| `HüU` | `hip` | Hüftumfang |
| `HüT` | `hip_depth` | Hüfttiefe |
| `BrT` | `bust_depth` | Brusttiefe |
| `HlB` | `neck_size` | Halslochbreite |
| `BrPA` | `bust_span` | Brustpunktabstand |
| `SuB` | `shoulder_width` | Schulterbreite |
| `RüL` | `back_length` | Rückenlänge |
| `VL` | `front_length` | Vorderlänge — VL2 variant kept as note (balancing, future feature) |
| `SiH` | `body_rise` | Sitzhöhe |
| `SrH` | `inseam` | Schritthöhe |
| `RüB` | `back_width` | Rückenbreite |
| `AlT` | `armscye_depth` | Armlochtiefe |
| `ArD` | `armscye_width` | Armdurchmesser |
| `BrB` | `chest_width` | Brustbreite |
| `gender` | `gender` | Geschlecht — unchanged |

## `BalanceAdjustments`

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `RüL` | `back_length` | Rückenlänge |
| `VL` | `front_length` | Vorderlänge |

## `PersonalAdjustments`

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `BeckenAdjustment` | `hip_offset` | Becken-Korrektur |

## `Allowance` — ease additions

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `RüB` | `back_width_ease` | Rückenbreite-Zugabe |
| `AlT` | `armscye_depth_ease` | Armlochtiefe-Zugabe |
| `ArD` | `armscye_width_ease` | Armdurchmesser-Zugabe |
| `BrB` | `chest_width_ease` | Brustbreite-Zugabe |
| `TaU` | `waist_ease` | Taillenumfang-Zugabe |
| `HüU` | `hip_ease` | Hüftumfang-Zugabe |
| `BrU` | `bust_ease` | Brustumfang-Zugabe (derived: 2 × (back_width_ease + armscye_width_ease + chest_width_ease)) |
| `SiH` | `body_rise_ease` | Sitzhöhe-Zugabe |
| `SrH` | `inseam_ease` | Schritthöhe-Zugabe |

## `BlouseMeasurements` — finished dimensions

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `BrW` | `bust_width` | finished bust half-width (= back_width_ease + armscye_width_ease + chest_width_ease + bust/2) |
| `TaW` | `waist_width` | finished waist half-width |
| `HüW` | `hip_width` | finished hip half-width |
| *(body fields)* | *(same as Person above)* | |

## `GarmentConfig` / `TrouserConfig`

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `MoL` | `length` | Modell-Länge |
| `SaW` | `hem_width` | Saumweite |
| `ZuvHoB` | `front_trouser_ease` | Zugabe vordere Hosenbreite |

## `WaistDistribution` + internal distribution helpers

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `vTaB` | `front_waist_width` | vordere Taillenbreite |
| `hTaB` | `back_waist_width` | hintere Taillenbreite |
| `TaB` | `total_waist_width` | Taillenbreite gesamt |
| `Ausfallbetrag` | `hip_shortfall` | Ausfallbetrag |
| `SaEinzug` | `side_seam_intake` | Seitennaht-Einzug |
| `vAbI` | `front_dart_width` | vorderer Abnäher-Einzug |
| `hAbI` | `back_dart_width` | hinterer Abnäher-Einzug |

## `FitClass` — ease fields

| Old (DE) | New (EN) | German full term |
|---|---|---|
| `ZuBrA` / `_ZuBrA` | `bust_point_ease` | Zugabe Brustpunktabstand |
| *(new)* | `back_width_ease` | Rückenbreite-Zugabe |
| *(new)* | `armscye_width_ease` | Armdurchmesser-Zugabe |
| *(new)* | `chest_width_ease` | Brustbreite-Zugabe |
| *(new)* | `armscye_depth_ease` | Armlochtiefe-Zugabe |
| *(new)* | `waist_ease` | Taillenumfang-Zugabe |
| *(new)* | `hip_ease` | Hüftumfang-Zugabe |

`bust_width_ease` is **never stored** — always derived:
`bust_width_ease = 2 × (back_width_ease + armscye_width_ease + chest_width_ease)`

## `fitclass.csv` — multi-index layout

Two-row header, `pk` as index, pairs of `(lo, hi)` columns per ease field.
Loaded with `pd.read_csv(..., header=[0, 1], index_col=0)`.
All values in **cm** in the file; converted to mm (× 10) on load.

```
ease,  back_width_ease,   armscye_width_ease,  chest_width_ease,  armscye_depth_ease,  waist_ease,    hip_ease,      bust_point_ease
pk,    lo,    hi,         lo,     hi,           lo,    hi,         lo,    hi,            lo,   hi,     lo,   hi,      lo,   hi
4,     0.7,   1.0,        1.5,    2.0,          1.3,   1.5,        1.0,   2.0,           4.0,  8.0,    4.0,  8.0,     0.0,  0.5
```

Only PK 4 is populated with real values. All other PKs raise `KeyError` until
the full table is digitised from the Mueller & Sohn source.
