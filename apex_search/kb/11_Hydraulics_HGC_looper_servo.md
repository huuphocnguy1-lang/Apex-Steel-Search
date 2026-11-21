# Mill hydraulics: HGC, loopers, bending, side guides, wrapper rolls (servo systems) (Apex built-in expert note)

Topic: HGC, hydraulic gap control, AGC cylinder, servo valve, looper hydraulics, bending, shifting, side guide,
wrapper roll, position control, force control, servo null, hunting, leakage test.

## HGC (hydraulic gap control) cylinders
One large cylinder per side (DS / OS) above the back-up roll chocks. Each has: servo valve(s) on a manifold, position
transducer, pressure transducers (piston side PS, rod side RS), pilot-operated check / safety block, accumulators
near the cylinder for fast response. Control in **position** (gap) or **force** mode, with tilt control (DS−OS).
- Roll force = PS·A_piston − RS·A_rod (minus friction / balancing).
- Typical supply: 250–300 bar; rod side held at low constant pressure (e.g. 20–40 bar) for stability.
- 'Servo %' on the HMI = valve command; in steady state near 0 % (only null offset).

### HGC checks
| Symptom | Likely causes | Checks |
|---|---|---|
| Gap drifts with no command | servo null shift, internal leakage, check valve leaking | servo % in steady state, leakage test |
| Hunting / oscillation | gain too high, air in oil, worn servo, transducer noise, accumulator pre-charge | position trend, pressure ripple, bleed air |
| Slow response | low supply pressure, filter clogged, accumulator empty, servo pilot filter | P supply, ΔP filter, pre-charge |
| DS/OS force difference | tilt, strip off-centre, transducer error, friction in chock | tilt, centre-line, transducer calibration |
| Calibration step fails | balancing pressure, transducer, leakage | calibration faults list |

**Leakage test (typical)**: hold position under defined force with valve at null, measure position drift or flow;
compare with OEM limit.

## Loopers (FM)
Hydraulic looper arms between stands lift the strip to keep tension. Cylinder in force (tension) control with position
limits. HMI: looper position OS/DS (mm / angle), PS / RS pressures, servo %, strip tension (N/mm²), strip force,
LP tare (weight of the looper roll), strip weight / bending compensation.
- Tension set too high → necking, strip break; too low → loops, cobbles.
- Looper hunting → servo, friction, speed control interaction, wrong tare.

## Work-roll bending / balancing
Cylinders in the chocks push WR apart (positive bending) or together; pressure-controlled via proportional or servo
valves. Bending force shown in MN per side. Asymmetric force → flatness problems / camber.

## Side guides
Hydraulic cylinders with position control (set-up, ref, act) and force limitation (SG force OS/DS); faults: position
deviation, sticky guides, worn liners.

## Wrapper rolls (down coilers)
Position / force control with fast servo valves, step control lifting rolls as the strip head passes; calibration
values (Cal. Val.) and P-Cal per roll. Faults: wrong gap vs thickness, slow response, calibration drift.

## Servo valve care
- Keep oil ISO 4406 ≤ 15/13/10 (servo), change pilot filters, flush after any opening of the system.
- Null adjustment only per OEM; check electrical command / feedback before replacing a valve.
- Replace with flushing plate when the system is opened; never run servo valves on unflushed lines.

Safety: HGC and loopers hold huge forces and accumulators store energy: LOTO, block the stand, discharge accumulators,
check zero pressure with gauges before opening any line.
