# ESP – Endless Strip Production: line overview (Apex built-in expert note)

Topic: ESP, endless rolling, Arvedi ESP, thin slab casting and direct rolling, coil mode, batch mode, mass flow.

## 1. What ESP is
ESP (Endless Strip Production, Arvedi / Primetals) links a thin-slab continuous caster directly to the rolling mill
in one line, with no tunnel furnace and no cut between caster and mill in endless mode. The strip is only cut at the
coilers by a high-speed flying shear. Typical line (≈ 180 m long):

| Order | Equipment | Abbrev. on HMI | Role |
|---|---|---|---|
| 1 | Thin-slab caster (curved, funnel mould) | Caster | Slab ~ 90–140 mm thick, casting speed ~ 4–7 m/min |
| 2 | HRM entry | ENT | Transfer from caster to first stand |
| 3 | High Reduction Mill, stands R1–R4 | HRM, R1…R4 | Rolls the slab (still hot core) to a transfer bar of ~ 10–20 mm |
| 4 | Pendulum shear + pusher / piler | SHP / PS, PIL | Cuts the bar in batch / plate mode, at start-up or emergency; plates are piled off-line |
| 5 | Rotary crop shear | SHR | Crop / emergency cut before the heater |
| 6 | Edge heater (optional) | EDH | Heats bar edges |
| 7 | Induction heater | IDH | Re-heats the bar (e.g. ~ 950 → 1100 °C) before finishing |
| 8 | Descaler | DSC | High-pressure water removes scale before F1 |
| 9 | Finishing mill, stands F1–F5 | FM, F1…F5 | Rolls to final thickness (≈ 0.8–12 mm) |
| 10 | Laminar cooling / run-out table | LCS, ROT | Cools from finishing temp (~ 820–900 °C) to coiling temp (~ 500–700 °C) |
| 11 | High-speed (flying) shear | HSS | Cuts the endless strip at coil change |
| 12 | Down coilers DC1–DC3 | DC1…DC3 | Coil alternately; one coils while the next is prepared |

## 2. Operating modes
- **Coil mode / Endless mode**: caster → HRM → FM → coilers continuous. Strip is cut only by the HSS. Best yield,
  thin gauges possible (the strip head does not have to be threaded every coil).
- **Batch mode**: the bar is cut into lengths (by the pendulum / rotary shear) and each piece is rolled and coiled
  separately (like a classic mill). Used at start-up, for thick strip, grade changes or after disturbances.
- **Plate mode**: the pendulum shear cuts plates which the pusher / piler removes from the line (e.g. when the FM is
  not ready, after a cobble, during casting start, so the caster can keep casting).
- **Mill Mode → C** button on the HMI = request transition to coil (endless) mode.

## 3. The key principle: mass flow coupling
In endless mode the mass flow is constant along the line:

  casting speed × slab thickness = bar speed × bar thickness = strip speed × strip thickness

Example: 5.1 m/min × 135 mm  →  bar 12 mm at ≈ 0.96 m/s  →  strip 1.78 mm at ≈ 6.4 m/s.
Consequences:
- The **caster sets the pace**. Any casting speed change goes through the whole mill; the mill speed cascade follows.
- A mill stop forces the caster to slow / switch to plate mode (pendulum shear + piler).
- HRM and FM stand speeds must be matched (interstand tension, loopers in the FM).
- Thin strip = high strip speed at the coilers (limits by coiler and HSS capability).

## 4. Interlocks to switch to coil mode (typical, check plant list)
FM ready for rolling; IDH entry temperature high enough; strip thin enough at IDH entry; pendulum shear cut active;
enough IDH converters running (e.g. ≥ 6); same strip under HRM entry and pendulum shear; coiler ready / simulation
off; casting speed high enough. On the Primetals HMI they are the ✓ list on the "Overview Pendulum Shear / Pusher and
Piler" screen.

## 5. Temperatures along the line (typical orders of magnitude)
Slab at HRM entry (R1 entry) ~ 1000–1100 °C surface (core hotter) · R4 exit ~ 900–1000 °C · IDH entry ~ 900–950 °C ·
IDH exit ~ 1050–1150 °C · FM exit (FDT) ~ 820–900 °C · coiling (CT) ~ 500–700 °C depending on grade.

## 6. Energy
ESP saves energy because the slab is rolled with its casting heat; the induction heater is the largest consumer
(several MW). The Technology screen shows specific energy (kWh/t) and EDH / IDH / HRM / FM power.

## 7. Typical disturbances and where to look
| Symptom | First checks |
|---|---|
| Mill trips to plate mode | Alarm line, pendulum-shear permissives, FM ready, IDH converters, casting speed |
| Thickness deviation at coils | AGC status, IDH exit temperature, HRM bar thickness, mill modulus / calibration |
| Strip wandering / centre-line deviation | Side guides, tilt (wedge), roll wear, temperature wedge across width |
| Coiling temperature off | Laminar cooling headers out of service, FDT, speed, model adaptation |
| Coil change failure | HSS cut angle, coiler 'Prepared', pinch-roll / wrapper-roll gaps, LAS speed |

Safety: hot strip, hydraulic pressure, rotating equipment, radiation gauges (thickness / profile gauges) — always
follow plant LOTO and OEM procedures.
