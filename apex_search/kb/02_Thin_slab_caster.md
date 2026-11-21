# Thin slab caster for ESP (Apex built-in expert note)

Topic: casting, continuous caster, thin slab, mould, oscillation, SEN, breakout, segments, soft reduction, liquid core.

## Main equipment
Ladle turret → ladle shroud → tundish (stopper rod, tundish weight) → submerged entry nozzle (SEN) → funnel-shaped
copper mould with oscillator → strand guide / segments (secondary cooling sprays, roll gap control) → bending /
straightening → withdrawal → transfer to HRM (in ESP no cut-off torch: the strand goes straight into R1).

## Key parameters (typical, check plant values)
| Parameter | Typical | Note |
|---|---|---|
| Casting speed | 4–7 m/min | sets mass flow of the whole ESP line |
| Slab thickness at mould | 90–140 mm (after liquid core reduction) | |
| Oscillation frequency | rises with speed (e.g. 4–6 Hz at 5 m/min) | negative strip time keeps the shell from sticking |
| Tundish superheat | 15–35 °C above liquidus | too high → breakout risk / centre segregation; too low → freezing / clogging |
| Mould level | ± 2–3 mm control band | level fluctuation → surface defects, breakouts |
| Strand withdrawal force | stable trend | rising force = sticking, bulging, segment issue |

Liquidus (empirical): Tl ≈ 1536 − (78 C + 7.6 Si + 4.9 Mn + 34.4 P + 38 S + 4.7 Cu + 3.1 Ni + 1.3 Cr + 3.6 Al) °C.

## HMI (Primetals ESP "Caster" screen)
Speed actual / setpoint, total force, ramp; oscillator frequency, ready / running; tracking (strand head, end of cast,
dummy bar); To Caster / From Caster handshake lamps (HRM loaded, running, run request, ready for cast / CCM linked,
ladle open, casting active, clear machine, dummy bar inserted, roll-gap check); rolling sequence (slab IDs, bar &
strip thickness, Endless / Batch); ladle and tundish weights; steel grade.

## Common problems
| Problem | Likely causes | Checks / actions |
|---|---|---|
| Sticker / breakout alarm | mould powder lubrication, oscillation fault, level fluctuation, high speed | mould thermocouple pattern, oscillator status, slow down per procedure |
| Mould level fluctuation | SEN clogging (Al2O3), stopper wear, argon, bulging | stopper position trend, argon flow / pressure, SEN change |
| Longitudinal cracks | uneven shell, mould taper, powder, high C-peritectic grade | heat-flux symmetry, powder, speed |
| Transverse / corner cracks | straightening in 700–900 °C ductility trough, high Al/N/Nb | secondary cooling, strand temperature at straightener |
| Centre segregation | high superheat, no / wrong soft reduction | superheat, soft-reduction position |
| Bulging, high withdrawal force | segment roll gap, cooling, worn rolls | roll-gap check mode, cooling flow, segment change |
| Casting speed limited by mill | mill not ready, plate mode | HRM ready signals on the Caster screen |

## Interaction with the mill (ESP specific)
- Speed changes at the caster change bar and strip speed instantly (mass flow).
- 'HRM run request' / 'Ready for cast' must be true for the caster to cast into the mill.
- At end of cast / ladle change the tundish weight drops; speed may be reduced — the mill set-up follows.

Safety: liquid steel, breakouts, steam explosions with water, tundish / ladle handling, radioactive level gauges.
