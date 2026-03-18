/**
 * Sovereignty One - ESP32 CDI/MED/Plasma Hybrid Controller
 * Capacitive Deionization + Multi-Effect Distillation + Plasma ZLD
 *
 * Hardware: ESP32-S3 DevKit
 * Sensors:  TDS, pH, ORP, Temperature, Pressure, Flow, Level
 * Actuators: Pumps, Valves, Heaters, Plasma Electrode Driver
 */

#include <Arduino.h>
#include <Wire.h>
#include <SPI.h>
#include <WiFi.h>
#include <ArduinoJson.h>

// ──────────────────────────────────────────────
// Pin Definitions
// ──────────────────────────────────────────────
#define CDI_PUMP_PIN       GPIO_NUM_4
#define MED_PUMP_PIN       GPIO_NUM_5
#define PLASMA_ENABLE_PIN  GPIO_NUM_6
#define BRINE_VALVE_PIN    GPIO_NUM_7
#define PRODUCT_VALVE_PIN  GPIO_NUM_8
#define ANTISCALE_PIN      GPIO_NUM_9

#define TDS_SENSOR_PIN     GPIO_NUM_34
#define PH_SENSOR_PIN      GPIO_NUM_35
#define ORP_SENSOR_PIN     GPIO_NUM_36
#define TEMP_SENSOR_PIN    GPIO_NUM_37
#define FLOW_SENSOR_PIN    GPIO_NUM_38
#define PRESSURE_PIN       GPIO_NUM_39
#define PV_VOLTAGE_PIN     GPIO_NUM_32
#define PV_CURRENT_PIN     GPIO_NUM_33

// ──────────────────────────────────────────────
// System Parameters
// ──────────────────────────────────────────────
const float ADC_MAX             = 4095.0;  // 12-bit ADC (ESP32)
const float ADC_VREF            = 3.3;     // Reference voltage (V)
const float TDS_TARGET_PPM      = 50.0;
const float TDS_MAX_FEED_PPM    = 45000.0;
const float PH_SAFE_MIN         = 6.0;
const float PH_SAFE_MAX         = 8.5;
const float ORP_MIN_MV          = -200.0;
const float PRESSURE_MAX_BAR    = 6.0;
const float TEMP_MAX_C          = 85.0;
const unsigned long CDI_CYCLE_MS    = 300000;  // 5 min per CDI cycle
const unsigned long ANTISCALE_MS    = 3600000; // Anti-scale flush every 60 min
const unsigned long PLASMA_PULSE_MS = 5000;    // Plasma burst duration

// ──────────────────────────────────────────────
// State Machine
// ──────────────────────────────────────────────
enum SystemMode {
  MODE_IDLE,
  MODE_CDI_CHARGE,
  MODE_CDI_DISCHARGE,
  MODE_MED_EVAP,
  MODE_PLASMA_ZLD,
  MODE_ANTISCALE,
  MODE_FAULT
};

SystemMode currentMode = MODE_IDLE;
bool safetyTripped = false;

// Sensor readings (updated in loop)
float tds_ppm     = 0.0;
float ph_val      = 7.0;
float orp_mv      = 0.0;
float temp_c      = 25.0;
float pressure_bar= 0.0;
float flow_lpm    = 0.0;
float pv_voltage  = 0.0;
float pv_current  = 0.0;
float pv_power    = 0.0;

unsigned long lastCdiCycle    = 0;
unsigned long lastAntiscale   = 0;
unsigned long modeStartTime   = 0;
unsigned long antiscaleStart  = 0;
const unsigned long ANTISCALE_FLUSH_MS = 30000; // 30s non-blocking flush

// ──────────────────────────────────────────────
// Sensor Reading Functions
// ──────────────────────────────────────────────
float readTDS() {
  int raw = analogRead(TDS_SENSOR_PIN);
  // TDS probe: 3V3 ref, 1024 steps, calibration factor 0.5
  float voltage = raw * (ADC_VREF / ADC_MAX);
  return voltage * 1000.0 * 0.5 * (1.0 / (1.0 + 0.02 * (temp_c - 25.0)));
}

