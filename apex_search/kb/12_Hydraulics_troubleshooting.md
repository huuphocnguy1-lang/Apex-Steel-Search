# Hydraulic troubleshooting guide (Apex built-in expert note)

Topic: hydraulic troubleshooting, pressure drop, overheating, noise, cavitation, leakage, contamination, ISO 4406,
flushing, filter, accumulator, pump, valve sticking, cylinder drift, hydraulic power unit, HPU.

## Method
1. Define the symptom (which actuator, which movement, since when, after what change).
2. Read the schematic: follow P → valve → actuator → T for that function; list every component in the path.
3. Measure, do not guess: pressure gauges at test points (Minimess), flow, temperature, electrical command and
   feedback of valves, transducer values on the HMI.
4. Split the circuit: is it the supply (HPU), the valve, or the actuator?
5. Fix the root cause, flush if contamination, document as a lesson learned.

## Symptom → causes table
| Symptom | Likely causes (most likely first) | Checks |
|---|---|---|
| No pressure / low pressure | pump not running / worn, relief valve open or set low, compensator setting, big internal leak, wrong valve energised | pump current & noise, relief setting, case drain flow, isolate branches |
| Pressure dips during movement | accumulator pre-charge low, pump too small, filter blocked | pre-charge, ΔP filter indicator |
| Actuator does not move | valve not energised (coil, PLC output, interlock), spool stuck (dirt), mechanical block, check valve | coil voltage / current, manual override, pressure at A/B |
| Slow movement | low flow, throttle setting, internal leakage, cold oil | flow, temperature, cylinder by-pass test |
| Cylinder drifts / does not hold | internal leakage (seals), valve leakage, pilot check valve dirty, servo null | load-holding test, close isolation valve |
| Jerky / chattering | air in oil, stick-slip (seals, guides), unstable pressure control, low pilot pressure | bleed, oil foam, pilot pressure |
| Overheating (> 60 °C) | relief valve blowing off continuously, cooler (water flow, fouling), internal leakage, high ambient | thermal camera on relief valve, cooler ΔT |
| Noisy pump | cavitation (suction strainer, low tank level, cold oil, suction valve closed), aeration (air leak at suction), worn pump | inlet vacuum, oil foam, tank level |
| Foaming oil | air ingress at suction, return line above oil level, water contamination | suction joints, return pipes |
| Milky oil | water ingress (cooler leak, condensation) | water ppm test, cooler pressure test |
| Frequent servo faults | contamination, null shift, electrical noise | ISO 4406 particle count, pilot filter |
| External leakage | fittings, hoses, seals | tighten / replace, check vibration & clamps |

## Cleanliness targets (ISO 4406, typical)
| System | Target |
|---|---|
| Servo valves (HGC, loopers, wrapper rolls) | 15/13/10 or better |
| Proportional valves | 16/14/11 |
| Directional valves, gear pumps | 18/16/13 |
| New oil from the drum | often 20/18/15 → always filter before filling |
Use offline filtration (kidney loop), β-rated filters (β ≥ 200), breathers with desiccant, change elements by ΔP.

## Flushing after repairs or new piping
Turbulent flow (Re > 4000, typically flushing velocity 2–3 × normal), by-pass sensitive valves with flushing plates,
heat the oil to 40–50 °C, flush until the target ISO code is reached on 2 consecutive samples.

## Accumulator check
Depressurise the oil side, check N2 pre-charge with the charging kit, refill with nitrogen only (never oxygen / air).
Bladder failure signs: no pre-charge, oil at the gas valve.

## Safety (always)
- LOTO electrical and hydraulic, discharge accumulators, check zero pressure with a gauge.
- Block suspended loads and stands (gravity can move cylinders when pressure is removed).
- Never search leaks with the hand (injection injury), wear eye protection.
- Hot oil and hot surfaces.
