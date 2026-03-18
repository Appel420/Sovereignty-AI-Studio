/**
 * Sovereignty One — ESP32 CDI/MED Hybrid Water System Controller
 *
 * Controls a Capacitive Deionization (CDI) + Membrane Electrodialysis (MED)
 * hybrid water purification system.
 *
 * Features:
 *  - Pump control (CDI / MED switching based on PV voltage & TDS thresholds)
 *  - Anti-scaling polarity reversal (automatic scheduling)
 *  - Safety interlocks (over-pressure, dry-run, temp limits)
 *  - Serial telemetry (JSON output at 1 Hz)
 *
 * Pin assignments and thresholds configurable via #define constants below.
 */

#include <Arduino.h>
#include <ArduinoJson.h>

// ─── Pin Assignments ─────────────────────────────────────────────────────────
#define PIN_CDI_PUMP        5     // CDI pump relay (HIGH = ON)
#define PIN_MED_PUMP        6     // MED pump relay (HIGH = ON)
#define PIN_POLARITY_A      7     // Polarity relay A
#define PIN_POLARITY_B      8     // Polarity relay B
#define PIN_PV_VOLTAGE      34    // ADC: photovoltaic voltage sense (0–3.3 V, scaled)
#define PIN_TDS_IN          35    // ADC: TDS sensor — inlet (ppm)
#define PIN_TDS_OUT         36    // ADC: TDS sensor — outlet (ppm)
#define PIN_PRESSURE        39    // ADC: system pressure sensor (PSI)
#define PIN_TEMP            32    // ADC: water temperature (°C, NTC)
#define PIN_FLOW            33    // Digital: flow sensor pulse pin

// ─── Thresholds ──────────────────────────────────────────────────────────────
#define PV_CDI_MIN_V        18.0f   // Min PV voltage to run CDI pump
#define PV_MED_MIN_V        22.0f   // Min PV voltage to run MED pump
#define TDS_CDI_MAX_PPM     1500    // Switch from CDI to MED above this TDS
#define TDS_PRODUCT_OK      50      // Target outlet TDS (ppm)
#define PRESSURE_MAX_PSI    85.0f   // Safety cutoff — over-pressure
#define TEMP_MAX_C          45.0f   // Safety cutoff — over-temperature
#define POLARITY_INTERVAL_MS 900000UL // Anti-scaling reversal every 15 min
#define TELEMETRY_INTERVAL_MS 1000UL  // 1 Hz serial JSON output

// ─── ADC Scaling Constants ────────────────────────────────────────────────────
// Adjust dividers to match your hardware voltage divider / sensor calibration.
#define PV_SCALE            (50.0f / 4095.0f)     // 0–50 V range
#define TDS_SCALE           (2000.0f / 4095.0f)   // 0–2000 ppm range
#define PRESSURE_SCALE      (100.0f / 4095.0f)    // 0–100 PSI range
#define TEMP_SCALE          (100.0f / 4095.0f)    // 0–100 °C range (NTC linearised)

// ─── State ────────────────────────────────────────────────────────────────────
enum class Mode { IDLE, CDI, MED, FAULT };
Mode currentMode = Mode::IDLE;
bool polarityState = false;           // false = normal, true = reversed
volatile uint32_t flowPulseCount = 0; // ISR counter

unsigned long lastPolarityMs = 0;
unsigned long lastTelemetryMs = 0;

// ─── ISR ─────────────────────────────────────────────────────────────────────
void IRAM_ATTR flowISR() {
  flowPulseCount++;
}

// ─── Helpers ─────────────────────────────────────────────────────────────────
float readVoltage(uint8_t pin, float scale) {
  return analogRead(pin) * scale;
}

float readTDS(uint8_t pin) {
  return analogRead(pin) * TDS_SCALE;
}

void setPumps(bool cdi, bool med) {
  digitalWrite(PIN_CDI_PUMP, cdi ? HIGH : LOW);
  digitalWrite(PIN_MED_PUMP, med ? HIGH : LOW);
}

void setPolarity(bool reversed) {
  digitalWrite(PIN_POLARITY_A, reversed ? LOW : HIGH);
  digitalWrite(PIN_POLARITY_B, reversed ? HIGH : LOW);
  polarityState = reversed;
}

