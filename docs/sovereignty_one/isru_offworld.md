# Sovereignty One — Extraterrestrial ISRU Adaptations

## In-Situ Resource Utilization for Off-World Water Production

---

## Mars

### Water Sources
- Subsurface briny aquifers (detected by MARSIS radar)
- Regolith-bound ice (polar and mid-latitude)
- Atmospheric water vapor (0.02% humidity, harvestable via desiccant)
- Perchlorate-contaminated meltwater (up to 1% ClO₄⁻ by mass)

### CDI Adaptation for Mars
- **Perchlorate removal**: Standard activated carbon CDI removes ~85% ClO₄⁻ in single pass; doped carbon (N-doped) achieves >99%
- **Operating temperature**: CDI can operate at -20°C to +5°C Martian ambient; cell capacitance drops ~30% at -20°C (compensate with more cell pairs)
- **Power budget**: 0.5–1.5 kWh/m³ (comparable to Earth) from compact RTG or solar panels
- **Pressure**: Operate at 10–100 mbar Martian atmospheric pressure (seals must be tightened; use EPDM not silicone above -40°C)

### MED Adaptation for Mars
- Low atmospheric pressure means boiling point ~10°C at 1.2 kPa (Martian surface)
- MED operates naturally at ultra-low temperatures and pressures — **advantage on Mars**
- Use waste heat from RTG or nuclear fission surface power system
- GOR improves to 4–6 at lower pressure (more effects achievable)

### Plasma ZLD for Martian Brine
- Plasma reactor is pressure-independent — works in vacuum
- Perchlorate destroyed by plasma (ClO₄⁻ → Cl⁻ + O₂) — dual benefit: water purification + oxygen production
- Mineral output: NaClO₄ → NaCl + O₂; MgSO₄ → fertilizer for greenhouse agriculture

### Miniaturization Targets (Mars Surface Unit)
- Output: 50–200 L/day (crew of 4–6)
- Mass: <80 kg (total system)
- Volume: 0.5 m³
- Power: <100W continuous (150W peak plasma pulse)

---

## Moon (Lunar South Pole)

### Water Sources
- Polar permanently shadowed regions (PSRs): water ice confirmed by LCROSS, M³
- Estimated: 600 million tonnes of ice in PSRs
- Ice mixed with regolith at 1–10% by mass
- Additional volatiles: CO₂, SO₂, H₂S (must be removed)

### Lunar CDI Adaptation
- Extract ice by microwave heating or resistive heating of regolith
- Meltwater TDS: 500–5,000 ppm (primarily sulfates, chlorides)
- CDI ideal for this TDS range — minimal adaptation needed
- Vacuum sealing required (Moon has no atmospheric pressure)

### Key Lunar Challenges
- Dust contamination: lunar regolith particles <1µm can clog CDI membranes — pre-filter with electrostatic precipitator
- Temperature extremes: -173°C (shadow) to +127°C (sunlit) — all components must be thermally isolated
- No magnetosphere: radiation hardening required for ESP32 electronics (use shielded enclosure + rad-hard COTS)

---

## Europa (Jupiter Moon)

### Water Source
- Global subsurface liquid ocean (~100 km deep, beneath 10–30 km ice shell)
- Ocean salinity: 35–100 g/L (similar to or saltier than Earth's seawater)
- Probable composition: MgSO₄, NaCl, H₂SO₄ (from radiolysis)
- Access: via ice shell drilling (melt probe, Philberth probe concept)

### CDI on Europa
- MgSO₄-dominated water: CDI performs excellently for divalent sulfate removal
- Operating temperature: ~0°C (just above ocean freezing point)
- Power: Europa Clipper / future lander nuclear power system
- Target: drinking water for crew of sub-ice habitat

### Plasma ZLD on Europa
- Mineral recovery from 100 g/L brine would yield:
  - MgSO₄·7H₂O (Epsom salt) — valuable for plant growth in habitat
  - NaCl — electrolyte source
  - Sulfur compounds — potential fuel precursors

---

## Enceladus (Saturn Moon)

### Water Source
- Active geysers venting salty water from subsurface ocean through tiger stripe fractures
- Geyser plume composition (Cassini): H₂O, NaCl, H₂, CO₂, CH₄, silica nanoparticles, organics
- TDS equivalent: ~10–20 g/L
- Organics detected: benzene, toluene, complex organics >200 amu

### Opportunity
- **Lowest energy water source in the outer solar system** — geyser water is freely available at surface
- CDI removes NaCl; plasma ZLD recovers minerals and destroys organic micropollutants
- Silica nanoparticles (2–8 nm): collect and use as structural material

---

## Titan (Saturn Moon)

### Water Source
- Titan has no liquid water on surface (too cold, -179°C)
- Lakes are liquid methane/ethane — not directly usable as water
- Water ice exists in crust; could be melted by RTG waste heat
- Atmospheric chemistry produces complex organics (tholins) that would contaminate any melt water

### Adaptation
- CDI for ion removal from melted ice
- Plasma ZLD destroys tholin organic contamination (oxidative plasma in O₂ atmosphere)
- Primary output: electrolysis feedstock for H₂ fuel and O₂ for propulsion/life support

---

## Technology Readiness Summary

| Target | CDI TRL | MED TRL | Plasma TRL | Key Barrier |
|--------|---------|---------|-----------|-------------|
| Earth (deployed) | 7–8 | 7 | 5–6 | — |
| Mars (near-term) | 4–5 | 5 | 4 | Perchlorate, pressure sealing |
| Moon (near-term) | 4 | 4 | 4 | Vacuum sealing, dust filtration |
| Europa (far-term) | 3 | 3 | 3 | Access to ocean, radiation |
| Enceladus (far-term) | 3 | 3 | 3 | Transit, power |
| Titan (speculative) | 2 | 2 | 3 | Temperature, tholin chemistry |
