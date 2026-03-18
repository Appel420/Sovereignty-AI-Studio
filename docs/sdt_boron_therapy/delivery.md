# SDT-Boron Therapy — Boron Delivery Systems

> **⚠️ RESEARCH ONLY** — See [README.md](README.md) for full disclaimer.

---

## Overview

Effective SDT-Boron therapy requires selective delivery of ¹⁰B-enriched compounds to tumor cells at concentrations sufficient for therapeutic effect (≥20 µg ¹⁰B/g tumor tissue per BNCT standards, adapted for SDT activation).

Three primary delivery platforms are under investigation:

---

## 1. Boronated Liposomes

### Design
- **Lipid shell**: DPPC/DPPE-PEG2000/cholesterol (molar ratio 55:5:40)
- **Diameter**: 100–200 nm (EPR effect optimal)
- **Boron payload**: Sodium dodecaborate (Na₂B₁₂H₁₁SH, BSH) encapsulated in aqueous core
- **Surface functionalization**: Anti-HER2 or anti-EGFR antibody fragments for tumor targeting
- **Loading efficiency**: 15–25 µg ¹⁰B per mg lipid

### Preparation Protocol
1. Hydrate lipid film in BSH solution (50 mg/mL) at 65°C
2. Extrude 11× through 200 nm polycarbonate membrane
3. Remove free BSH by dialysis (10 kDa MWCO, 24h, 4°C)
4. Conjugate targeting ligand via NHS-EDC chemistry
5. Characterize by DLS, zeta potential, ICP-MS for ¹⁰B quantification

### Pharmacokinetics (murine data)
- **T½ circulation**: 8–14 hours (PEGylated formulation)
- **Tumor accumulation**: 4–12% injected dose/g tumor (passive EPR + active targeting)
- **Peak tumor:blood ratio**: 3:1 to 8:1 at 24–48h post-injection
- **Optimal ultrasound window**: 12–48h post-injection

### Advantages
- Clinically established delivery platform (FDA-approved liposomal drugs: Doxil, Abraxane)
- High boron loading capacity
- Tunable release kinetics

---

## 2. Boron-Loaded Microbubbles

### Design
- **Shell**: DSPC/DPPA/MPEG-DSPE lipid shell
- **Gas core**: Perfluoropropane (C₃F₈) or SF₆ (for ultrasound contrast)
- **Boron attachment**: BSH or carboranyl lipid analogs embedded in shell
- **Diameter**: 1–5 µm (cavitation-optimized for MHz ultrasound)
- **Boron concentration**: 5–15 µg ¹⁰B per 10⁸ microbubbles

### Mechanism
1. IV injection → circulates through vasculature
2. Focused ultrasound causes microbubble oscillation (stable cavitation)
3. Shell disruption at tumor vasculature releases BSH payload locally
4. Sonoporation enhances cellular uptake of released boron compounds
5. Secondary ultrasound pulse (lower frequency) activates boron-ROS mechanism

### Dual-Frequency Protocol
- **Phase 1**: 1.0 MHz, 100 kPa, 5 min — microbubble disruption + delivery
- **Phase 2**: 0.5 MHz, 500 kPa, 10 min — sonodynamic activation
- Interval: 30 min for cellular uptake

### Advantages
- Real-time ultrasound imaging for treatment monitoring
- Vascular-to-intracellular delivery in two-step process
- Cavitation enhances cellular membrane permeability (sonoporation)

---

## 3. Small Molecule Boron-Sonosensitizer Conjugates

### Lead Candidates

**Boronated Chlorin e6 (BChle6)**
- Chlorin e6 (sonosensitizer) + carborane cage covalently linked
- Molecular weight: ~900 Da
- Tumor selectivity via porphyrin transporter upregulation in cancer cells
- ¹O₂ quantum yield: 0.52 (vs 0.54 for chlorin e6 alone — minimal impact from boron conjugation)

**BSH-Porphyrin Conjugate**
- Na₂B₁₂H₁₁SH linked to meso-tetracarboxyphenyl porphyrin
- Water-soluble at physiological pH
- Cellular uptake: 2.3 µg ¹⁰B/10⁶ cells (HeLa, 4h incubation)

### Formulation
- Administered as 5% DMSO in PBS solution (IV push over 15 min)
- Dose: 50–100 mg/kg (murine models)
- Tumor accumulation: 18–24h post-administration

---

## Dosimetry Considerations

Target ¹⁰B concentration for SDT activation (estimated from BNCT literature, adapted):
- **Minimum effective**: 10 µg ¹⁰B/g tumor tissue
- **Optimal**: 20–30 µg ¹⁰B/g tumor tissue
- **Selectivity ratio** (tumor:normal tissue): minimum 3:1 required

Boron quantification methods:
- ICP-MS (inductively coupled plasma mass spectrometry) — gold standard
- Prompt gamma neutron activation analysis (PGNAA)
- ¹⁰B NMR spectroscopy (for in vitro work)