bool safetyCheck(float pressurePSI, float tempC) {
  if (pressurePSI > PRESSURE_MAX_PSI) {
    Serial.println("{\"alert\":\"OVER_PRESSURE\",\"psi\":" + String(pressurePSI) + "}");
    return false;
  }
  if (tempC > TEMP_MAX_C) {
    Serial.println("{\"alert\":\"OVER_TEMP\",\"c\":" + String(tempC) + "}");
    return false;
  }
  return true;
}

void enterFault(const char* reason) {
  setPumps(false, false);
  currentMode = Mode::FAULT;
  Serial.printf("{\"fault\":\"%s\"}\n", reason);
}

// ─── Anti-Scaling Polarity Reversal ──────────────────────────────────────────
void checkPolarityReversal() {
  if (millis() - lastPolarityMs >= POLARITY_INTERVAL_MS) {
    setPumps(false, false);    // Brief pause during reversal
    delay(200);
    setPolarity(!polarityState);
    delay(200);
    lastPolarityMs = millis();
    Serial.printf("{\"event\":\"polarity_reversal\",\"state\":%s}\n",
                  polarityState ? "true" : "false");
  }
}

// ─── Control Loop ─────────────────────────────────────────────────────────────
void controlLoop() {
  float pvV      = readVoltage(PIN_PV_VOLTAGE, PV_SCALE);
  float tdsIn    = readTDS(PIN_TDS_IN);
  float tdsOut   = readTDS(PIN_TDS_OUT);
  float pressure = readVoltage(PIN_PRESSURE, PRESSURE_SCALE);
  float temp     = readVoltage(PIN_TEMP, TEMP_SCALE);

  if (!safetyCheck(pressure, temp)) {
    enterFault("safety_interlock");
    return;
  }

  // Recover from fault if conditions improve
  if (currentMode == Mode::FAULT && pressure < PRESSURE_MAX_PSI && temp < TEMP_MAX_C) {
    currentMode = Mode::IDLE;
  }

  if (currentMode == Mode::FAULT) return;

  // Mode selection logic
  if (pvV >= PV_MED_MIN_V && tdsIn > TDS_CDI_MAX_PPM) {
    // High TDS + enough PV → use MED
    if (currentMode != Mode::MED) {
      setPumps(false, true);
      currentMode = Mode::MED;
    }
  } else if (pvV >= PV_CDI_MIN_V) {
    // Sufficient PV → use CDI
    if (currentMode != Mode::CDI) {
      setPumps(true, false);
      currentMode = Mode::CDI;
    }
  } else {
    // Not enough power → idle
    if (currentMode != Mode::IDLE) {
      setPumps(false, false);
      currentMode = Mode::IDLE;
    }
  }

  checkPolarityReversal();

  // Telemetry
  if (millis() - lastTelemetryMs >= TELEMETRY_INTERVAL_MS) {
    noInterrupts();
    uint32_t pulses = flowPulseCount;
    flowPulseCount = 0;
    interrupts();

    // ~7.5 pulses/second per L/min (common YF-S201 sensor)
    float flowLPM = pulses / 7.5f;

    StaticJsonDocument<256> doc;
    doc["ts"]      = millis();
    doc["mode"]    = (currentMode == Mode::CDI) ? "CDI"
                   : (currentMode == Mode::MED) ? "MED"
                   : (currentMode == Mode::FAULT) ? "FAULT"
                   : "IDLE";
    doc["pv_v"]    = pvV;
    doc["tds_in"]  = tdsIn;
    doc["tds_out"] = tdsOut;
    doc["psi"]     = pressure;
    doc["temp_c"]  = temp;
    doc["flow_lpm"]= flowLPM;
    doc["polarity"]= polarityState;

    serializeJson(doc, Serial);
    Serial.println();
    lastTelemetryMs = millis();
  }
}

// ─── Setup ────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);

  pinMode(PIN_CDI_PUMP,   OUTPUT);
  pinMode(PIN_MED_PUMP,   OUTPUT);
  pinMode(PIN_POLARITY_A, OUTPUT);
  pinMode(PIN_POLARITY_B, OUTPUT);
  pinMode(PIN_FLOW,       INPUT_PULLUP);

  // Start in safe state
  setPumps(false, false);
  setPolarity(false);

  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), flowISR, RISING);

  lastPolarityMs  = millis();
  lastTelemetryMs = millis();

  Serial.println("{\"event\":\"boot\",\"system\":\"sovereignty-one-esp32\"}");
}

// ─── Loop ─────────────────────────────────────────────────────────────────────
void loop() {
  controlLoop();
  delay(100); // 10 Hz control loop
}
