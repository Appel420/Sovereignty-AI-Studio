# SDT-Boron Therapy — Killing Mechanism

> **⚠️ RESEARCH ONLY** — See [README.md](README.md) for full disclaimer.

---

## Overview of Tumor Cell Death Pathways

SDT-Boron therapy engages multiple overlapping cancer cell death mechanisms:

1. **ROS-mediated oxidative damage** (primary SDT mechanism)
2. **DNA double-strand breaks** (boron-mediated radical amplification)
3. **Mitochondrial pathway apoptosis**
4. **Immunogenic cell death (ICD)** triggering anti-tumor immunity
5. **Anti-angiogenic vascular disruption**

---

## 1. Reactive Oxygen Species (ROS) Generation

### Mechanism
Upon ultrasound activation of the sonosensitizer (e.g., boronated chlorin e6):

```
Sonosensitizer + hν(ultrasound) → ¹Sonosensitizer* → ³Sonosensitizer*
³Sonosensitizer* + O₂ → ¹O₂ (singlet oxygen)     [Type II pathway]
³Sonosensitizer* + substrate → O₂•⁻ (superoxide)  [Type I pathway]
O₂•⁻ + H⁺ → H₂O₂ → •OH (hydroxyl radical via Fenton)
```

### Boron Enhancement of ROS
¹⁰B atoms in the sonosensitizer conjugate undergo ultrasound-driven excitation:
- ¹⁰B + acoustic cavitation → excited ¹⁰B* state
- ¹⁰B* participates in Fenton-like radical chain reactions
- Net effect: 2–4× increase in •OH yield vs non-boronated sonosensitizer (Osminkina et al., 2019 [ref 3])

### Intracellular ROS Targets
| Biomolecule | ROS Attack | Consequence |
|-------------|-----------|-------------|
| Lipid membrane | •OH + PUFA → lipid peroxidation | Membrane integrity loss |
| Mitochondria | O₂•⁻ → mtDNA damage | Cytochrome c release |
| Nuclear DNA | •OH → 8-oxoguanine, DSBs | Apoptosis initiation |
| Proteins | •OH → carbonylation | Enzyme inactivation |

---

## 2. DNA Repair Blockade

### Direct DNA Damage
Hydroxyl radical (•OH) causes:
- **8-oxo-7,8-dihydroguanine (8-oxoG)**: mismatches → G:C → T:A transversions
- **Thymine glycol**: replication block → S-phase arrest
- **Double-strand breaks (DSBs)**: detected by γ-H2AX foci; primary lethal lesion

### Boron-Specific Mechanism (Hypothesized)
Boron-sonosensitizer conjugates localized in nucleus:
- ¹⁰B* excited by cavitation → local radical generation within 1–2 nm of DNA
- Proximity effect: radical generated adjacent to DNA strand → higher strand break probability vs bulk radical diffusion
- **Analogous to BNCT α-particle track**: localized linear energy transfer (LET) at DNA

### DNA Repair Pathway Interference
ROS from SDT disrupts:
- **PARP-1**: oxidative damage to PARP-1 → NAD⁺ depletion → necrotic/apoptotic switch
- **ATM kinase**: oxidation of cysteine residues → impaired DSB sensing
- **Ku70/Ku80**: oxidative inactivation → NHEJ repair suppression
- Net effect: accumulation of unrepaired DSBs → cell death commitment

---

## 3. Apoptosis Pathways

### Intrinsic (Mitochondrial) Pathway
1. ROS → mitochondrial membrane permeabilization (MMP)
2. Cytochrome c release into cytosol
3. Apoptosome formation: cytochrome c + Apaf-1 + dATP → caspase-9 activation
4. Caspase-3/7 effector activation → DNA fragmentation, cell shrinkage
5. Phosphatidylserine externalization → phagocytic clearance

### Extrinsic Pathway (ROS-mediated)
- •OH → NF-κB suppression → downregulation of anti-apoptotic Bcl-2, XIAP
- Upregulation of death receptors: FasL, TRAIL → caspase-8 activation
- Bid cleavage → cross-talk with mitochondrial pathway (amplification loop)

### Quantification Markers
| Marker | Detection Method | SDT-Boron Timepoint |
|--------|-----------------|---------------------|
| Caspase-3 activity | Fluorogenic substrate assay | 4–8h post-treatment |
| Annexin V binding | Flow cytometry | 6–12h |
| γ-H2AX foci | Immunofluorescence | 1–4h |
| MMP loss | JC-1 dye, flow cytometry | 2–6h |
| Sub-G₁ fraction | PI staining, FACS | 12–24h |

---

## 4. Immunogenic Cell Death (ICD)

SDT-Boron at sufficient ROS levels induces ICD — a form of apoptosis that activates anti-tumor immunity:

### ICD Hallmarks
1. **Calreticulin (CRT) surface exposure**: "eat-me" signal for dendritic cells
2. **HMGB1 release**: activates TLR4 on DCs → IL-12, TNF-α secretion
3. **ATP secretion**: purinergic signal → DC recruitment and maturation
4. **Type I IFN induction**: viral mimicry pattern → antigen cross-presentation

### Abscopal Effect Potential
ICD-triggered adaptive immune response may control distal, untreated metastases — the "abscopal effect." Combination with checkpoint inhibitors (anti-PD-1, anti-CTLA-4) potentially synergistic.

---

## 5. Vascular Disruption

At the tumor vascular level:
- ROS → endothelial cell apoptosis → tumor blood vessel collapse
- Microbubble cavitation → physical disruption of tumor neovasculature
- Result: secondary tumor hypoxia and necrosis

**Note**: Unlike vascular disrupting agents (VDAs), SDT-Boron vascular effects are spatially confined to the ultrasound focal zone, preserving normal tissue vasculature.

---

## Selectivity Mechanisms

Cancer cells are preferentially killed vs normal tissue due to:
1. **Higher boron accumulation**: tumor targeting + EPR effect
2. **Elevated baseline ROS**: cancer cells are closer to oxidative stress threshold
3. **Impaired antioxidant defense**: many tumors have reduced glutathione, SOD activity
4. **Proliferative advantage becomes vulnerability**: S-phase cells 2–3× more sensitive to ROS-mediated DNA damage
5. **Spatial confinement**: ultrasound focal zone limits treatment to target volume
