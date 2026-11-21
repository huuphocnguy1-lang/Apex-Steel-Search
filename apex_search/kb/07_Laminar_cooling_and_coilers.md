# Laminar cooling, high-speed shear and down coilers (Apex built-in expert note)

Topic: laminar cooling, LCS, ROT, coiling temperature, CT, high speed shear, HSS, flying shear, down coiler, DC,
mandrel, wrapper rolls, pinch roll, coil change, endless.

## Laminar cooling (run-out table)
Top and bottom headers in groups (e.g. G1–G4, headers 1–16) cool the strip from finishing temperature (FDT,
~ 820–900 °C) to coiling temperature (CT, ~ 500–700 °C). A cooling model selects the number of headers from speed,
thickness, FDT and CT target; trim headers correct the last degrees; feedback from the CT pyrometer adapts the model.
Side sprays (CS) remove water from the strip surface.

| Problem | Likely causes | Checks |
|---|---|---|
| CT too high | headers out of service (crossed on HMI), low water flow / pressure, speed higher than planned | header status, pump, tank level |
| CT too low / variable | water on strip (side sprays), model adaptation, pyrometer steam | side sprays, pyrometer window |
| Flatness after cooling bad | top/bottom imbalance, edge over-cooling | top/bottom ratio, edge masking |
| Header valve not switching | valve / positioner, air supply | valve test |

## High-speed shear (HSS) – endless mode
A drum / cam flying shear cuts the strip at full speed at each coil change. Drum and cam motors are synchronised to
strip speed (encoders, last cut angle ≈ 180°). Before the cut the next coiler must be 'Prepared' and READY. Signals:
cam / drum angle, cut-done counter, pinch rolls EN/EX gaps and forces, side guides, fly-wheel coupled / uncoupled,
lubrication flow per lube point (HSS Detail 2).

| Problem | Likely causes | Checks |
|---|---|---|
| Failed cut | timing / encoder, knife wear, speed mismatch | last cut angle, encoder reset, knife |
| Head not entering next coiler | gate / deflector, pinch roll gap, wrapper rolls | coiler 'Prepared', PR gap |
| Lube alarm | blocked lube line, pump | HSS Detail 2 lube list |

## Down coilers (DC1–DC3)
Each coiler: pinch rolls (top / bottom, gap and force OS/DS), side guides, mandrel (expansion, gear step, bearings,
drive), wrapper rolls WR1–WR4 (hydraulic cylinders with position / force control, step control to avoid marks from
the strip head), blow-down / coil handling. States on HMI: Selected, Production, Prepared, Loaded, READY / NO-READY.

| Problem | Likely causes | Checks |
|---|---|---|
| Bad wrap / head not gripped | wrapper-roll gaps vs thickness, calibration (P-Cal), mandrel expansion, speed lead | WR gaps, Cal. Val., speeds |
| Telescoped coil | side-guide position / force, strip tension, centre-line | SG, tension, CL deviation |
| Coil marks from head | wrapper-roll step control timing | WR timing |
| Coiler NO-READY | mandrel not collapsed / expanded, drive, coil car, hydraulics | coiler detail screen |

Safety: rotating mandrel, hot coils, hydraulic wrapper-roll cylinders (stored energy), coil car movements.
