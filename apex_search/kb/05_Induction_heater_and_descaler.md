# Induction heater (IDH), edge heater (EDH), rotary shear (SHR) and descaler (DSC) (Apex built-in expert note)

Topic: induction heating, IDH, inductors, converters, edge heater, rotary crop shear, descaling, scale.

## Induction heater
Between HRM and FM the bar cools; the IDH (a row of inductor coils fed by medium-frequency converters, several MW in
total) re-heats it to the FM entry temperature. The bar passes inside the coils; eddy currents heat it.
- Power distribution follows temperature target, bar thickness and speed.
- HMI values: IDH entry / exit temperature (pyrometers), number of running converters, power (MW), pinch rolls of the
  heater, inductor cooling water.
- Coil-mode permissives include "IDH entry strip temperature high enough", "IDH entry strip thin enough" and
  "at least N running converters".
- Inductors can be moved / lifted for maintenance; the line has a cooling-water system "FM induction heater CA / CC"
  on the Media screen.

| Problem | Likely causes | Checks |
|---|---|---|
| Exit temperature low | converter(s) tripped, low entry temp, high speed, pyrometer dirty | converter status, power, pyrometer windows |
| Converter trip | cooling water flow / conductivity / temperature, earth fault, overcurrent | cooling station, converter fault log |
| Temperature non-uniform (head/tail, edges) | speed change, edge cooling | edge heater, speed profile |
| Bar touching inductor | bar shape (camber, head up), guide rollers | HRM shape, guides |

## Edge heater (EDH)
Heats the bar edges which cool faster (avoids edge cracks and helps FM edge quality); power shown as EDH MW.

## Rotary crop shear (SHR)
Drum shear before the heater; crops head / tail or makes emergency cuts in batch mode; has its own pinch roll and side
guides ('Rot. Shear PR & SGN'). Tracking reset button "SHR Track. Reset".

## Descaler (DSC)
High-pressure water headers (≈ 200–400 bar) before F1 remove the secondary scale. Problems: nozzle clogging, low
pressure (pump, accumulator, leak), header valve not opening → rolled-in scale defects. Media screen: "FM Descaler".

Safety: high voltage / medium frequency converters, strong magnetic fields at inductors (pacemakers!), high-pressure
water jets.
