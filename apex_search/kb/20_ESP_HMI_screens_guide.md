# ESP plant HMI screens guide – Primetals / Sancess operator screens (Apex built-in expert note)

Topic: HMI, operator screens, WinCC, buttons, alarm line, navigation, HRM Mode, FM Mode, Technol., Mat. Track., roll change, calibration.
Source: photos of the ESP line operator station (13–14 Oct 2026). '(likely)' = meaning deduced from the label.

## Common screen frame

### Area status / navigation bar
- **MES**: Link to the plant MES / Level-2 system for that line section (one MES button per section).
- **DC3 · DC2 · DC1**: Down coilers 3, 2, 1.
- **ROT**: Run-out table (roller table after the finishing mill).
- **HSS**: High-speed shear (flying shear that cuts between coils in endless mode).
- **LCS**: Laminar cooling system on the run-out table (likely).
- **F5 … F1**: Finishing-mill stands.
- **DSC**: Descaler (high-pressure water) before the finishing mill.
- **IDH**: Induction heater between roughing and finishing mill.
- **SHR**: Rotary shear (crop shear before the induction heater).
- **SHP**: Pendulum shear (cuts the bar after the roughing mill / for plate piling).
- **R4 … R1**: Roughing-mill (HRM) stands.
- **ENT**: HRM entry (between caster and R1).

### Navigation colours
- **Green button**: Section ready / no fault.
- **Blue  !  in front**: Attention: section not ready or a condition missing — open it to see why.
- **Click on a button**: Opens the screen of that section (likely).

### Alarm line
- **Time stamp**: Time of the newest message (e.g. 16:05:49.911).
- **Message source**: PLC block that raised it (e.g. HS_P02_COOL_LOG/COOL_MSG = cooling logic).
- **Message text**: What happened (e.g. 'SHF Side Spray Valve not opened'). Red = alarm, yellow = warning / information.
- **Right field**: Newest message of the selected area (e.g. 'COC C1 cooling', 'Coil mode').
- **List icon (left)**: Opens the message / alarm list.
- **Triangle icon**: Acknowledge messages (likely).
- **✓  and  wrench**: ✓ = system OK; wrench = maintenance / service mode.
- **User field (e.g. OHIO)**: Logged-in user / operator group.

### Left screen menu and alarm flags
- **Home**: Start screen.
- **Technol.**: Technology overview of the whole ESP line.
- **Caster**: Caster strand overview.
- **HRM Mode**: Roughing-mill operating screen.
- **FM Mode**: Finishing-mill operating screen.
- **Mat. Track.**: Material tracking.
- **Cool. L1**: Laminar cooling.
- **HSS Mode**: High-speed shear.
- **DC Mode**: Down coilers.
- **Diag.**: Diagnostics, communication, E-stops, safety.
- **HRM / FM / DC CSM**: Central switching & monitoring (MCC feeders, drives) per area.
- **Media**: Hydraulics, lubrication, cooling water systems.
- **HRM RCH / FM RCH**: Roll change of the roughing / finishing mill.
- **Safety**: Safety overview.
- **▼ under each button**: Drop-down list of the sub-screens of that area.
- **AH (red)**: Alarm high in that area, not yet acknowledged.
- **AH (black)**: Alarm high, already acknowledged but still active.
- **WH (yellow)**: Warning high in that area.
- **S**: System / process-control message in that area (likely).

### Bottom toolbar
- **›  (arrow)**: Open / close the extra tool panel (likely).
- **Key**: Log in / log out, change user rights.
- **Calendar-clock**: Message archive / alarm history (likely).
- **Screen with magnifier**: Screen selection / search a picture (likely).
- **L2 database**: Level-2 data (set-ups, coil data) (likely).
- **Report sheet**: Reports / shift log (likely).
- **◀ ▲ ▼ ▶**: Navigate to the previous / upper / lower / next screen in the hierarchy.
- **Curved arrow ↶ / ↷**: Back / forward to the last screens opened.
- **Screen → monitor**: Move the picture to another monitor (likely).
- **3 window-layout icons**: Load / save / delete a screen composition (likely).
- **Window with X**: Close all extra windows.
- **Magnifier on page**: Find a tag / signal (likely).
- **Camera**: Hard-copy (screenshot).
- **Printer**: Print the screen.
- **?**: Help for the current screen.
- **Speaker**: Silence the alarm horn.
- **✓✓ (bottom-right of a screen)**: Close / confirm this pop-up screen (likely).

### Value colours
- **White field**: Actual (measured) value.
- **Light-blue field**: Reference used by Level-1 (likely).
- **Dark-blue field**: Set-point from Level-2 / next coil (likely).
- **Yellow field**: Value out of tolerance / warning.
- **Green label**: Function ON / ready (e.g. READY, ROLLING, SYNC UP).
- **Blue label**: Mode or selection active (e.g. Pendulum, Rotary, MAN).
- **Pink / magenta label**: Not ready / manual / maintenance (e.g. 'Manual Not Ready', 'No Start Condition').

### Mimic symbols
- **HGC**: Hydraulic gap control (stand position).
- **WRB**: Work-roll bending.
- **WRS**: Work-roll shifting.
- **PR**: Pinch roll.
- **THC**: Thickness control (likely).
- **PRC**: Profile control (likely).
- **MTC**: Mass-flow / tension control (likely).
- **LDR / PIL**: Loader / piler of the pusher-piler.
- **RCH**: Stand in roll-change mode.
- **ROLLING / SYNC UP / SYNC DN**: Stand rolling / speed synchronising up / down.
- **T**: Temperature measuring point (pyrometer).
- **ITC R1/R2 …**: Interstand tension between two stands.

## Area: Caster

### Screen: Caster – Strand Overview
What it shows: Casting speed set/actual, oscillator (frequency, ready/running), strand head and dummy-bar tracking, cut length, and the rolling sequence of the next slabs/coils (ID, thickness, width, Endless/Batch).
Use it for: Check the caster is running and synchronised with the mill; see which coils are coming next.

Buttons:
- **Cut Mode**: Shows / selects the cutting mode of the strand.
- **Rolling Sequence list**: Next coils: ID, thickness, width, Endless / Batch.
- **Green arrows on the segments**: Segment status (roll gap / drive) along the strand.

Fields (value seen on the photo):
- **Actual / Setpoint speed**: Casting speed measured / requested (photo: 5.1 / 5.1 m/min)
- **Total Force**: Withdrawal force on the strand (photo: 506 kN)
- **Actual ramp / Setpoint ramped**: Speed change rate and ramped target (photo: +0.5 / 5.1 m/min)
- **Oscillator frequency**: Mould oscillation (rises with casting speed) (photo: 5.4 Hz)
- **Strand head tracking**: Length cast since the start of the sequence (photo: 1769.7 m)
- **To Caster (lamps)**: HRM loaded / running / run request / ready for cast — HRM side signals sent to the caster (photo: all green except Hold speed)
- **From Caster (lamps)**: CCM linked, ladle open, casting active, clear machine, dummy bar inserted, roll-gap check (photo: linked, ladle open, casting)
- **Unit status block**: LCS, ROT, HSS, DC1–3, F1–F5, SHP, SHR, IDH, DSC, Entry, R1–R4, Media: green = ready (photo: DC2 blue (selected / not ready))
- **Coil Mode**: Line runs in endless coil mode (photo: active)
- **Rolling Sequence 1–16**: Next slabs: ID, slab thickness (h-bar), strip thickness, Endless/Batch. Dark blue = in mill, green = current, red = in caster (photo: 12–14 mm bar → 1.775 mm strip)
- **Tundish / ladle weight**: Steel left in ladle / tundish (photo: 191.4 t / 64.6 t)
- **Steel Grade**: Grade of the running heat (photo: ZE1001 Low Carbon)

