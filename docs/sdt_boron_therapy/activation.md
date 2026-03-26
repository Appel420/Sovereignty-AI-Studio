# SDT-Boron Therapy — Ultrasound Activation Parameters

> **⚠️ RESEARCH ONLY** — See [README.md](README.md) for full disclaimer.

---

## Sonodynamic Activation Fundamentals

Sonodynamic therapy (SDT) uses **low-intensity focused ultrasound (LIFU)** to activate sonosensitizer molecules within target tissue, generating reactive oxygen species (ROS) that trigger tumor cell death. When combined with boron compounds, the mechanism involves both sonodynamic ROS production and boron-assisted radical amplification.

---

## Ultrasound Parameters for SDT-Boron

### Frequency Selection

| Frequency | Effect | Application |
|-----------|--------|-------------|
| 0.5 MHz | Deep tissue penetration (>10 cm), strong cavitation | Abdominal/pelvic tumors |
| 1.0 MHz | Moderate depth (5–10 cm), balanced thermal/cavitation | Soft tissue tumors |
| 3.0 MHz | Superficial penetration (<3 cm), precise focal volume | Skin/subcutaneous |

**Recommended primary frequency**: 1.0 MHz (most published SDT data; optimal cavitation threshold)

### Intensity Parameters

| Parameter | Stable Cavitation (SDT) | Inertial Cavitation (ablation) |
|-----------|------------------------|-------------------------------|
| ISPTA | 0.1–1.0 W/cm² | >5 W/cm² |
| ISPPA | 5–50 W/cm² | >200 W/cm² |
| MI | 0.1–0.4 | >0.7 |
| Duty cycle | 20–50% | 5–20% |

**SDT-Boron target**: ISPTA = 0.5 W/cm², MI = 0.3 (stable cavitation regime — non-ablative)

### Pulse Sequence (Optimized for BSH-Liposome Delivery)

```
Phase 1: Delivery Enhancement
  Frequency: 1.0 MHz
  Pressure: 100 kPa (MI = 0.1)
  Pulse: 50% duty cycle, 5 min total
  Purpose: Microbubble-mediated sonoporation for boron uptake

[30 min pause — cellular uptake of BSH]

Phase 2: SDT Activation
  Frequency: 1.0 MHz
  Pressure: 500 kPa (MI = 0.5)
  Pulse: 20% duty cycle (2 ms on / 8 ms off)
  Duration: 20 min total
  Purpose: Sonosensitizer activation → ROS generation

[Monitor temperature — maintain <42°C to avoid thermal ablation]
```

---

## Focused Ultrasound Transducer Requirements

### Clinical Research Transducer Specifications
- **Array type**: Phased array or single-element with mechanical steering
- **Aperture**: 10–15 cm (for 5–10 cm focal depth)
- **Focal spot size**: 1–3 mm lateral × 5–15 mm axial (–6 dB)
- **Steering range**: ±20° electronic, ±30° mechanical
- **Imaging integration**: Co-registered B-mode for real-time guidance

### Temperature Monitoring
- **MR-guided HIFU**: Gold standard (MR thermometry); not required for SDT intensities
- **Thermocouple array**: Adequate for research at SDT power levels
- **Acoustic radiation force imaging (ARFI)**: Real-time mechanical property mapping during treatment
- **Target thermal dose**: CEM43 < 2 (non-ablative — unlike HIFU which targets CEM43 > 240)

---

## Cavitation Monitoring

Passive cavitation detection (PCD) confirms therapeutic cavitation activity:

### Stable Cavitation (desired for SDT)
- Spectral signature: harmonic peaks at f₀ × n (subharmonic at f₀/2)
- Broadband emission: low-level, continuous
- Bubble oscillation: linear to mildly nonlinear

### Inertial Cavitation (avoid for SDT)
- Spectral signature: broadband noise burst (wideband emission)
- Bubble collapse: violent, generates shock waves and free radical burst
- Associated with cell membrane disruption and hemorrhage at high rates

**PCD detection setup**:
- Passive detector: 2.25 MHz broadband transducer, 90° to treatment beam
- FFT analysis: 512-point windowed FFT, 10 ms frames
- Threshold: subharmonic (500 kHz) emission >6 dB above noise floor = stable cavitation confirmed

---

## Biological Temperature Window

| Temperature | Biological Effect |
|-------------|------------------|
| 37°C | Normal tissue function |
| 40–41°C | Mild hyperthermia — enhances sonosensitizer uptake |
| 42–43°C | Hyperthermia — synergistic with SDT (acceptable limit) |
| 44–46°C | Thermal damage onset — avoid |
| >46°C | Ablative injury — outside SDT protocol |

SDT-Boron protocol targets **39–42°C** focal tissue temperature for optimal ROS generation without thermal ablation.