float readPH() {
  int raw = analogRead(PH_SENSOR_PIN);
  float voltage = raw * (ADC_VREF / ADC_MAX);
  return 3.5 * voltage + 0.0; // linear calibration
}

float readORP() {
  int raw = analogRead(ORP_SENSOR_PIN);
  float voltage = raw * (ADC_VREF / ADC_MAX) - (ADC_VREF / 2.0);
  return voltage * 1000.0; // mV
}

float readTemp() {
  int raw = analogRead(TEMP_SENSOR_PIN);
  float voltage = raw * (ADC_VREF / ADC_MAX);
  return (voltage - 0.5) * 100.0; // LM35: 10mV/°C, offset 500mV
}

float readPressure() {
  int raw = analogRead(PRESSURE_PIN);
  float voltage = raw * (ADC_VREF / ADC_MAX);
  return (voltage / 3.3) * PRESSURE_MAX_BAR;
}

float readFlow() {
  // Pulse-counting flow meter — simplified for analog reading here
  int raw = analogRead(FLOW_SENSOR_PIN);
  return raw * (10.0 / ADC_MAX); // 0–10 LPM range
}

void readPVMonitor() {
  int vRaw = analogRead(PV_VOLTAGE_PIN);
  int iRaw = analogRead(PV_CURRENT_PIN);
  pv_voltage = vRaw * (60.0 / ADC_MAX);   // 0–60V
  pv_current = iRaw * (20.0 / ADC_MAX);   // 0–20A
  pv_power   = pv_voltage * pv_current;
}

// ──────────────────────────────────────────────
// Safety Interlock
// ──────────────────────────────────────────────
bool checkSafetyInterlocks() {
  if (temp_c > TEMP_MAX_C) {
    Serial.println("FAULT: Overtemperature");
    return false;
  }
  if (pressure_bar > PRESSURE_MAX_BAR) {
    Serial.println("FAULT: Overpressure");
    return false;
  }
  if (ph_val < PH_SAFE_MIN || ph_val > PH_SAFE_MAX) {
    Serial.println("FAULT: pH out of safe range");
    return false;
  }
  if (tds_ppm > TDS_MAX_FEED_PPM) {
    Serial.println("FAULT: Feed TDS exceeds maximum");
    return false;
  }
  return true;
}

// ──────────────────────────────────────────────
// Actuator Control
// ──────────────────────────────────────────────
void allActuatorsOff() {
  digitalWrite(CDI_PUMP_PIN,    LOW);
  digitalWrite(MED_PUMP_PIN,    LOW);
  digitalWrite(PLASMA_ENABLE_PIN, LOW);
  digitalWrite(BRINE_VALVE_PIN, LOW);
  digitalWrite(PRODUCT_VALVE_PIN, LOW);
  digitalWrite(ANTISCALE_PIN,   LOW);
}

void runCDICharge() {
  digitalWrite(CDI_PUMP_PIN,    HIGH);
  digitalWrite(PRODUCT_VALVE_PIN, HIGH);
  digitalWrite(BRINE_VALVE_PIN, LOW);
}

void runCDIDischarge() {
  digitalWrite(CDI_PUMP_PIN,    HIGH);
  digitalWrite(BRINE_VALVE_PIN, HIGH);
  digitalWrite(PRODUCT_VALVE_PIN, LOW);
}

void runMEDEvaporation() {
  digitalWrite(MED_PUMP_PIN,    HIGH);
  digitalWrite(PRODUCT_VALVE_PIN, HIGH);
}

void runPlasmaZLD() {
  digitalWrite(PLASMA_ENABLE_PIN, HIGH);
  digitalWrite(BRINE_VALVE_PIN,   HIGH);
}

void runAntiscale() {
  unsigned long now = millis();
  if (antiscaleStart == 0) {
    // Begin flush cycle
    antiscaleStart = now;
    digitalWrite(ANTISCALE_PIN, HIGH);
    digitalWrite(CDI_PUMP_PIN,  HIGH);
  } else if (now - antiscaleStart >= ANTISCALE_FLUSH_MS) {
    // Flush complete — return to idle
    digitalWrite(ANTISCALE_PIN, LOW);
    digitalWrite(CDI_PUMP_PIN,  LOW);
    antiscaleStart = 0;
    currentMode = MODE_IDLE;
  }
  // Safety checks continue to run normally between calls
}