How it works: In ESP the caster and the mill are one line: the casting speed sets the mass flow for the whole mill. The 'To Caster / From Caster' lamps are the handshake between caster and roughing mill — the caster is only allowed to cast into the mill when HRM is loaded, running and ready.

What to check:
- Casting speed and Setpoint equal; ramp 0 in steady state.
- Total force stable — a rising force can mean strand sticking or segment problem.
- All unit blocks green before 'Ready for cast'; a blue/grey block shows which unit stops the start.
- Ladle / tundish weight to plan the next ladle change.

### Screen: Caster – Strand Overview (next day, 14 Oct)
What it shows: Same screen on 14 Oct with a different sequence (Batch / Endless coils, 3.485–4.000 mm) and a SG-FM301R F1 WRC error in the alarm line.
Use it for: Compare with the previous page: different production state and an active F1 work-roll-cooling alarm.

Buttons:
- **Same buttons as the previous Caster page**: —

Fields (value seen on the photo):
- **Actual speed**: Casting speed (photo: 4.3 m/min)
- **Total force**: Withdrawal force (photo: 455 kN)
- **Oscillator**: Frequency (photo: 4.3 Hz)
- **Strand head tracking**: Length cast (photo: 2211.1 m)
- **Rolling sequence**: Mixed Batch / Endless coils, 17–18 mm bar → 3.485–4.000 mm strip (photo: —)
- **Alarm line**: SG-FM301R F1 WRC — Error (F1 work-roll cooling, side guide FM301R) (photo: red)

How it works: Same screen one day later: lower casting speed for thicker strip (3.5–4 mm) and a batch coil in the sequence.

What to check:
- Compare speed / force with the previous day for the same grade.
- Clear the F1 WRC error (work-roll cooling) before it stops the mill.

## Area: HRM – Roughing Mill (R1–R4)

### Screen: HRM – Stand Function Overview
What it shows: Menu of HRM stand functions: interstand tension, AGC, ASC, bending, shifting.
Use it for: Entry point to switch individual technological functions of the roughing stands on/off.

Buttons:
- **Interstand Tension**: Switch the interstand tension control on / off.
- **AGC**: Automatic gauge (thickness) control.
- **ASC**: Automatic shape (flatness) control (likely).
- **Bending**: Work-roll bending control.
- **Shifting**: Work-roll shifting control.

Fields (value seen on the photo):
- **Interstand Tension**: Tension control between stands (looper-less in HRM) (photo: button)
- **AGC**: Automatic gauge control — keeps thickness (photo: button)
- **ASC**: Automatic shape control (likely) (photo: button)
- **Bending / Shifting**: Work-roll bending and shifting controls (photo: button)

How it works: Overview page: each button opens the detail of that technological function for R1–R4, where it can be switched on/off and its status read.

What to check:
- If thickness is out of tolerance: check AGC is ON for all stands.
- If shape / centre-line is bad: check bending and ASC status.

### Screen: HRM Mode – Line Overview (R1–R4)
What it shows: Mimic of the roughing area with bar thickness/width, speed, IDH entry/exit and shear temperatures, stand status (ROLLING / SYNC UP), roll force, bending, shifting, gap, roll cooling and centre-line deviation trend.
Use it for: Main operating screen of the HRM: one look at all four stands and the bar coming from the caster.

Buttons:
- **Ghost Selection**: Run the mill 'empty' with a virtual strand (test without material) (likely).
- **Mill Master**: Choose the master stand for the speed cascade (likely).
- **Stand Mode**: Set each stand: rolling / dummy / out of line.
- **Local Panels**: Enable / disable the local operator panels.
- **Release Drives**: Release (enable) the main and auxiliary drives.
- **Jogging Selection**: Select equipment for slow jogging (inching).
- **CRS Unit**: Crop / rotary-shear unit (likely).
- **Rot. Shear PR & SGN**: Rotary-shear pinch roll and side guides.
- **Pusher / Piler**: Open the pusher / piler screen.
- **Pendulum Shear**: Open the pendulum-shear screen.
- **Monitor Controls**: Thickness / tension monitor controls (likely).
- **HGC Man Gap**: Set the stand gap manually.
- **Stand Controls**: Technological controls of the stands (AGC, bending, shifting).
- **Stand Cooling**: Work-roll cooling on / off.
- **HRM Entry**: Entry equipment between caster and R1.
- **Edge Heater**: Edge heater before the induction heater.
- **Toggle Screen**: Switch between the two views of this screen.

Fields (value seen on the photo):
- **Strip Thick. / Speed**: Final strip thickness (act / ref / L2) and line speed (photo: 1.78 mm · 0.94 m/s)
- **Bar Thick. / Bar Width**: Bar after the HRM (photo: 12.0 mm · 1267 mm)
- **IDH Exit / Entry**: Temperatures before and after the induction heater (photo: 1036–1040 °C / 951–929 °C)
- **Shear**: Temperature at the rotary / pendulum shear (photo: 989 °C)
- **R4 Exit**: Temperature after R4 (yellow = warning) (photo: 1022 / 1006 °C)
- **HRM / FM READY**: Both mills ready (photo: green)
- **RCH R4–R1**: Roll-change status per stand (photo: RCH)
- **Slab Thick. / Width**: Slab from the caster (photo: 135 mm · 1252 mm)
- **SG / PR / TRC**: Side-guide opening, pinch-roll gap, tracking positions (photo: 1281 mm · 12 mm)
- **Stand table (R4–R1)**: Bending, shifting, roll force, current, speed, gap, tilt, roll cooling, tension (photo: R4: 17.3 MN, gap 10.7 mm)
- **Trends**: HRM exit centre-line deviation (4.4 mm) and interstand tensions ITC R1/R2 … R3/R4 (photo: —)
- **Ladle / Tundish**: Weights (photo: 190.8 / 64.7 t)

How it works: This is the operating screen of the roughing mill. The mimic follows the bar from the caster (right) through R1→R4, the rotary / pendulum shear, edge heater and induction heater to the FM (left). Each stand shows its controls (HGC, WRB, WRS) and status (ROLLING / SYNC UP).

What to check:
- Centre-line deviation small (< ± 10 mm) — otherwise check side guides / tilt.
- Roll force of each stand inside its normal range; big DS/OS difference → tilt.
- Yellow fields (e.g. R4 exit temperature) = out of tolerance.
- Tension trend stable; spikes = speed mismatch between stands.

### Screen: HRM – Bar Graph
What it shows: Per stand R1–R4: HGC position and gap (ref/act/tilt), speed, roll force, thickness deviation, temperature, WRS and tension as bar graphs.
Use it for: Spot quickly a stand that is out of target (tilt, force imbalance, speed).

Buttons:
- **No buttons**: Display only: per-stand bar graphs, values and trends.

Fields (value seen on the photo):
- **HGC Ref / Act / Tilt**: Hydraulic cylinder position and DS-OS difference (photo: R4 10.7 / 10.7 / -0.4 mm)
- **Gap Ref / Act**: Roll gap (photo: R4 12.2 / 11.2 mm)
- **Reduction**: Thickness reduction per stand (photo: R4 41.9 % · R1 49 %)
- **Speed**: Stand speed (set / act) (photo: 0.15 – 0.85 m/s)
- **Rollforce**: Roll force per stand (photo: 13–17 MN)
- **Thick. Dev.**: Thickness deviation (photo: 7.1)
- **Temp.**: Rotary shear / R1 (photo: 986 / 1035 °C)
- **Current**: Main-drive current (photo: 25–36 %)
- **Workroll Bending**: Bending force (photo: 3.3–3.6 MN)
- **HRM / FM exit**: Centre-line, crown C25/C40, wedge C25/C40 (photo: CL 4.47 mm, crown 62 µm)
- **Tension Roll Force**: Tension rolls OS / DS (photo: 65 / 68 kN)

