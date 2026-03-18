# Sovereignty One — Water Sovereignty System

## From Hello to Goodbye

From the first raindrop collected to the last mineral extracted from brine, Sovereignty One closes the loop on water — a fully sovereign, self-powered, zero-liquid-discharge desalination and purification platform designed to operate anywhere on Earth, and beyond.

**We believe clean water is a fundamental human right, not a commodity.** Sovereignty One is built on that premise: open hardware, open firmware, open data — a system that any community can build, operate, maintain, and eventually export to the stars.

---

## Technical Summary

Sovereignty One is a **CDI + MED + Plasma ZLD hybrid system** that combines three proven desalination technologies into a single, solar-powered, self-correcting unit:

| Subsystem | Technology | Purpose |
|-----------|-----------|---------|
| **CDI** | Capacitive Deionization | Primary desalination (low-energy, reversible) |
| **MED** | Multi-Effect Distillation | Secondary polishing + volume reduction |
| **Plasma ZLD** | Cold plasma brine treatment | Zero-liquid-discharge + mineral extraction |
| **Control** | ESP32-S3 firmware | Autonomous sensor-driven operation |
| **Power** | PV + battery | Off-grid, self-sustaining |

### Key Specifications

- **Feed water range**: Brackish (500 ppm) to seawater (45,000 ppm TDS)
- **Product water quality**: <50 ppm TDS (WHO drinking standard)
- **Daily output**: 1,000–10,000 L/day (modular, scalable)
- **Power consumption**: 0.5–3 kWh/m³ (CDI-dominant mode)
- **Footprint**: 2m × 1.5m × 1.8m (standard shipping container configurable)
- **ZLD**: 100% brine recovery via plasma mineralization

### System Architecture

```
[Feed Water] → [Pre-filter] → [CDI Stack] → [Product Water]
                                    ↓
                              [Brine Concentrate]
                                    ↓
                              [MED Evaporator] → [Distillate]
                                    ↓
                              [Plasma Reactor] → [Mineral Salts]
                                    ↓
                              [ZLD — Zero Discharge]

[PV Array] → [MPPT Controller] → [Battery Bank] → [All Subsystems]
[ESP32-S3 Controller] ← [TDS/pH/ORP/Temp/Pressure/Flow Sensors]
```

---

## Quick Start

See the [Build Manual](build_manual.md) for full assembly instructions.

See [BOM — CDI](bom_cdi.md) and [BOM — MED](bom_med.md) for parts lists.

See [Deployment Plan](deployment_plan.md) for site requirements.

---

## Repository Structure

```
sovereignty_one/
├── firmware/
│   └── esp32_hybrid_controller.ino   # ESP32-S3 control firmware
docs/sovereignty_one/
├── README.md              # This file
├── build_manual.md        # Full build instructions
├── bom_cdi.md             # CDI subsystem bill of materials
├── bom_med.md             # MED subsystem bill of materials
├── grant_proposal.md      # Funding proposals
├── deployment_plan.md     # Site deployment guide
├── brine_mining.md        # ZLD brine mineral extraction revenue
└── isru_offworld.md       # Extraterrestrial ISRU adaptations
```

---

## License

Hardware designs, firmware, and documentation are released under the **CERN Open Hardware Licence v2 — Strongly Reciprocal (CERN-OHL-S-2.0)**.
