# Sovereignty One — Technical Documentation

> *From Hello to Goodbye: A sovereign platform that begins with a greeting and ends with full independence.*

---

## Vision

Sovereignty One is a self-hosted, vendor-independent AI platform and water systems research project.
Its goal: **zero dependency on external SaaS**, from compute to water purification to interplanetary resource extraction.

Every component is self-hosted, sovereign, and designed to run on infrastructure you own and control.

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                   Sovereignty AI Studio                     │
│                                                             │
│  ┌─────────────┐    ┌──────────────────────────────────┐   │
│  │  Frontend   │    │     Sovereign Agent Bridge        │   │
│  │ (Port 9898) │◄──►│  node-bridge/sovereign_bridge.mjs │   │
│  └─────────────┘    └──────────────┬───────────────────┘   │
│                                    │                        │
│                     ┌──────────────▼───────────────────┐   │
│                     │    ai_core/sovereign_bridge.py     │   │
│                     │  ┌──────────┐  ┌──────────────┐  │   │
│                     │  │local_gguf│  │  local_onnx  │  │   │
│                     │  └──────────┘  └──────────────┘  │   │
│                     └──────────────┬───────────────────┘   │
│                                    │                        │
│  ┌──────────┐  ┌──────────┐   ┌───▼────────┐              │
│  │ Postgres │  │  Redis   │   │  Backend   │              │
│  │  (5432)  │  │  (6379)  │   │  FastAPI   │              │
│  └──────────┘  └──────────┘   └────────────┘              │
└─────────────────────────────────────────────────────────────┘
```

### Key Principle
**All AI inference is local.** No request ever reaches an external SaaS provider.
The sovereign bridge tries providers in order: `local_gguf → local_onnx → sovereign_api`
and never falls back to Meta, Google, or any third party.

---

## CDI+MED+Plasma Hybrid Water System

### Technology Stack

| Stage | Technology | Purpose |
|-------|-----------|---------|
| Pre-treatment | Micro/ultrafiltration | Remove suspended solids |
| Primary | CDI (Capacitive Deionization) | Remove dissolved ions, low-energy |
| Secondary | MED (Membrane Electrodialysis) | High-TDS brine concentration |
| Tertiary | Plasma oxidation (optional) | Pathogen elimination, emerging contaminants |
| Brine | ZLD (Zero Liquid Discharge) pond | Mineral recovery, salt harvesting |

### CDI Operating Parameters
- Input TDS: 500–3,000 ppm
- Output TDS: <50 ppm target
- PV minimum: 18 V @ 10 A
- Polarity reversal: every 15 minutes (anti-scaling)
- Recovery rate: 70–85%

### MED Operating Parameters
- Input TDS: 1,500–35,000 ppm (brackish to seawater)
- Output TDS: <200 ppm
- PV minimum: 22 V @ 15 A
- Stage count: 3–7 effects depending on salinity
- Recovery rate: 40–65%

### Brine Mining Targets
- NaCl (table salt) — commodity
- MgCl₂ — magnesium feedstock
- KCl — potassium fertilizer
- Lithium (brine concentration > 150 ppm)
- Boron (SDT-Boron therapy feedstock at medical grade)

---

## Build Phases

### Phase 1 — Pilot (250 L/day)
- [ ] Single ESP32 controller
- [ ] CDI cell stack (10 pairs)
- [ ] PV array (500 W)
- [ ] Basic telemetry via Serial JSON

### Phase 2 — Community Scale (10,000 L/day)
- [ ] ESP32 cluster with CAN-bus orchestration
- [ ] Full CDI+MED switching based on TDS
- [ ] ZLD evaporation pond
- [ ] Sovereignty One dashboard integration (live telemetry)

### Phase 3 — Industrial (100,000 L/day)
- [ ] Plasma oxidation tertiary stage
- [ ] Automated brine mineral extraction
- [ ] Grid tie-in or full off-grid PV+battery
- [ ] Predictive maintenance via AI core

### Phase 4 — ISRU (In-Situ Resource Utilisation)
- [ ] Regolith water extraction (lunar / asteroid)
- [ ] Ice sublimation + CDI polishing
- [ ] Europa brine processing (long-term)

---

## Software Build Checklist

- [x] `ai_core/sovereign_bridge.py` — Python sovereign AI bridge
- [x] `ai_core/providers/local_inference.py` — GGUF/ONNX local providers
- [x] `ai_core/providers/sovereign_api.py` — self-hosted API provider
- [x] `node-bridge/sovereign_bridge.mjs` — Node.js WebSocket bridge
- [x] `db/schema.sql` — full Postgres schema
- [x] `db/connector.py` — psycopg2 connector
- [x] `backend/api/org.py` — org CRUD
- [x] `backend/api/project.py` — project CRUD
- [x] `backend/api/auth.py` — JWT auth
- [x] `backend/api/dashboard.py` — security dashboard
- [x] `backend/roles/roles_registry.py` — RBAC with all role tiers
- [x] `analytics/usage_tracker.py` — AI usage tracking
- [x] `analytics/audit_logger.py` — immutable audit trail
- [x] `firmware/esp32_controller.ino` — ESP32 water system controller
- [x] `docker-compose.yml` — self-hosted stack (no Ollama)

---

## Grant Proposal Summary

**Title:** Sovereignty One — Zero-Vendor Water Sovereignty Platform

**Problem:** 2.2 billion people lack access to safe drinking water.
Existing solutions depend on expensive imported components and proprietary SaaS control systems.

**Solution:** A fully open-source, self-manufactured CDI+MED hybrid water system
controlled by an ESP32 running sovereign firmware, integrated with a local AI monitoring platform.

**Impact:** One pilot unit provides clean water for 50 households.
Phase 2 serves a village of 500. Phase 3 serves a town of 5,000.

**Budget Ask:** $2.4M for 3-year pilot program (10 pilot units across 3 continents).

---

## Future Vision

*From the oceans of Europa to the ice caps of Mars — wherever water exists in the universe,
Sovereignty One will be there to purify it.*

The same ESP32 firmware that controls a village water pump in Kenya today
will control a brine extraction system on a Jupiter moon tomorrow.
Sovereignty is not a destination — it is a trajectory.

---

*Documentation maintained by the Sovereignty AI Studio sovereign agent network.*
*Last updated: 2026-03-18*

---

## Local Inference Setup


```
Requires: `pip install openAi
### ONNX Models
`ONNXProvider` in `ai_core/providers/local_inference.py` provides a base class.
Because ONNX models have model-specific input/output tensor names, you must subclass it:
```python
from ai_core.providers.local_inference import ONNXProvider

class MyONNXProvider(ONNXProvider):
    def chat(self, messages, *, context=None, max_tokens=1200, stream=False):
        self._load_model()
        prompt = _messages_to_prompt(messages)
        # Bind inputs specific to your model
        inputs = {self._session.get_inputs()[0].name: [[prompt]]}
        outputs = self._session.run(None, inputs)
        return outputs[0][0]
```
Register your subclass in `ai_core/sovereign_bridge.py` by extending `_load_provider()`.

### Sovereign API
Point to any self-hosted LLM API that accepts OpenAI-compatible chat completions:
```bash
SOVEREIGN_API_URL=http://my-llm-server:9898/v1
SOVEREIGN_API_JWT=your-jwt-token
```