How it works: Same data as HRM Mode but as bar graphs: ideal for comparing the four stands at a glance. Crown and wedge are measured by the profile gauges at HRM and FM exit.

What to check:
- Tilt close to 0 on every stand; wedge (C25/C40) near 0 µm — else adjust tilt.
- Reduction distribution as planned by Level 2.
- Currents well below 100 % — high current = overload risk.

### Screen: HRM – Roll Change Overview (RCH)
What it shows: Status of R1–R4 roll change: rolling/automatic mode, start conditions, top BUR/WR diameters, remove/insert sequence, reference and actual positions.
Use it for: Prepare and follow a roughing-mill roll change; check roll diameters entered.

Buttons:
- **Remove Sequence (per stand)**: Start the automatic roll removal.
- **Insert Sequence (per stand)**: Start the automatic roll insertion.
- **Motor symbol (red M)**: Drive of the roll-change car; red = not running.
- **Ref. / Act. Position, Ref. Speed**: Target and real position / speed of the roll-change car.
- **✓ / ✗**: Confirm / cancel the entry.

Fields (value seen on the photo):
- **Mode lamps**: Rolling Mode · Automatic Mode · Automatic Stopped · No Start Condition · Locked (photo: Rolling, Auto stopped)
- **Top/Bottom BUR, WR**: Diameters of back-up and work rolls in the stand (photo: BUR 1.435–1.441 m, WR 0.705–0.763 m)
- **Overview Stand Rx**: Opens the stand roll-change detail (photo: button)
- **Rolling / Roll Change**: Select stand mode (photo: buttons)
- **Remove / Insert Sequence**: Start the automatic sequence (photo: buttons)
- **Ref / Act position, Ref speed**: Roll-change car (photo: 18670 mm · 0 %)

How it works: Select 'Roll Change' for the stand, then run Remove Sequence (old rolls out) and Insert Sequence (new rolls in). 'No Start Condition' (pink) means a permissive is missing — open Overview Stand to see which.

What to check:
- Enter the new roll diameters correctly — they are used for speed and gap set-up.
- Mode must show 'Automatic Mode' and no pink lamp before starting a sequence.
- Act position = Ref position before you start.

### Screen: HRM – R1 Roll Change
What it shows: Step buttons for R1: remove/insert sequence, side-shift load/unload, rollset to millbay, limit switches, backup-roll change sequence.
Use it for: Run and monitor the individual roll-change steps of stand R1.

Buttons:
- **Remove / Insert Sequence**: Automatic roll removal / insertion for R1.
- **Side Shift Load / Unload**: Move the roll set on / off the side-shift table.
- **Rollset to Millbay**: Send the roll set to the mill bay.
- **Limit Switches 1 / 2**: Check the roll-change limit switches.
- **Backup Roll Change Sequence**: Back-up roll change steps.
- **F1 Mode · F3 Data Request · F5 Seq. Load · F6 Seq. Unload · F7 Seq. Remove · F8 Seq. Insert · F9 Roll Data**: Function keys: mode, ask roll data from Level-2, start each sequence, enter roll data.

Fields (value seen on the photo):
- **Sequence buttons + status boxes**: Remove, Insert, Side Shift Load/Unload, Rollset to Millbay, Rollset to Rollshop; the grey boxes on the right show the step progress (photo: —)
- **Side Shifter**: Side-shift car (blue = selected / moving) (photo: cyan)
- **Equipment list**: WR change tractor & hook, WR / BUR latches, top / bottom strippers, spindle carriers, wedge adjustment & clamping, ducking floor-plate, BUR change cylinder, BUR balancing & locking, main drive, screw-down, WR bending/balancing, stand cooling, exit tension roll (photo: —)
- **RCH Ready for Rolling**: All roll-change equipment back in rolling position (photo: green)
- **S12 / S13 / S14**: Pic. Up / Pic. Down / Apply (likely: select picture step, apply) (photo: buttons)
- **Mode lamps**: Rolling · Automatic · Automatic stopped · No start condition · Locked (photo: —)

How it works: Detail of the R1 roll change: each equipment item has its own status boxes; during the sequence they fill step by step. An AH flag next to an item shows which device has an alarm.

What to check:
- Item with alarm (AH) or not finished = where the sequence stopped.
- Before rolling: 'RCH Ready for Rolling' must be green.
- Latches (keepers) closed and strippers in position before starting the mill.

### Screen: HRM – R2 Calibration
What it shows: Calibration steps (check balancing, close gap, force taration, contact position…) with gap/force trend and calibration result values.
Use it for: Zero / calibrate the R2 gap after a roll change.

Buttons:
- **Step 1 … 8**: Check balancing → … → roll-force taration → go to contact → roll force 200 t → 500 t → RF 1000 t / zeroing → open gap. Blue = to do, green = active / done.
- **General Faults 1 / 2**: Faults that block the calibration.
- **CAL ■ ▶  ·  Sync**: Stop / start the calibration; Sync = synchronise DS and OS.
- **Modulus Test (HYS) ■ ▶**: Mill-modulus (stretch) test; option with oil-bearing test.
- **Calibration / Detail · R4 R3 R2 R1**: Change page and stand.

Fields (value seen on the photo):
- **Step 1–8**: Check balancing → prepare / close gap → roll-force taration → go to contact position → RF 200 t → RF 500 t → RF 1000 t / zeroing → open gap (photo: step 8 green)
- **General Faults 1 / 2**: Faults blocking calibration (photo: red)
- **Trend**: Gap [mm] and roll force [MN] during the calibration (photo: —)
- **Calibration Operations**: CAL start ▶ / stop ■, Sync, calibration time (photo: 119.5 s)
- **Modulus Test (HYS)**: Mill stretch test, optional with oil-bearing test (photo: —)
- **Gap: Average / Differ. position**: After calibration (photo: 36.0 mm / -0.3 mm)
- **Tabs**: Calibration / Detail · R4 R3 R2 R1 (photo: R2)

How it works: After a roll change the stand must be calibrated: the rolls are pressed together to a defined force, and the gap is set to zero at that force (zeroing). The modulus test measures the mill stretch used by AGC.

What to check:
- Run calibration after every roll change and when gap readings drift.
- DS-OS difference after calibration close to 0.
- If a step stays blue: check General Faults and balancing pressure.

### Screen: HRM – Main Drive R1
What it shows: Single-line of the R1 main drive from the 33 kV / 50 Hz supply: transformer, converter, motor, cooling, drive temperatures and general/control status.
Use it for: Check the R1 main drive is ready and healthy (power, cooling, temperatures).

Buttons:
- **Main Drive SHP · R4 · R3 · R2 · R1**: Choose which main drive to display.
- **General / Control**: Drive status and control mode.

Fields (value seen on the photo):
- **Single line**: 3AC 50 Hz 33 kV → transformer → converter → motor M; excitation 300 V breaker and control (photo: all ✓)
- **General**: Main drive status, manual intervention, mode (photo: ROLLING)
- **Control**: Auxiliary, Excitation breaker, Main drive (switch on / off) (photo: buttons)
- **Temperatures**: Stator, bearings DE/NDE, air in/out (photo: 47 °C stator, 30–36 °C)
- **Actual values**: Speed, current, torque (absolute and %) (photo: 92 rpm · 389 A · 96 kNm)
- **Fault / Warning**: Number of active faults / warnings (photo: 0 / 0)
- **Cooling unit, drive auxiliaries, active infeed**: Auxiliary systems (photo: green)

