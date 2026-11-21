# Finishing mill F1–F5 (FM / HSM) (Apex built-in expert note)

Topic: finishing mill, FM, HSM, hot strip mill, AGC, HGC, looper, tension, bending, shifting, flatness, profile, MZC,
calibration, mill modulus, roll change, cobble.

## Stand equipment
4-high stands: work rolls + back-up rolls, hydraulic gap control (HGC) cylinders DS/OS with position transducers and
pressure transducers (piston side PS, rod side RS), work-roll bending (WRB), work-roll shifting (WRS), hydraulic
loopers between stands (HLC), side guides (SGC), work-roll cooling (basic + ADD), multi-zone cooling (MZC) for
flatness, interstand strip cooling, wedge adjustment (pass-line height).

## Controls
| Control | What it does | Main signals |
|---|---|---|
| HGC | positions the stand (position control 'PosControl' or force control) | ref / act gap, tilt, roll force DS/OS |
| AGC | keeps thickness: gaugemeter (h = S + F/M), monitor AGC from exit gauge, feed-forward | thickness deviation, mill modulus |
| Looper (HLC) | keeps interstand tension constant and absorbs mass-flow errors | looper position (mm / angle), strip tension N/mm², force |
| Mass-flow / speed | speed cascade from the master stand | stand speeds, looper position |
| Bending | profile (crown) and flatness | bending force OS/DS |
| Shifting | wear spreading, profile | shift top / bottom |
| MZC | thermal crown per zone for flatness | valve rows A / B, zones 1–30 |
| ASC | automatic shape / flatness control | flatness gauge |

## HMI ("FM Mode", "FM Bar Graph", "F1 – Detail", "F1 – Calibration")
F1 Detail shows: looper general status (HLC, man. intervention, transducer, servo), looper position OS/DS, PS/RS
pressures, servo %, strip tension next / actual, strip force, LP tare, strip weight / bending; HGC: roll force DS/OS,
diff. roll force, ref / act gap, gap DS/OS, tilt; bending and shifting; speed and cooling ADD 1/2; side guide set-up
/ ref / act; roll diameters; wedge adjustment height; passline deviation; calibration counter.

## Calibration (after every roll change)
Steps: check balancing → centre position → prepare / close gap → force taration → go to contact position →
roll force steps (e.g. 200 t, 500 t, 1000 t) → zeroing → open gap. Modulus test (HYS) measures mill stretch M.
After calibration DS−OS difference ≈ 0.

## Typical problems
| Symptom | Likely causes | Checks |
|---|---|---|
| Thickness off at head | set-up model, temperature, calibration, roll diameter | set vs act gap, FM entry temp, calibration |
| Thickness oscillation | AGC tuning, eccentricity of back-up roll, looper oscillation | AGC trend, roll eccentricity compensation |
| Looper hunting / tension swings | servo valve, speed mismatch, looper control gain, transducer | looper position & servo %, speed trims |
| Cobble at threading | wrong speed / gap, head shape, side guides, looper up too early | threading speed, head temp, SG |
| Strip break | excessive tension, edge crack, inclusions | tension trend, edges |
| Wavy edges / centre buckle | bending, thermal crown, MZC faults, roll wear | bending force, MZC valve test, roll profile |
| Camber / running off-centre | tilt, temperature wedge, SG offset | tilt, force DS/OS, centre-line trend |
| Rolled-in scale | descaler, roll surface | DSC pressure, WR surface |

Roll wear: plan work-roll change from 'Length rolled' (km) on the FM RCH screen; F5 / last stands usually wear first
for surface quality.
