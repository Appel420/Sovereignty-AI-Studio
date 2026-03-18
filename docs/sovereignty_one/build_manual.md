# Sovereignty One — Full Build Manual

## CDI + MED + Plasma ZLD Hybrid Desalination System

---

## 1. Safety First

> ⚠️ **WARNING**: This system handles high-voltage plasma electrodes (up to 10 kV), pressurized water circuits (up to 6 bar), and corrosive brine concentrates. All electrical work must be performed by qualified personnel. Always depressurize and de-energize before maintenance.

Required personal protective equipment (PPE):
- Safety glasses / face shield
- Chemical-resistant gloves (nitrile, minimum)
- Rubber-soled footwear
- Non-conductive tools for plasma section

---

## 2. Tools Required

- Pipe cutter (15mm and 22mm)
- Compression fitting tool
- Multimeter (DC/AC, 1000V rated)
- Oscilloscope (for plasma tuning)
- pH/TDS calibration solutions
- Torque wrench (10–50 Nm)
- Soldering station (for sensor boards)
- Laptop with Arduino IDE (ESP32-S3 board package)

---

## 3. CDI Subsystem Build

### 3.1 Carbon Electrode Stack Assembly

1. Cut activated carbon cloth (ACC) sheets to **150 mm × 200 mm** using ceramic scissors (avoid metal contamination).
2. Insert sheets alternately: `[current collector] [ACC] [separator] [ACC] [current collector]`
3. Use **Celgard 3501** or equivalent porous HDPE separator (0.5 mm thick).
4. Stack 20–40 electrode pairs per cell module.
5. Seal edges with food-grade silicone sealant. Allow 24h cure.
6. Connect current collectors in parallel to the CDI power supply bus.
7. Target cell capacitance: **200–400 F per module** at 1.2V.

### 3.2 CDI Flow Circuit

```
[Feed Pump] → [Pre-filter 5µm] → [CDI Cell] → [Product valve] → [Storage tank]
                                       ↓
                                 [Brine valve] → [Brine collection]
```

- Use **PVDF or PP** piping throughout (corrosion resistance).
- Flow rate: 0.5–2 L/min per cell module.
- Pressure drop: <0.3 bar across the CDI stack.

### 3.3 CDI Power Supply

- Charge voltage: **0.8–1.4V DC** per cell pair (never exceed 1.6V).
- Use an **LM2596** or **XL4016** buck converter (adjustable).
- Discharge: short-circuit through a resistor (10Ω, 10W) to release ions.
- CDI cycle: 5 min charge → 5 min discharge.

---

## 4. MED Subsystem Build

### 4.1 Evaporator Module Construction

1. Source **316L stainless steel** tubes (25mm OD, 1mm wall, 600mm length) — minimum 20 tubes per effect.
2. Assemble tube bundle into a **HDPE shell** (300mm ID, 700mm long).
3. Install **steam distribution header** at inlet.
4. Connect tube bundle outlet to the next effect's steam inlet (multi-effect cascade, 3 effects).
5. Install brine level sensors in each effect chamber.

### 4.2 MED Thermal Management

- Effect 1: 70°C, 0.3 bar (vacuum)
- Effect 2: 55°C, 0.16 bar
- Effect 3: 40°C, 0.07 bar
- Use a **12V compressor chiller** for the final condenser (250W).

### 4.3 MED Heat Source

- Primary: 300W flat-plate solar thermal collector (evacuated tube array optional).
- Backup: 500W PTC heater element (food-grade, PTFE-coated).
- Controls: SSR (solid-state relay) on the PTC heater, thermocouple feedback.

---

## 5. Plasma ZLD Subsystem Build

### 5.1 Plasma Reactor Construction

1. Use a **quartz glass tube** (50mm ID, 300mm length) as the discharge chamber.
2. Install **titanium mesh electrodes** on the outer surface (wrapped, not inserted).
3. Connect to a **high-voltage driver** (10 kV, 1–10 kHz, 50W) — resonant half-bridge topology.
4. Fill the quartz tube with brine concentrate from the MED output.
5. Install a **magnetic stirrer** at the base to prevent hot spots.