How it works: Switch-on order of a main drive: auxiliaries (cooling) → excitation breaker → main drive. The tabs at the bottom choose the drive (SHP, R4, R3, R2, R1).

What to check:
- Fault counter 0 before start.
- Temperatures rising → check cooling unit / air flow.
- Torque % vs. other stands to see load distribution.

### Screen: HRM – VVVF SHP Ex
What it shows: Single-line of the 420 V variable-frequency drives (HRM_SLM.01 …) feeding the auxiliary motors.
Use it for: Find which VVVF drive is off or faulted.

Buttons:
- **SYUP**: Supply ON (likely).

Fields (value seen on the photo):
- **AC 420 V supply**: Feeds HRM_SLM.01 / .02 smart line modules (photo: ✓ Vdc)
- **HRM DC busbar 01**: Common DC bus (photo: DC 570 V)
- **Inverters + motors**: PP plate discharge RT 1.1, 1.2, 2.1, 2.2 (pusher/piler roller tables) (photo: all ✓)
- **Temperatures**: Inverter / motor temperature (photo: 31–34 °C / 0 °C)
- **Device tags**: =1WI932FA19 … +1WI24B4AB22 (cabinet location) (photo: —)
- **Arrows**: Go to Rotary-shear roller tables / HRM entry-exit (photo: buttons)
- **SYUP**: Supply up / on (likely) (photo: green)

How it works: Variable-frequency drives on a common DC bus. Hover a drive: 'Inverter on / off' tooltip. The tag tells the cabinet where to find the drive.

What to check:
- Green tick on every inverter and motor.
- Use the device tag to find the cabinet when a drive is faulted.

### Screen: HRM – Central Switching & Monitoring (CSM)
What it shows: HRM MCC feeders, frequency-controlled drives and main drives with their on/off status.
Use it for: Electrical switching overview of the roughing area before start-up.

Buttons:
- **MCC Feeders**: Motor-control-centre feeders of the HRM.
- **Frequency Controlled Drives**: Variable-frequency drives.
- **Main Drives**: Main-drive switching.

Fields (value seen on the photo):
- **MCC Feeders**: HRM MCC feeder (photo: button)
- **Frequency Controlled Drives**: Roller tables, pumps… (photo: buttons)
- **Main Drives**: R1–R4 main drives (photo: buttons)

How it works: Electrical switching overview: open a group to switch it and see its state.

What to check:
- All groups green before start-up.

### Screen: HRM – MTR IBS (head/tail positions)
What it shows: Line mimic plus, for R1–R4, BasisID with head and tail position values per coil/value set.
Use it for: Check how the bar head/tail positions are tracked through the roughing stands.

Buttons:
- **No buttons**: Tables of head / tail position values per stand and order.

Fields (value seen on the photo):
- **HRM table (left)**: Per roller-table / stand: Vact, Vref (m/s) and operating mode (SYDN, ROLLING, SYUP) (photo: 0.09–6.00 m/s)
- **Stand blocks R4–R1, F1–F5, SHR, SHP, HSS, Caster**: Counter + BasisID with head and tail position for 4 values (photo: e.g. +7530 66.0 / 56.4)
- **Caster block**: 16 values (BasisID 7500–8300) (photo: counter 118)
- **Orders 1–16**: Order list with head / tail positions (photo: —)

How it works: MTR = material tracking. For each tracking zone the system keeps the head and tail position of every piece (BasisID). This screen is mainly for commissioning / diagnosis of tracking.

What to check:
- Vact = Vref in each zone; a mode SYUP/SYDN shows speed synchronisation.
- Head / tail positions must increase along the line — a stuck value = tracking error → see Mat. Track.

## Area: Shears, Heater & Piler

### Screen: Pendulum Shear / Pusher and Piler
What it shows: Pusher/piler status and plate-piling sequence, plate counter, pendulum-shear status (auto cut, encoder), cut length, balancing and the list of permissives (FM ready, IDH, coiler simulation, casting speed…).
Use it for: Check why the pendulum shear is not cutting / piler is not ready.

Buttons:
- **Plate Information**: Plate data.
- **Pusher/Piler Operations**: Pusher and piler commands.
- **Shear Operations**: Pendulum-shear commands.
- **Shear Encoder**: Encoder selection / status.
- **Plate Mode · Auto Cut**: Cutting mode of the shear.
- **Check Valves · Man. Interv. · Maintenance**: Pusher/piler status and intervention modes.

Fields (value seen on the photo):
- **Pusher / Piler status**: Ready, check valves, manual intervention, maintenance (photo: Ready)
- **Pusher (slab) lift / lower**: Ref / act position, lifted / lowered (photo: 0 mm)
- **Travers to RT / to DT**: Pusher travel to roller table / discharge table (photo: 5 / 1 mm)
- **Piler lift / lower**: Ref / act (photo: 349 / 349 mm)
- **Plate piling mode**: PPM step number, plate counter (photo: step 5 · 6 plates)
- **Tailout cut**: Tailout length, last slab, cut rule (photo: 0.0 m)
- **Coil mode → permissives**: FM ready, IDH entry temp high enough, IDH strip thin enough, shear cut active, IDH ≥ 6 converters, same strip HRMEn LB ↔ SHP, coiler simulation, casting speed high enough (photo: all ✓)
- **PREx / PREn, SG, speed**: Pinch-roll gaps exit/entry, side guide, speed (photo: 13.8 / 13.3 mm · 1271 mm · 0.53 m/s)
- **Pendulum shear status**: Ready, frame, cut cycle (✗), maintenance, swiv M, OLV M, safety valves, knife cooling (photo: cut cycle ✗)
- **Overload**: Top / bottom knife position, overload force (photo: -3340 / -3700 mm · 472 kN)
- **Balancing / Swivelling**: DS/OS trans., frame positions and forces (photo: 15 / 25 mm)
- **Slab cut length**: Last / next cut, cut selection (Man cut, Plate mode, Auto cut) (photo: 7.0 m)
- **Length past shear**: Strip length after the shear (photo: 39.5 m)

How it works: The pendulum shear cuts the bar after the HRM — for plates (pusher/piler) or for emergency / start cuts. In coil mode it may only stay idle when all permissives on the checklist are ✓.

What to check:
- A permissive without ✓ shows why coil mode / auto cut is blocked.
- Cut cycle ✗ = shear not in a cut cycle (normal in endless).
- Knife positions and overload force after a cobble / overload.

### Screen: HSS – High-Speed Shear Mode
What it shows: Strip data (width, thickness, HYP, temperature, tension), pinch rolls EX/EN (gap, OS/DS force), HSS drives (cam, drum, cut done), side guides and coiler temperatures; mode Endless.
Use it for: Follow the flying cut between coils in endless mode.

Buttons:
- **Toggle Screen**: Change view.
- **Ghost DC Selection**: Coiler test without strip (likely).
- **Operator Control**: Operator commands.
- **HSS Coiler Mode**: Coiler mode linked to the shear.
- **Cooling**: Cooling on the run-out table.
- **HSS Control**: High-speed-shear control.
- **Release HSS Drives**: Enable the shear drives.
- **Sideguides**: Side guides before the coilers.
- **Release RT Drives**: Enable the roller-table drives.
- **Local Panels**: Local operator panels.

