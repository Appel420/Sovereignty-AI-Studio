# Sovereignty One — Site Deployment Plan

## Requirements & Checklist

---

## 1. Site Assessment Criteria

Before deploying a Sovereignty One unit, confirm all site requirements are met:

### Water Source
- [ ] Feed water TDS characterized (test kit or lab analysis)
- [ ] Feed water volume sufficient (minimum 2× daily output)
- [ ] Pre-sedimentation basin available or constructible
- [ ] Water rights / permits confirmed (where applicable)

### Power
- [ ] Solar irradiance ≥4 peak sun hours/day (annual average)
- [ ] Space for PV array: minimum 8m² (4× 2m² panels)
- [ ] Battery storage space: weatherproof enclosure for 200Ah LiFePO₄
- [ ] Electrical permit (if grid-tied backup desired)

### Physical Space
- [ ] Footprint: minimum 3m × 2m level ground
- [ ] Roof/shade optional but recommended for longevity
- [ ] Brine/mineral storage area: minimum 1m × 1m adjacent
- [ ] Product water storage: minimum 500L tank nearby

### Personnel
- [ ] At least one trained operator per community
- [ ] Basic electronics/mechanical aptitude confirmed
- [ ] Spare parts kit on-site (filter cartridges, fuses, gaskets)

---

## 2. Standard Hardware Configuration

### PV System
- 4× 200W monocrystalline panels (800W peak)
- 1× 60A MPPT charge controller (Victron SmartSolar or equivalent)
- 2× 100Ah LiFePO₄ batteries (24V bank)
- 1× 1000W pure sine inverter (for 220V accessories)

### Water System
- 1× CDI stack (20-pair, 150×200mm electrodes)
- 1× MED unit (3-effect, 300mm ID shells)
- 1× Plasma ZLD reactor (quartz, 50mm ID)
- Feed pump: 12V, 50W, peristaltic
- Pre-filter: 10-inch PP housing, 5µm + 1µm cartridges
- Product storage: 200L HDPE food-grade tank
- Brine/mineral collection: 50L HDPE + crystallizer tray

### Control & Monitoring
- 1× ESP32-S3 controller board (flashed with latest firmware)
- Sensor suite: TDS × 2, pH, ORP, temperature, pressure, flow
- GSM/LoRa module for remote telemetry (optional)
- Weatherproof enclosure: IP65, 400×300×150mm

---

## 3. Installation Sequence

### Day 1: Civil & Structural
1. Level and compact mounting area
2. Install anchor bolts for unit frame
3. Excavate cable trench (PV to unit, <10m preferred)
4. Position and secure water storage tanks

### Day 2: PV System
1. Mount PV panels (tilt angle = latitude ±5°, south-facing in northern hemisphere)
2. Run DC cable (6mm², tinned copper) from panels to charge controller
3. Install charge controller in weatherproof enclosure
4. Connect battery bank (series/parallel for 24V)
5. Commission charge controller — confirm charging

### Day 3: Water System
1. Assemble CDI stack modules in frame
2. Install MED unit and connect to CDI brine output
3. Install plasma reactor and connect to MED concentrate
4. Connect all pipe circuits (feed → CDI → product; CDI brine → MED → plasma → mineral)
5. Pressure test all circuits at 1.5× operating pressure
6. Install pre-filter housing and cartridges

### Day 4: Controls & Commissioning
1. Mount ESP32 controller board in enclosure
2. Wire all sensors per the wiring table in the build manual
3. Wire relay outputs to pumps, valves, and actuators
4. Flash latest firmware via USB
5. Power on — confirm serial telemetry
6. Run fresh water flush for 2 hours
7. Introduce feed water — calibrate sensors against reference samples
8. Enable automated operation — monitor for 4 hours
9. Test emergency stop and safety interlocks

### Day 5: Training & Handover
1. Train operator on daily checks (sensor readings, flow rates, pressure)
2. Demonstrate filter cartridge replacement
3. Demonstrate CDI discharge cycle and electrode flush
4. Review fault codes and telemetry dashboard
5. Leave printed quick-reference card and maintenance schedule
6. Provide spare parts kit inventory

---

## 4. Performance Targets (Post-Commissioning)

| Metric | Target |
|--------|--------|
| Product TDS | <50 ppm |
| Product pH | 6.5–8.5 |
| Daily output | 500–2,000 L |
| CDI removal efficiency | >80% |
| System uptime | >95% monthly |
| Mineral recovery | >90% of brine solids |
| Energy consumption | <1.5 kWh/m³ |
