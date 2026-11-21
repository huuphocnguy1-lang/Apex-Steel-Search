# Industrial hydraulics fundamentals for steel plants (Apex built-in expert note)

Topic: hydraulics, ISO 1219 symbols, pumps, valves, servo valve, proportional valve, accumulator, cylinder, formulas.

## Formulas (SI)
| Quantity | Formula | Handy units |
|---|---|---|
| Cylinder force | F = p × A | F[kN] = p[bar] × A[cm²] / 100 |
| Piston area | A = π d² / 4 | d = 200 mm → 314 cm² |
| Annulus (rod side) area | A = π (D² − d²) / 4 | |
| Cylinder speed | v = Q / A | v[m/s] = Q[L/min] / (6 × A[cm²]) |
| Flow for a speed | Q = v × A | Q[L/min] = 6 × v[m/s] × A[cm²] |
| Hydraulic power | P = p × Q | P[kW] = p[bar] × Q[L/min] / 600 |
| Pump drive power | P / η | η total ≈ 0.85–0.9 |
| Pump flow | Q = V × n × ηv | V[cm³/rev] × n[rpm] / 1000 = L/min |
| Accumulator (isothermal) | p0·V0 = p1·V1 = p2·V2 | usable ΔV = V0·p0·(1/p1 − 1/p2) (absolute pressures!) |
| Orifice / valve flow | Q ∝ √Δp | servo valve: Q = Qn · x · √(Δp / Δpn) |

## Pumps
Fixed displacement (gear, vane) with relief valve; variable displacement axial piston with pressure compensator /
load sensing (most mill systems: constant pressure e.g. 210–280 bar with accumulators). Typical faults: cavitation
(noise, low inlet pressure, clogged suction strainer, cold oil), worn pump (case drain flow high, slow build-up),
compensator setting drift.

## Valves
- **Directional** (solenoid, pilot-operated), **pressure** (relief, reducing, sequence, counterbalance),
  **flow** (throttle, flow control), **check / pilot-operated check** (load holding), **cartridge (logic) valves**.
- **Proportional valves**: spool position proportional to current/command, with or without on-board electronics.
- **Servo valves** (nozzle-flapper or direct drive): very fast, precise; used for HGC, loopers, side guides, wrapper
  rolls. Need very clean oil (ISO 4406 ≤ 16/14/11, better 15/13/10). 'Null' = command where the spool is centred
  (no flow); null shift causes drift.

## Accumulators
Bladder / piston type, nitrogen pre-charge p0 typically ≈ 0.9 × minimum working pressure (for energy storage).
Check pre-charge regularly with the oil side depressurised. Low pre-charge → small usable volume, pressure dips
during fast movements. **Stored energy: always discharge before work.**

## Cylinders
Differential cylinders (piston / rod side), position transducers (magnetostrictive inside the rod, e.g. Temposonics),
pressure transducers PS / RS to calculate force: F = pPS·APS − pRS·ARS. Faults: internal leakage (seal by-pass),
external leakage, rod scoring, transducer faults.

## Oil
Mineral oil HLP 46 / HLP 68 (or fire-resistant HFC / HFD near hot zones). Working temperature 40–55 °C. Viscosity too
low (hot) → leakage, wear; too high (cold) → cavitation, sluggish response. Water content < 0.05 % (500 ppm) for
mineral oil. Cleanliness per ISO 4406 (code for ≥4 / ≥6 / ≥14 µm particles per mL).

## ISO 1219 symbol reading (quick guide)
Square boxes = valve positions (number of boxes = number of positions); arrows in boxes = flow paths; T = blocked
port; spring on the side = return position; zig-zag = spring; triangle filled = hydraulic (open = pneumatic);
circle with filled triangle pointing out = pump, pointing in = motor; dashed line = pilot / drain; capsule shape =
accumulator; diamond = filter / cooler / heater (with symbols inside). Ports: P pressure, T tank, A/B work ports,
X/Y pilot / drain, L leakage.