Fields (value seen on the photo):
- **Strip data**: Strip-ID, width, thickness, customer thickness, HYP, temperature, tension (photo: 1264 mm · 1.77 mm · 550 °C)
- **Mode / Base-ID**: Endless; base ID (photo: Endless · 7430)
- **Selected shear**: Pendulum / Rotary / High speed (photo: High Speed)
- **Air pressure**: Shear air supply (photo: 6.70 bar)
- **Coiler temps C3/C2/C1**: Coiling temperature at each coiler (photo: 97 / 482 / 491 °C)
- **Pinch roll EX / EN**: Gap and OS/DS force (photo: 50 mm)
- **HSS drives**: Cam / drum angle, cut done counter (photo: 359° / 222° · 253 cuts)
- **SG EX / EN**: Side-guide opening and forces (photo: 1282 mm)
- **Strip speed / LAS / CL dev**: Line speed, laser number, centre-line deviation (photo: 6.26 m/s · 5 · -3.4 mm)
- **Coilers**: Counters and 'Ready' per coiler, C1–C3 strip lengths (photo: C1 994 / 1025 m)
- **Endless / FW Uncoupled**: Endless mode, fly-wheel uncoupled (photo: green)
- **Bar graphs**: Speeds / currents of DC, pinch rolls, HSS, RT cooling, LS (photo: —)

How it works: In endless rolling the strip never stops: the high-speed shear cuts it on the fly and the next coiler takes the new head. Cam/drum angle and 'cut done' follow every cut.

What to check:
- Mill Ready and coilers 'Ready' before the cut.
- Cut done counter increases at each coil change.
- Centre-line deviation small before the shear (risk of wrong cut / bad wrap).

### Screen: HSS – Detail 2 (lubrication)
What it shows: High-speed-shear lubrication flow per lube point, shear status and drive values.
Use it for: Check lube flow alarms on the high-speed shear.

Buttons:
- **Lube point list**: Each lubrication point of the shear with flow status.

Fields (value seen on the photo):
- **Lube points 8–21**: Bearing housings OS/DS, EN/EX, top/bottom, spray headers — ✓ = flow OK (photo: all ✓)
- **High speed shear**: Drum and cam: encoder angle, brake open, motors (photo: 16° / 359°)
- **Encoder reset**: Drum / Ecc encoder reset buttons (photo: —)
- **Last cut angle memory**: Eccentric / drum angle at the last cut (2 scans) (photo: 179.9 / 180.1°)
- **General status**: Automatic, maintenance, knife-change enable, fly-wheel uncoupled (photo: Automatic)
- **Coiler / Shear / RT drives**: Speed set / act of all drives around the shear (photo: ≈ 6.25 m/s)

How it works: Diagnosis of the high-speed shear: lubrication of every bearing, encoder angles and the speeds of all drives that must be synchronous at the cut.

What to check:
- Any lube point without ✓ → lubrication fault, stop before bearing damage.
- Last cut angle ≈ 180° (cut in the right position).
- All RT / pinch-roll speeds equal to strip speed.

## Area: FM – Finishing Mill (F1–F5)

### Screen: FM – Stand Function Overview
What it shows: Menu of FM stand functions: interstand tension, AGC, ASC, bending, shifting.
Use it for: Entry point to switch technological functions of the finishing stands.

Buttons:
- **Interstand Tension · AGC · ASC · Bending · Shifting**: Same as HRM, for F1–F5.

Fields (value seen on the photo):
- **Interstand Tension**: Tension control between stands (looper-less in HRM) (photo: button)
- **AGC**: Automatic gauge control — keeps thickness (photo: button)
- **ASC**: Automatic shape control (likely) (photo: button)
- **Bending / Shifting**: Work-roll bending and shifting controls (photo: button)

How it works: Same as HRM Stand Function Overview, for the finishing stands F1–F5.

What to check:
- AGC / bending / shifting ON for every stand during rolling.

### Screen: FM Mode – Line Overview (F1–F5)
What it shows: Mimic of the finishing mill with strip thickness/width, speed, temperatures, loopers, roll cooling, stand status and per-stand bending, shifting, force, speed, gap, cooling. (Picture taken with no strip in the mill.)
Use it for: Main operating screen of the FM.

Buttons:
- **Ghost Selection · Mill Master · Stand Mode · Local Panels · Release Drives · Jogging Selection**: Same as HRM Mode.
- **Monitor Controls · Stand Controls · Stand Cooling**: Same as HRM Mode, for F1–F5.
- **UTR**: FM function (not visible on the photo).
- **AUX Cooling**: Auxiliary / interstand strip cooling.
- **Side Guide**: FM side guides.
- **Descaler**: Descaler screen.
- **Ind. Heater Pinch Rolls**: Pinch rolls of the induction heater.
- **Induction Heater**: Induction-heater screen.
- **Toggle Screen**: Change view.

Fields (value seen on the photo):
- **Speed / Strip thick. / Strip width**: FM entry and exit values (photo: 0 (no strip))
- **Exit temperature / IDH entry & exit**: Temperatures (photo: —)
- **Stand status F1–F5**: RCH, ROLLING, SYNC UP; HRM / FM / Media READY (photo: ROLLING)
- **Loopers**: Looper between stands (L) (photo: —)
- **Stand table**: Bending, shifting, roll force, speed, thick/reduct., gap, tilt, basic / ADD cooling (photo: —)
- **FM exit centre-line**: Trend (photo: -3.4 mm)
- **Gear oil / LP / HP temps**: BO2, BO1, GO, LP, HP (photo: 41–45 °C)

How it works: Operating screen of the finishing mill — same layout as HRM Mode. On this photo the mill is empty (zeros), stands still in ROLLING.

What to check:
- Same checks as HRM: tilt, centre-line, roll force, looper position.
- Media READY before threading.

### Screen: FM – Bar Graph
What it shows: Per stand F1–F5: HGC (ref/act/tilt), gap, speed, roll force, looper, temperature and differential force bar graphs.
Use it for: Quickly see a finishing stand out of target.

Buttons:
- **No buttons**: Display only (bar graphs, wedge values, set / act / next).

Fields (value seen on the photo):
- **HGC / Gap / Tilt**: Per stand F5–F1 (photo: F1 5.7 / 6.9 mm)
- **Speed, roll force, looper, temperature**: Bar graphs (photo: —)
- **Wedge C25 / C40**: Wedge at FM exit (photo: +6 / +7 µm)
- **Set / Act / Next**: Bending or shift set-points for current and next coil (photo: F2 +4.4)
- **Differential rollforce**: Trends DS-OS (photo: —)

How it works: Bar-graph view of F1–F5 for quick comparison; 'Next' shows the Level-2 set-up for the next coil.

What to check:
- Wedge near 0 µm; otherwise correct tilt.
- Set = Act for all stands.

### Screen: FM – F1 Detail
What it shows: Hydraulic looper control (force/position), hydraulic gap control (roll force DS/OS, PS pressures), side-guide control, bending, shifting and calibration status of F1.
Use it for: Detailed check of stand F1 during setup or troubleshooting.

Buttons:
- **Calibration / Detail**: Change page.
- **F5 … F1**: Choose stand.
- **ForceContr / PosControl**: Looper or gap in force or position control.
- **Maintenance**: Maintenance mode of the stand.