### 5.2 Plasma HV Driver

- IGBT pair: FGH40N60SMD
- Gate driver: IR2110
- Transformer: ferrite core EE65, primary 10T, secondary 200T (20:1 ratio for 10kV from 500V bus)
- Safety: 10MΩ bleeder resistors across output; polycarbonate enclosure; interlocked safety door switch.

### 5.3 Mineral Recovery

After plasma treatment, filter brine through:
1. 0.2 µm ceramic membrane (silica/alumina removal)
2. Ion exchange columns (NaCl → Na₂CO₃ separation)
3. Crystallizer pan (evaporation of residual water)
4. Harvest minerals: NaCl, MgSO₄, CaCO₃, KCl

---

## 6. ESP32 Controller Installation

### 6.1 Sensor Wiring

| Sensor | Model | Pin (ESP32-S3) | Notes |
|--------|-------|----------------|-------|
| TDS | DFRobot SEN0244 | GPIO34 | Calibrate with 1413 µS/cm solution |
| pH | Atlas Scientific EZO-pH | GPIO35 | 2-point calibration (pH 4.0, 7.0) |
| ORP | Atlas Scientific EZO-ORP | GPIO36 | Reference: 225 mV in 468 mV Zobell |
| Temperature | DS18B20 | GPIO37 | Use 4.7kΩ pull-up to 3.3V |
| Pressure | HK1100C 0–10 bar | GPIO39 | Analog 0.5–4.5V output |
| Flow | YF-S201 | GPIO38 | Interrupt counting |
| PV Voltage | Voltage divider 60:1 | GPIO32 | Use precision resistors |
| PV Current | ACS712-20A | GPIO33 | VCC=5V, 100mV/A |

### 6.2 Actuator Wiring

All actuator pins drive **5V relay modules** (opto-isolated). Use separate 12V/5A supply for relay power.

### 6.3 Firmware Upload

```bash
# Install Arduino IDE 2.x
# Add ESP32-S3 board package:
# https://raw.githubusercontent.com/espressif/arduino-esp32/gh-pages/package_esp32_index.json

# Board: ESP32S3 Dev Module
# Upload Speed: 921600
# Flash Size: 8MB
# PSRAM: OPI PSRAM

arduino-cli compile --fqbn esp32:esp32:esp32s3 sovereignty_one/firmware/esp32_hybrid_controller.ino
arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32s3 sovereignty_one/firmware/esp32_hybrid_controller.ino
```

---

## 7. System Integration & Testing

### 7.1 Pre-Commissioning Checks

- [ ] All pipe joints leak-tested at 1.5× operating pressure (9 bar for 6 bar systems)
- [ ] All electrical connections torqued and insulated
- [ ] CDI voltage confirmed <1.6V per cell pair
- [ ] Plasma HV enclosure interlocks verified
- [ ] Emergency stop button accessible and tested
- [ ] All sensors calibrated and reading within ±2% of reference

### 7.2 First Run Procedure

1. Fill feed tank with fresh water (not brine) for initial flush.
2. Power on ESP32 controller — confirm telemetry output on serial monitor.
3. Open feed valve slowly — check for leaks.
4. Enable CDI charge cycle — monitor TDS drop on product side.
5. Introduce brine feed gradually, monitoring sensor readings.
6. Enable MED after CDI cycle confirms stable operation.
7. Enable Plasma ZLD last, after brine concentrate accumulates.
8. Monitor mineral crystallizer output after 24h operation.

---

## 8. Maintenance Schedule

| Interval | Task |
|----------|------|
| Daily | Check sensor readings, flow rates, pressure |
| Weekly | Flush CDI stack, clean pre-filter cartridge |
| Monthly | pH/TDS sensor recalibration |
| Quarterly | Clean MED tubes (citric acid descale) |
| Annually | Replace CDI carbon electrodes, inspect plasma electrodes |
