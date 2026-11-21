# Pendulum shear (PS / SHP), pusher and piler (Apex built-in expert note)

Topic: pendulum shear, pendular shear, PS, SHP, plate mode, plate piling, pusher, piler, cut length, knife, overload.

## Role in ESP
After the HRM the pendulum shear can cut the transfer bar while it moves:
- at **start of casting** and when the finishing mill is not ready: plates are cut and removed by the
  **pusher / piler** (plate mode) so the caster can keep casting;
- in **batch mode**: bar cut into lengths for single-coil rolling;
- for **emergency / cobble** cuts and **tail-out** cuts at end of cast;
- in **endless (coil) mode** it stays idle but ready ('Pendulum Shear Cut active' permissive).

## Main parts
Eccentric-driven knife frame swinging with the bar (pendulum motion so the cut is square at bar speed); top and
bottom knives; main drive (DRV) with encoder (absolute and motor encoder); hydraulic **balancing** (DS / OS
transducers) and **swivelling** frame cylinders; knife cooling; overload protection (OVL); safety valves;
pinch rolls before / after (PREn / PREx); side guides; hoods (entry / exit) ; pusher (slab lift / lower and travel
to roller table or discharge table) and piler (lift / lower, plate counter).

## HMI "Overview Pendulum Shear / Pusher and Piler"
- Pusher / Piler status: Ready, Check valves, Man. Interv., Maintenance; positions Ref / Act.
- Plate piling mode sequence: PPM step number, plate counter.
- Tailout cut: tailout length, last slab, cut rule.
- Coil-mode permissives (✓ list): FM ready, IDH entry temperature high enough, IDH entry strip thin enough,
  pendulum shear cut active, IDH ≥ 6 running converters, same strip under HRMEn LB ↔ SHP, coiler simulation mode,
  casting speed high enough.
- Shear status: Ready, Frame, Cut cycle, Maintenance, Swiv M, OLV M, Safety valves, Knife cooling, Auto Cut, encoder
  selection.
- Overload: top / bottom knife position, overload force.
- Balancing / swivelling: DS/OS transducer values, frame positions and forces.
- Slab cut length: last / next cut length; cut selection Man Cut / Plate Mode / Auto Cut; length past shear.

## Cut length
Cut length = bar speed × time between cuts; the shear needs the bar speed (from pinch rolls / tracking) and the
encoder angle. Wrong cut length → check speed source, tracking (MTR), encoder, slip of measuring roll.

## Typical problems
| Symptom | Likely causes | Checks / actions |
|---|---|---|
| No cut / cut cycle not started | permissive missing, shear not 'Ready', encoder fault, safety valves | permissive list, alarm line, encoder status |
| Incomplete cut / bar not separated | knife clearance too big, worn / chipped knives, cold or thick bar, low drive torque | knife gap, knife condition, bar temperature, drive current |
| Overload trip (OVL) | bar too thick / cold, wrong timing, knife collision | overload force, cut angle, bar thickness |
| Cut not square / bent plate | swivel / balancing pressure wrong, timing vs speed | balancing pressures, frame positions, speed sync |
| Wrong plate length | speed measurement, tracking error | MTR / Mat. Track, measuring roll |
| Piler fault | lift position, check valves, roller table / discharge table position | positions Ref / Act, limit switches, hydraulics |
| Knife overheating | knife cooling off | cooling flow |

Safety: the shear can move suddenly; isolate drive and hydraulics, block the frame, release accumulator pressure
before working on knives (OEM knife-change procedure, 'Knife change enable').