Fields (value seen on the photo):
- **General status (left)**: HLC (looper), man. intervention, transducer, servo (photo: green)
- **Looper OS/DS**: Position, speed, PS/RS pressures, servo % (photo: 184.9 mm · 1.62 m/s)
- **Hydraulic looper control**: Position ref/act/tilt, force: strip tension next / act, strip force (photo: 16 N/mm² · 142.6 kN)
- **Status (centre)**: PosControl · ROLLING; roll diameters; PS/RS pressures DS/OS (photo: WR 0.744 m, BUR 1.44 m)
- **Hydraulic gap control**: Roll force DS/OS, diff., ref/act gap, gap DS/OS, tilt (photo: 21.9 MN · gap 5.7 mm)
- **Bending / Shifting**: Bending force OS/DS, shifting top/bottom (photo: +3.0 MN / 0 mm)
- **General**: Speed, cooling ADD 1/2 (photo: 1.49 m/s · 296 m³/h)
- **Side guide control**: SGC set-up / ref / act position (photo: 1289 / 1309 / 1280 mm)
- **Wedge adjustment / passline**: Stand pass-line height (photo: 56.2 / 10.0 mm)
- **Status blocks**: HGC, WRB, WRS: man. intervention, transducer, servo, maintenance (photo: —)
- **Calibration**: Calibration counter, general operations, SYNC (photo: 9)

How it works: Full detail of one finishing stand: hydraulic gap (thickness), looper (tension), bending (profile), shifting, side guides.

What to check:
- Roll force DS ≈ OS; big difference → tilt / strip off-centre.
- PS / RS pressures plausible; servo % near 0 in steady state.
- Any pink 'Maintenance' block = function in maintenance mode.

### Screen: FM – F1 Calibration
What it shows: Calibration steps (balancing, centre position, close gap, force taration, contact position) with gap/force trend.
Use it for: Calibrate the F1 gap after a roll change.

Buttons:
- **Step 1 … 8**: Same calibration steps as R2.
- **CAL ■ ▶ · Sync · Modulus Test**: Start / stop calibration and mill-modulus test.
- **Calibration / Detail · F5 … F1**: Change page and stand.

Fields (value seen on the photo):
- **Step 1–8**: Check balancing → prepare / close gap → roll-force taration → go to contact position → RF 200 t → RF 500 t → RF 1000 t / zeroing → open gap (photo: step 8 green)
- **General Faults 1 / 2**: Faults blocking calibration (photo: red)
- **Trend**: Gap [mm] and roll force [MN] during the calibration (photo: —)
- **Calibration Operations**: CAL start ▶ / stop ■, Sync, calibration time (photo: 119.5 s)
- **Tabs**: Calibration / Detail · F5 F4 F3 F2 F1 (photo: F1)

How it works: After a roll change the stand must be calibrated: the rolls are pressed together to a defined force, and the gap is set to zero at that force (zeroing). The modulus test measures the mill stretch used by AGC.

What to check:
- Run calibration after every roll change and when gap readings drift.
- DS-OS difference after calibration close to 0.
- If a step stays blue: check General Faults and balancing pressure.

### Screen: FM – Roll Change Overview (RCH)
What it shows: Status of F1–F5 roll change: modes, start conditions, top BUR/WR diameters, sequences, positions.
Use it for: Prepare and follow a finishing-mill roll change.

Buttons:
- **Remove / Insert Sequence (per stand)**: Automatic roll removal / insertion.
- **Ref. / Act. Position, Ref. Speed**: Roll-change car target / actual.
- **✓ / ✗**: Confirm / cancel.

Fields (value seen on the photo):
- **Mode lamps**: Rolling · Manual Not Ready · Automatic Stopped · No Start Condition · Locked (photo: Manual Not Ready)
- **Roll diameters**: Top/bottom BUR and WR (photo: WR 0.527–0.744 m)
- **Length rolled**: Km rolled since roll change (photo: F5 143.3 km · F1 35.1 km)
- **Remove / Insert sequence**: Automatic roll change (photo: buttons)
- **Ref / Act position, speed**: Roll-change car (photo: F2 29525 / 29449 mm)

How it works: Same as HRM RCH; 'Length rolled' tells when the work rolls are due for change.

What to check:
- Plan the roll change from 'Length rolled' (F5 wears fastest).
- 'Manual Not Ready' (pink) → local panel / manual mode not ready.

### Screen: FM – F1 Roll Change
What it shows: Step buttons for F1: remove/insert sequence, side-shift, rollset to millbay, limit switches, backup-roll change.
Use it for: Run the individual roll-change steps of stand F1.

Buttons:
- **Remove / Insert Sequence · Side Shift Load / Unload · Rollset to Millbay**: Roll-change steps of F1.
- **Limit Switches 1 / 2 · Backup Roll Change Sequence**: Checks and back-up roll change.
- **F1 Mode · F2 Command · F3 Data Request · F5 Seq. SSH Load · F6 Seq. SSH Unload · F7 Seq. Remove · F8 Seq. Insert · F9 Roll Data**: Function keys of the roll change.

Fields (value seen on the photo):
- **Sequence buttons + status boxes**: Remove, Insert, Side Shift Load/Unload, Rollset to Millbay, Rollset to Rollshop; the grey boxes on the right show the step progress (photo: —)
- **Side Shifter**: Side-shift car (blue = selected / moving) (photo: cyan)
- **Equipment list**: WR change tractor & hook, WR / BUR latches, top / bottom strippers, spindle carriers, wedge adjustment & clamping, ducking floor-plate, BUR change cylinder, BUR balancing & locking, main drive, screw-down, WR bending/balancing, stand cooling, exit tension roll (photo: —)
- **RCH Ready for Rolling**: All roll-change equipment back in rolling position (photo: green)
- **S12 / S13 / S14**: Pic. Up / Pic. Down / Apply (likely: select picture step, apply) (photo: buttons)
- **Mode lamps**: Rolling · Automatic · Automatic stopped · No start condition · Locked (photo: —)

How it works: Same as R1 roll change, for F1 (adds WR shifting and F2 Command / SSH load-unload keys). Here WR change tractor & hook and BUR change cylinder show AH alarms.

What to check:
- Item with alarm (AH) or not finished = where the sequence stopped.
- Before rolling: 'RCH Ready for Rolling' must be green.
- Latches (keepers) closed and strippers in position before starting the mill.

### Screen: FM – Flatness Valve Test F4
What it shows: Test page of the F4 multi-zone flatness (work-roll cooling) valves, zones 1–30, cycle / single test modes.
Use it for: Test each spray valve of F4 one by one.

Buttons:
- **Cycle Test**: Test all valves one after the other.
- **Single Test**: Test one valve.
- **Flush**: Flush the spray headers.
- **Valve Test F5 · Flatness**: Go to F5 test / flatness screen.

Fields (value seen on the photo):
- **MZC Row A / B**: Multi-zone cooling nozzles A and B, zones 1–30 from OS to DS (I = open, O = closed) (photo: —)
- **Nozzle row selection**: Choose row A or B for the test (photo: —)
- **Cycle Test**: First open valve, cycle time, time until first valve opens (photo: 1 · 8000 ms · 4000 ms)
- **Single Test**: Duty-cycle pulsing (photo: 100 %)
- **Flush**: Flush headers (photo: —)
- **Sketch**: Basic, MZC A, MZC B sprays on top / bottom work roll (photo: —)

How it works: Multi-zone work-roll cooling controls flatness: each zone sprays more or less to change the roll's thermal crown. This page tests the valves one by one (cycle) or one valve (single).

What to check:
- During the cycle test every zone must change I → O; a zone that does not move = blocked valve / nozzle.
- Check nozzles visually with Flush.

### Screen: FM – Central Switching & Monitoring (CSM)
What it shows: FM MCC feeders, frequency-controlled drives and main drives with on/off status.
Use it for: Electrical switching overview of the finishing area.