// ──────────────────────────────────────────────
// Mode Selection Logic
// ──────────────────────────────────────────────
SystemMode selectMode() {
  unsigned long now = millis();

  // Anti-scale takes priority (maintenance cycle)
  if (now - lastAntiscale > ANTISCALE_MS) {
    lastAntiscale = now;
    return MODE_ANTISCALE;
  }

  // Use available PV power budget to select mode
  if (pv_power > 500.0) {
    // Plenty of solar — run plasma ZLD on brine
    if (tds_ppm > 5000.0) return MODE_PLASMA_ZLD;
    // Run CDI for primary desalination
    unsigned long elapsed = now - lastCdiCycle;
    if (elapsed > CDI_CYCLE_MS) {
      lastCdiCycle = now;
      return (currentMode == MODE_CDI_CHARGE) ? MODE_CDI_DISCHARGE : MODE_CDI_CHARGE;
    }
    return currentMode;
  } else if (pv_power > 200.0) {
    // Moderate power — MED evaporation
    return MODE_MED_EVAP;
  } else {
    // Low power — idle
    return MODE_IDLE;
  }
}

// ──────────────────────────────────────────────
// Telemetry
// ──────────────────────────────────────────────
void sendTelemetry() {
  StaticJsonDocument<512> doc;
  doc["tds"]       = tds_ppm;
  doc["ph"]        = ph_val;
  doc["orp"]       = orp_mv;
  doc["temp"]      = temp_c;
  doc["pressure"]  = pressure_bar;
  doc["flow"]      = flow_lpm;
  doc["pv_v"]      = pv_voltage;
  doc["pv_a"]      = pv_current;
  doc["pv_w"]      = pv_power;
  doc["mode"]      = (int)currentMode;
  doc["safety_ok"] = !safetyTripped;
  serializeJson(doc, Serial);
  Serial.println();
}

// ──────────────────────────────────────────────
// Setup
// ──────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  Serial.println("Sovereignty One - CDI/MED/Plasma Hybrid Controller v1.0");

  pinMode(CDI_PUMP_PIN,     OUTPUT);
  pinMode(MED_PUMP_PIN,     OUTPUT);
  pinMode(PLASMA_ENABLE_PIN,OUTPUT);
  pinMode(BRINE_VALVE_PIN,  OUTPUT);
  pinMode(PRODUCT_VALVE_PIN,OUTPUT);
  pinMode(ANTISCALE_PIN,    OUTPUT);

  allActuatorsOff();
  lastAntiscale = millis();
  lastCdiCycle  = millis();
}

// ──────────────────────────────────────────────
// Main Loop
// ──────────────────────────────────────────────
void loop() {
  // 1. Read all sensors
  tds_ppm      = readTDS();
  ph_val       = readPH();
  orp_mv       = readORP();
  temp_c       = readTemp();
  pressure_bar = readPressure();
  flow_lpm     = readFlow();
  readPVMonitor();

  // 2. Safety check
  if (!checkSafetyInterlocks()) {
    allActuatorsOff();
    safetyTripped = true;
    currentMode = MODE_FAULT;
    sendTelemetry();
    delay(5000);
    return;
  }
  safetyTripped = false;

  // 3. Mode selection and execution
  currentMode = selectMode();
  switch (currentMode) {
    case MODE_CDI_CHARGE:    runCDICharge();    break;
    case MODE_CDI_DISCHARGE: runCDIDischarge(); break;
    case MODE_MED_EVAP:      runMEDEvaporation(); break;
    case MODE_PLASMA_ZLD:    runPlasmaZLD();    break;
    case MODE_ANTISCALE:     runAntiscale();    break;
    case MODE_IDLE:
    default:                 allActuatorsOff(); break;
  }

  // 4. Send telemetry every 5 seconds
  static unsigned long lastTelemetry = 0;
  if (millis() - lastTelemetry > 5000) {
    sendTelemetry();
    lastTelemetry = millis();
  }

  delay(500);
}
