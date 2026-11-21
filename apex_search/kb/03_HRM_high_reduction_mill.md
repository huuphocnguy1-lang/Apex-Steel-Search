# HRM – High Reduction Mill / roughing mill R1–R4 (Apex built-in expert note)

Topic: roughing mill, RM, HRM, R1 R2 R3 R4, reduction, AGC, HGC, tilt, wedge, crown, centre-line, roll change, calibration.

## Role
The HRM (4 four-high stands directly after the caster) rolls the slab with its casting heat to a transfer bar
(e.g. 135 mm → 65 → 35 → 20 → 12 mm). Reductions are large (≈ 40–50 % per stand). Speeds are low (0.1–1 m/s) and
fixed by casting speed (mass flow). No loopers: interstand tension is controlled through stand speeds (ITC).

## Equipment per stand
Work rolls (WR) + back-up rolls (BUR), main drive (MV converter, motor; e.g. 33 kV supply), hydraulic gap control
(HGC) cylinders on DS and OS, work-roll bending (WRB), work-roll shifting (WRS) where fitted, roll cooling (basic +
ADD 1 / ADD 2), side guides (SG), pinch rolls (PR), thickness / profile gauges at HRM exit.

## Important values on the HMI ("HRM Mode", "HRM Bar Graph")
| Value | Meaning | Good practice |
|---|---|---|
| HGC Ref / Act | cylinder position | Act follows Ref |
| Gap Ref / Act | roll gap | as set-up |
| Tilt (DS−OS) | gap difference across width | close to 0; corrects wedge / strip running off-centre |
| Rollforce | per stand, MN | within design; DS vs OS difference shows off-centre strip / tilt |
| Reduction % | per stand | per Level-2 schedule |
| Centre-line deviation | strip position at HRM exit | small (± few mm) |
| Crown C25 / C40, wedge C25 / C40 | profile at 25 / 40 mm from edge | wedge ≈ 0 µm; crown per target |
| Current % | main drive load | margin to 100 % |

## Controls
- **AGC** (automatic gauge control): adjusts HGC position to keep exit thickness, using roll force and mill modulus
  (gaugemeter principle: h = S + F / M, S = gap, F = force, M = mill modulus).
- **ITC** interstand tension control (R1/R2, R2/R3, R3/R4): speed trim to keep small tension.
- **Bending / shifting**: profile and flatness, wear distribution.
- **Stand modes**: rolling / dummy / out of line, 'Ghost' (virtual material) for tests.

## Roll change and calibration
Roll change (HRM RCH screen): stand in Roll Change mode → Remove Sequence → new rolls → Insert Sequence; enter
diameters (used by speed & gap set-up). Then **calibration**: balancing check → close gap → roll-force taration →
contact → 200 t / 500 t / 1000 t → zeroing → open gap; optional mill-modulus (HYS) test. Check DS−OS difference after
calibration ≈ 0.

## Typical problems
| Symptom | Likely causes | Checks |
|---|---|---|
| Wedge / camber, strip runs to one side | tilt wrong, temperature wedge from caster, worn rolls, side guide offset | tilt, force DS/OS, SG positions, roll profile |
| Thickness deviation | calibration drift, AGC off, temperature change from caster | AGC status, calibration date, HRM exit temp |
| High roll force / current | cold slab, high reduction, wrong roll diameter entered | R1 entry temp, reduction plan, diameters |
| Tension spikes | speed mismatch, roll diameter error | ITC trend, diameters |
| Bar head turning up/down | top/bottom speed or temperature difference | roll speeds, cooling |

Safety: rotating rolls, hydraulic stored energy (HGC, balancing), roll change car movements.