Buttons:
- **MCC Feeders · Frequency Controlled Drives · Main Drives**: Electrical switching of the FM.

Fields (value seen on the photo):
- **MCC Feeders**: HRM MCC feeder (photo: button)
- **Frequency Controlled Drives**: Roller tables, pumps… (photo: buttons)
- **Main Drives**: R1–R4 main drives (photo: buttons)

How it works: Electrical switching overview: open a group to switch it and see its state.

What to check:
- All groups green before start-up.

## Area: Cooling & Down Coilers

### Screen: Cooling L1 – Laminar Cooling
What it shows: Cooling section G1–G4 mimic, coiling temperature DC1 / LC exit, strip width/thickness, tank level, flows and trend.
Use it for: Check the run-out-table cooling and coiling temperature.

Buttons:
- **Flatness**: Open the flatness screen.
- **Cal. flow**: Flow used for calibration only.

Fields (value seen on the photo):
- **DC1–3 / LC exit temp**: Coiling and laminar-cooling exit temperatures (photo: 514 / 557 °C)
- **Strip width / thick / speed**: act / ref / L2 (photo: 1266 mm · 1.78 mm · 6.01 m/s)
- **FM exit temp**: Finishing temperature (photo: 849 °C)
- **Groups G1–G4, headers 1–16**: Top / bottom cooling headers; blue = active, crossed = out of service (photo: 11–12 active)
- **CS**: Side sprays (water removal) (photo: —)
- **Tank level / air / tank temp**: Cooling water tank (photo: 92 % · 27 °C · 38 °C)
- **CT / FM Ex temp**: Target and actual, Δ = act - ref (photo: 550 / 557 °C)
- **Trend**: Temp DC, temp FM, thickness (photo: —)

How it works: Laminar cooling brings the strip from finishing temperature (~850 °C) to coiling temperature (~550 °C). The model opens the right number of headers; the trim headers correct the last degrees.

What to check:
- CT Δ (act - ref) within ± 15 °C.
- Crossed header = out of service → less cooling capacity.
- Tank level and water temperature normal.

### Screen: DC Mode – Down Coilers
What it shows: Strip data, C1–C3 pinch rolls (gap, force), side guides, expected lengths, switch-off length, base ID.
Use it for: Follow coil change between down coilers C1, C2, C3.

Buttons:
- **Coiler 1 / 2 / 3 Settings**: Set-up of each coiler.
- **Coiler 1 / 2 / 3 Controllers**: Coiler controls.
- **C1 / C2 / C3 Release Drives**: Enable each coiler's drives.
- **Sideguides · Release RT Drives**: Side guides, roller table.
- **HSS-Coiler Mode · MTR · Local Panels**: Shear-coiler mode, material tracking, local panels.
- **Encoder Selection · PDH Diag. · CD and CC Switch On · Cooling**: Encoder, diagnostics, coiler switch-on, cooling.
- **Toggle · Ghost DC · Operator**: View, test without strip, operator commands.

Fields (value seen on the photo):
- **Strip data**: ID, width, thickness, HYP, temp, tension; St.Ten %, C-turns (photo: 1264 mm · 1.77 mm)
- **C1/C2/C3 Exp., Sw-Off**: Expected lengths and switch-off length (photo: 10 m / 13 m)
- **Pinch rolls C1–C3**: Gap and OS/DS force (photo: 65 mm)
- **SG C1–C3, SG HSS**: Side-guide openings and forces (photo: 1331 / 1273 / 1335 mm)
- **Coilers**: PRC, READY / NO-READY, wrapper rolls WR1–4 gaps, diameter, MAB (mandrel) (photo: C2 NO-READY · dia 1466 mm)
- **Coil count**: Total coils (photo: 114)
- **Coiler 1-2-3**: Selected / Production / Prepared / Loaded (photo: C2 loaded)
- **LAS speed / next**: Laser speed meter (photo: 6.25 / 6.33 m/s)
- **FM exit / SG centre-line**: Deviation (photo: -4 mm)
- **Media DC**: GO / LP / HP temperatures and levels (photo: 46 / 43 / 40 °C)

How it works: Three down coilers work in turn: one coils (Loaded), the next is Prepared. At the cut the HSS sends the new head to the prepared coiler.

What to check:
- Next coiler must be 'Prepared' and READY before the cut.
- Wrapper-roll gaps match strip thickness.
- Centre-line deviation small for a good coil edge.

### Screen: Coiler 1 – Detail 2
What it shows: Mandrel (expansion, speed, torque), wrapper rolls WR1–WR4 position/force, strip length, coil diameter.
Use it for: Troubleshoot wrapping / coiling problems on coiler 1.

Buttons:
- **BDD · Maintenance**: Coiler 1 modes (BDD likely = coil-dimension / diameter detection).
- **Calibration · P-Cal.**: Wrapper-roll calibration.

Fields (value seen on the photo):
- **Mandrel**: Expansion, grade, SV output/feedback, body temperatures (photo: E · 150 / 89 %)
- **Gearstep / bearings**: Gear step, MAB (photo: 2 · MAB)
- **Wrapper rolls WR1–4**: Piston / rod pressure, stroke, current (photo: 83 / 203 bar · 22 A)
- **Drives**: PR top/bottom, mandrel, WR1–4 speeds (photo: +6.3 / +8.2 m/s)
- **Data actual strip**: Strip length, end diameter, diameter, coil weight (photo: 955.9 m · 1651 mm)
- **WR position / force**: Gap and stroke, force per wrapper roll (photo: WR1 481 mm)
- **General status**: WRC1–4: check valve, man. intervention, maintenance, calibration, Cal. Val., P-Cal (photo: -5.04 mm)
- **Blowdown device**: BDD, maintenance (photo: —)

How it works: Wrapper rolls press the strip head round the mandrel for the first wraps, then open. Calibration values give their zero position.

What to check:
- Wrapper-roll speeds slightly above strip speed during wrapping.
- Calibration value of each WR stable; re-calibrate after maintenance (P-Cal).

### Screen: DC – Central Switching & Monitoring (CSM)
What it shows: Down-coiler MCC feeders and frequency-controlled drives.
Use it for: Electrical switching overview of the coiler area.

Buttons:
- **MCC Feeders · Frequency Controlled Drives**: Electrical switching of the coilers.

Fields (value seen on the photo):
- **MCC Feeders**: DC MCC feeders (photo: button)
- **Frequency Controlled Drives**: Coiler drives (photo: button)

How it works: Electrical switching of the coiler area.

What to check:
- All feeders ON before starting coilers.

## Area: Line-wide: Technology, Tracking, Media, Diagnostics

### Screen: Technology Overview (Technol.)
What it shows: Whole ESP line on one page: trend of thickness / IDH exit temperature / speed / ladle, sequence list, caster → HRM → IDH → FM → coilers mimic with speeds, forces and energy. Coil mode, long tail-out.
Use it for: The 'one screen' to see the whole line state and production history.

Buttons:
- **Caster Overview**: Jump to the caster.
- **F1 / F2 / F3 Vibration**: Mill-vibration monitoring per stand.
- **THC · PRC labels**: Thickness / profile control active.
- **Trend toolbar (◀ ▶ zoom 1:1)**: Scroll and zoom the production trend.

Fields (value seen on the photo):
- **Sequence table**: Seq, ladle, grade, cast coils, thickness (photo: ZE1001 / ZE2011)
- **Trend**: Thickness, IDH exit temp, speed, ladle over 12 h (photo: —)
- **Plate / Coil time**: Time and % in plate / coil mode (photo: Coil 98.9 %)
- **Rolling seq.**: Next coils with h-bar and h-strip (photo: 17.1 / 3.49 mm)
- **Cast / Rolled**: Length and weight (photo: 189.9 km · 2743 t rolled)
- **Strip / bar / cast data**: Thickness, width, speed (photo: 3.47 mm · 1263 mm · 1.42 m/s)
- **Temperatures**: CT, FM ex, IH ex/en, RSH, R4 ex, R1 en (photo: 518 / 766 / 1115 / 823 / 852 / 901 / 1001 °C)
- **Mimic**: Rollforce and gap per stand, THC / PRC, SYNC UP (photo: —)
- **Energy**: Total specific energy; EDH, IDH, HRM MD, FM MD (photo: 119.8 kWh/t · IDH 14.2 MW)

How it works: The production overview of the whole ESP line, from tundish to coiler, with history trend and energy consumption.

What to check:
- Coil-mode % high = good endless production.
- Specific energy vs. normal (IDH is the biggest consumer).
- Long Tailout (yellow) = tail-out condition active.

### Screen: Technology Overview (Technol.) – later
What it shows: Same screen a few minutes later (MAB Auto Open, sharper picture).
Use it for: Compare with the previous page.

Buttons:
- **Same buttons as the previous Technology page**: —

Fields (value seen on the photo):
- **Sequence table**: Seq, ladle, grade, cast coils, thickness (photo: ZE1001 / ZE2011)
- **Trend**: Thickness, IDH exit temp, speed, ladle over 12 h (photo: —)
- **Plate / Coil time**: Time and % in plate / coil mode (photo: Coil 98.9 %)
- **Rolling seq.**: Next coils with h-bar and h-strip (photo: 17.1 / 3.49 mm)

How it works: Same screen later, with 'MAB Auto Open' in the alarm line.

What to check:
- Coil-mode % high = good endless production.
- Specific energy vs. normal (IDH is the biggest consumer).

### Screen: Material Tracking (Mat. Track.)
What it shows: Line mimic and table of every tracked piece: ID, base ID, slab/rolled length, entry/exit thickness, production mode, per area (Caster, HRM, pendulum shear, rotary shear, FM).
Use it for: Find where each slab/coil is and its dimensions; reset tracking if needed.

Buttons:
- **All Tracking Reset**: Clear all tracked pieces (use with care!).
- **Ghost Selection**: Virtual piece for tests.
- **Tracking Conveyor**: Conveyor tracking.
- **FM Reset**: Reset FM tracking.
- **SHR Track. Reset · SHP Track. Reset**: Reset rotary / pendulum-shear tracking.

Fields (value seen on the photo):
- **Mimic**: Caster → R1–R4 → pusher/piler → heater → descaler → F1–F5 → cooling → C1–C3 (photo: —)
- **Per zone**: ID, base ID, slab length, rolled length, entry thick., exit thick. (set blue / act), production mode (photo: —)
- **Caster**: Slabs 260576115–120 (photo: 135 mm)
- **HRM R1–R4**: Thickness reduction (photo: 135 → 64.8 → 34.6 → 19.6 mm)
- **FM F1–F5**: Thickness reduction (photo: 12.2 → 6.9 → 4.5 → 3.0 → 2.2 → 1.8 mm)
- **Production mode**: Endless / Batch (photo: Endless)

How it works: Tracking follows every piece through the line; set-ups and cuts depend on it. Blue = Level-2 calculated value, black = actual.

What to check:
- Same ID must move from zone to zone — if not, tracking is lost.
- Use the reset buttons only when the line is empty or with the shift leader (they delete tracking data).

### Screen: Media System Overview
What it shows: Media (water, hydraulics, lubrication) for down-coiler area, FM, HRM and general plant.
Use it for: Check that all media pumps/systems are ready before start.

Buttons:
- **Each system button**: Opens that media system: DC / FM / HRM LP and HP hydraulics, gear lub, BUR lub, multizone cooling, ROT LC cross-spray, FM induction-heater cooling, edge-heater cooling, fans, FM descaler, grease, central filling station, sensors.
- **Remote (blue label)**: System is in remote = controlled from the HMI.
- **Green circle arrows**: Pumps running.

Fields (value seen on the photo):
- **Down coiler area**: DC LP hydraulic, HP hydraulic, gear lub (photo: Remote)
- **FM area**: FM LP / HP hydraulic, gear lub, BUR lub, multizone cooling, ROT LC cross-spray, induction-heater cooling CA / CC (photo: Multizone station ready)
- **HRM area**: HRM LP / HP hydraulic, gear lub, BUR lub, edge-heater cooling (photo: Remote)
- **General plant**: Fans, FM descaler, grease, central filling station, sensors (photo: —)

How it works: All media systems that must run before the mill can start. Each button opens the system (pumps, pressures, tanks).

What to check:
- Every system in Remote with pumps running (green arrows) before start-up.
- Yellow mark (e.g. central filling station) = warning in that system.

### Screen: Diagnostics Overview
What it shows: Communication overview, E-stop overview, safety overview, commissioning switches, media.
Use it for: Entry point for automation diagnostics and safety status.

Buttons:
- **AS/DP Communic. · OS Communic.**: PLC-network / operator-station communication.
- **Ticket System**: Fault tickets.
- **E-Stop MEDIA / DC / FM / HRM**: E-stop circuits per area.
- **Ackn Com. Switches after PLC Restart**: Acknowledge commissioning switches after a PLC restart.
- **COMMISSIONING SWITCHES**: Commissioning (bypass) switches.
- **Media · DC/CT Safety · Finishing Mill Stands · Finishing Mill · High Red. Mill**: Safety screens per area.

Fields (value seen on the photo):
- **Communication overview**: AS/DP (PLC networks) and OS (operator stations) communication (photo: buttons)
- **E-Stop overview**: E-stop circuits Media, DC, FM, HRM (photo: buttons)
- **Safety overview**: Commissioning switches, ack after PLC restart, Media, DC/CT, FM stands, FM, HRM (photo: buttons)
- **Ticket system**: Fault tickets (photo: button)

How it works: Entry point for automation faults: communication loss, emergency stops and safety circuits.

What to check:
- After an E-stop: open the area E-stop page to find which button / circuit.
- After a PLC restart: acknowledge the commissioning switches.
- Commissioning (bypass) switches must be OFF in production.

### Screen: AS DP Communication
What it shows: Profibus/Profinet networks: E-stop mill, media mill, HRM/FM stand control, DC and coiler controls.
Use it for: Find a lost bus node / PLC communication fault.

Buttons:
- **Show EVTs**: Show communication events.
- **Station symbols**: Green = node OK; grey/red = lost.

Fields (value seen on the photo):
- **E-Stop mill / Media mill**: EMS, MED PLC racks with PN (Profinet) cards (photo: green)
- **Mill area line control**: MDH, MIM, SHP, SHR, IDH, THC, FLC (photo: SHP PN red)
- **HRM stand control**: STM R1–R4, MRG RG (photo: green)
- **FM stand control**: STM F1–F5, MRG F5, FG (photo: green)
- **DC common / coiler control**: COM, MRG, MTR, HSS, CCC, CCS / GCS C1–C3 (photo: CCS C3 PN red)
- **CP**: CPU of each rack (photo: —)

How it works: Network map of the PLC racks. Each card is a Profinet (PN) node; red = node lost / faulty.

What to check:
- Red PN card: check cable, switch and power of that node (here SHP and C3).
- 'Show EVTs' to see the communication event history.
