/*
 * SENTINEL · ESP32/LoRa field node
 * -----------------------------------------------------------------------------
 * Reads the environmental channels, a manual SOS button and battery state,
 * then transmits a JSON packet to the sector LoRa gateway.
 *
 * Board:      ESP32 DevKit v1 (or equivalent)
 * Radio:      SX1276 / RFM95W, 865-867 MHz (India)
 * Libraries:  LoRa (sandeepmistry), DHT sensor library (Adafruit),
 *             ArduinoJson 7.x, TinyGPSPlus (mikalhart)
 *
 * The node is deliberately offline: it has no WiFi and no server credentials.
 * The gateway owns the authenticated uplink. Every field below maps 1:1 to the
 * server contract in docs/payload-schema.md.
 */

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <DHT.h>
#include <ArduinoJson.h>
#include <TinyGPSPlus.h>
#include <math.h>

// ── Commissioning ────────────────────────────────────────────────────────────
// Change these four values per physical node before flashing.
#define NODE_ID          "SN-NASH-01"
#define SITE_LAT          19.9975f
#define SITE_LON          73.7898f
#define WATER_MOUNT_CM    200.0f   // distance from sensor face to dry river bed

// ── Pin map ──────────────────────────────────────────────────────────────────
#define PIN_LORA_SCK      18
#define PIN_LORA_MISO     19
#define PIN_LORA_MOSI     23
#define PIN_LORA_SS       5
#define PIN_LORA_RST      14
#define PIN_LORA_DIO0     26

#define PIN_DHT           4
#define PIN_RAIN          27
#define PIN_TRIG          32
#define PIN_ECHO          33
#define PIN_VIBRATION     25
#define PIN_MQ135         34
#define PIN_SOS           13
#define PIN_BATTERY       35
#define PIN_STATUS_LED    2
#define PIN_GPS_RX        16        // GPS TX -> ESP32 RX
#define PIN_GPS_TX        17        // GPS RX -> ESP32 TX

// ── Timing ───────────────────────────────────────────────────────────────────
constexpr uint32_t SEND_INTERVAL_MS    = 60UL * 1000UL;
constexpr uint32_t FIRST_SEND_DELAY_MS = 10UL * 1000UL;
constexpr uint32_t VIBRATION_WINDOW_MS = 5000UL;
constexpr uint32_t GPS_BAUD = 9600;

// ── Calibration constants ────────────────────────────────────────────────────
constexpr float RAIN_MM_PER_TIP = 0.2794f;   // common tipping-bucket resolution
constexpr uint32_t BATTERY_DIVIDER = 2;      // 100k/100k divider on ADC35
constexpr float MQ135_RL_KOHM = 10.0f;       // load resistor on the MQ-135 board
constexpr float MQ135_R0_KOHM = 3.6f;        // calibrate against clean air
constexpr float ADC_REF_VOLTS = 3.3f;
constexpr uint32_t SOS_HOLD_MS = 600;        // deliberate press, not a bump
constexpr float LORA_FREQUENCY = 866E6f;     // 865-867 MHz for India

DHT dht(PIN_DHT, DHT22);
TinyGPSPlus gps;
HardwareSerial gpsSerial(2);

volatile uint32_t rainTips = 0;
volatile uint32_t vibrationPulses = 0;

float lastTemp = NAN;
float lastHumidity = NAN;
float lastWaterLevel = 0.0f;
uint32_t lastRainReadMs = 0;
uint32_t nextSendAt = 0;
uint32_t sendSequence = 0;
bool sosLatched = false;
uint32_t sosDownAt = 0;

void IRAM_ATTR onRainTip() {
  rainTips++;
}

void IRAM_ATTR onVibration() {
  vibrationPulses++;
}

void blink(uint8_t times, uint16_t durationMs) {
  for (uint8_t index = 0; index < times; index++) {
    digitalWrite(PIN_STATUS_LED, HIGH);
    delay(durationMs);
    digitalWrite(PIN_STATUS_LED, LOW);
    if (index + 1 < times) delay(durationMs);
  }
}

bool initLoRa() {
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_SS);
  LoRa.setPins(PIN_LORA_SS, PIN_LORA_RST, PIN_LORA_DIO0);

  for (uint8_t attempt = 0; attempt < 5; attempt++) {
    if (LoRa.begin(LORA_FREQUENCY)) {
      LoRa.setTxPower(17);
      LoRa.setSpreadingFactor(9);
      LoRa.setSignalBandwidth(125E3);
      LoRa.setCodingRate4(5);
      LoRa.setPreambleLength(8);
      LoRa.setSyncWord(0x12);
      LoRa.enableCrc();
      return true;
    }
    Serial.printf("[lora] init attempt %u failed\n", attempt + 1);
    delay(2000);
  }
  return false;
}

void pollGps() {
  while (gpsSerial.available() > 0) {
    gps.encode(gpsSerial.read());
  }
}

void pollSos() {
  const bool pressed = digitalRead(PIN_SOS) == LOW;
  if (!pressed) {
    sosDownAt = 0;
    return;
  }
  if (sosDownAt == 0) {
    sosDownAt = millis();
  } else if (millis() - sosDownAt >= SOS_HOLD_MS) {
    sosLatched = true;
  }
}

bool readClimate(float &temperature, float &humidity) {
  // DHT22 occasionally returns NaN immediately after power-up; keep the last
  // valid pair and retry rather than emitting a value the server must reject.
  for (uint8_t attempt = 0; attempt < 3; attempt++) {
    const float t = dht.readTemperature();
    const float h = dht.readHumidity();
    if (!isnan(t) && !isnan(h)) {
      lastTemp = t;
      lastHumidity = h;
      break;
    }
    delay(120);
  }
  if (isnan(lastTemp) || isnan(lastHumidity)) return false;
  temperature = lastTemp;
  humidity = lastHumidity;
  return true;
}

long readDistanceCm() {
  digitalWrite(PIN_TRIG, LOW);
  delayMicroseconds(2);
  digitalWrite(PIN_TRIG, HIGH);
  delayMicroseconds(10);
  digitalWrite(PIN_TRIG, LOW);

  const unsigned long duration = pulseIn(PIN_ECHO, HIGH, 30000UL);
  if (duration == 0) return -1;
  return static_cast<long>((duration * 0.0343f) / 2.0f);
}

float readWaterLevel() {
  long samples[7];
  uint8_t valid = 0;
  for (uint8_t index = 0; index < 7; index++) {
    const long distance = readDistanceCm();
    if (distance > 2 && distance < WATER_MOUNT_CM + 100) {
      samples[valid++] = distance;
    }
    delay(60);
  }
  if (valid == 0) return lastWaterLevel;

  // Insertion sort: a median rejects splashes and the odd ultrasonic outlier.
  for (uint8_t i = 1; i < valid; i++) {
    const long value = samples[i];
    int8_t j = i - 1;
    while (j >= 0 && samples[j] > value) {
      samples[j + 1] = samples[j];
      j--;
    }
    samples[j + 1] = value;
  }
  const float medianDistance = samples[valid / 2];
  const float level = WATER_MOUNT_CM - medianDistance;
  lastWaterLevel = constrain(level, 0.0f, 1500.0f);
  return lastWaterLevel;
}

float readRainRate() {
  noInterrupts();
  const uint32_t tips = rainTips;
  rainTips = 0;
  interrupts();

  const uint32_t now = millis();
  const float elapsedSeconds = max(1.0f, (now - lastRainReadMs) / 1000.0f);
  lastRainReadMs = now;
  const float rate = tips * RAIN_MM_PER_TIP * (3600.0f / elapsedSeconds);
  return constrain(rate, 0.0f, 500.0f);
}

float estimateAqiFromPpm(float ppm) {
  // Piecewise interpolation over a representative MQ-135 response curve. The
  // result is an AQI-equivalent public-health index, not a certified PM2.5
  // measurement. Recalibrate at commissioning (see docs/esp32-integration.md).
  static const float ppmPoints[] = { 10.0f, 50.0f, 100.0f, 200.0f, 400.0f, 1000.0f, 3000.0f };
  static const float aqiPoints[] = { 0.0f, 25.0f, 50.0f, 100.0f, 150.0f, 300.0f, 500.0f };
  constexpr uint8_t pointCount = sizeof(ppmPoints) / sizeof(ppmPoints[0]);

  if (ppm <= ppmPoints[0]) return 0.0f;
  for (uint8_t index = 1; index < pointCount; index++) {
    if (ppm <= ppmPoints[index]) {
      const float span = ppmPoints[index] - ppmPoints[index - 1];
      const float ratio = (ppm - ppmPoints[index - 1]) / span;
      return aqiPoints[index - 1] + ratio * (aqiPoints[index] - aqiPoints[index - 1]);
    }
  }
  return 500.0f;
}

float readAqi() {
  const uint16_t raw = analogRead(PIN_MQ135);
  if (raw < 20) return 0.0f;

  const float volts = (raw / 4095.0f) * ADC_REF_VOLTS;
  if (volts >= ADC_REF_VOLTS - 0.01f) return 500.0f;

  const float rsKohm = ((ADC_REF_VOLTS - volts) / volts) * MQ135_RL_KOHM;
  const float ratio = rsKohm / MQ135_R0_KOHM;
  const float ppm = 116.6020682f * powf(ratio, -2.769034857f);
  return constrain(estimateAqiFromPpm(ppm), 0.0f, 1000.0f);
}

float readBatteryVoltage() {
  const uint32_t millivolts = analogReadMilliVolts(PIN_BATTERY);
  const float volts = (millivolts / 1000.0f) * BATTERY_DIVIDER;
  if (volts < 1.0f || volts > 5.5f) return 3.70f;
  return volts;
}

uint8_t readVibrationLevel() {
  const uint32_t startPulses = vibrationPulses;
  const uint32_t started = millis();
  while (millis() - started < VIBRATION_WINDOW_MS) {
    pollSos();
    delay(10);
  }
  const uint32_t pulses = vibrationPulses - startPulses;
  const uint32_t scaled = pulses * 8UL;
  return static_cast<uint8_t>(scaled > 100UL ? 100UL : scaled);
}

void useGpsOrCommissionedFix(double &latitude, double &longitude) {
  pollGps();
  if (gps.location.isValid() && gps.location.age() < 10000) {
    latitude = gps.location.lat();
    longitude = gps.location.lng();
  } else {
    latitude = SITE_LAT;
    longitude = SITE_LON;
  }
}

String makePacketId() {
  char identifier[64];
  snprintf(identifier, sizeof(identifier), "%s-%08X-%lu", NODE_ID,
           static_cast<uint32_t>(ESP.getEfuseMac()), static_cast<unsigned long>(++sendSequence));
  return String(identifier);
}

bool transmit(const String &payload) {
  for (uint8_t attempt = 0; attempt < 3; attempt++) {
    LoRa.beginPacket();
    LoRa.print(payload);
    if (LoRa.endPacket()) return true;
    Serial.printf("[lora] TX attempt %u failed\n", attempt + 1);
    delay(250);
  }
  return false;
}

void sendReading() {
  float temperature = 0.0f;
  float humidity = 0.0f;
  if (!readClimate(temperature, humidity)) {
    Serial.println("[sensor] DHT22 unavailable; packet skipped");
    return;
  }

  double latitude = SITE_LAT;
  double longitude = SITE_LON;
  useGpsOrCommissionedFix(latitude, longitude);

  const float waterLevel = readWaterLevel();
  const float rain = readRainRate();
  const uint8_t vibration = readVibrationLevel();
  const float aqi = readAqi();
  const float battery = readBatteryVoltage();
  pollSos();

  JsonDocument document;
  document["nodeId"] = NODE_ID;
  document["lat"] = latitude;
  document["lon"] = longitude;
  document["temp"] = temperature;
  document["humidity"] = humidity;
  document["rain"] = rain;
  document["waterLevel"] = waterLevel;
  document["vibration"] = vibration;
  document["aqi"] = aqi;
  document["sos"] = sosLatched;
  document["battery"] = battery;
  document["packetId"] = makePacketId();

  String payload;
  serializeJson(document, payload);

  digitalWrite(PIN_STATUS_LED, HIGH);
  const bool sent = transmit(payload);
  digitalWrite(PIN_STATUS_LED, LOW);

  if (sent) {
    Serial.printf("[lora] sent %s\n", payload.c_str());
    if (sosLatched && digitalRead(PIN_SOS) == HIGH) sosLatched = false;
  } else {
    Serial.println("[lora] packet dropped after three attempts");
  }
}

void setup() {
  Serial.begin(115200);
  delay(250);

  pinMode(PIN_STATUS_LED, OUTPUT);
  pinMode(PIN_TRIG, OUTPUT);
  pinMode(PIN_ECHO, INPUT);
  pinMode(PIN_RAIN, INPUT_PULLUP);
  pinMode(PIN_VIBRATION, INPUT_PULLUP);
  pinMode(PIN_SOS, INPUT_PULLUP);

  analogReadResolution(12);
  analogSetPinAttenuation(PIN_BATTERY, ADC_11db);
  analogSetPinAttenuation(PIN_MQ135, ADC_11db);

  dht.begin();
  gpsSerial.begin(GPS_BAUD, SERIAL_8N1, PIN_GPS_RX, PIN_GPS_TX);

  attachInterrupt(digitalPinToInterrupt(PIN_RAIN), onRainTip, FALLING);
  attachInterrupt(digitalPinToInterrupt(PIN_VIBRATION), onVibration, FALLING);

  Serial.printf("\n[sentinel] node %s booting\n", NODE_ID);
  if (!initLoRa()) {
    Serial.println("[lora] radio not detected; restarting in 10 s");
    blink(12, 120);
    delay(10000);
    ESP.restart();
  }

  // Let the DHT and MQ-135 stabilize before the first uplink.
  delay(2000);
  lastRainReadMs = millis();
  nextSendAt = millis() + FIRST_SEND_DELAY_MS;
  blink(2, 120);
  Serial.println("[sentinel] ready");
}

void loop() {
  pollGps();
  pollSos();

  if (static_cast<int32_t>(millis() - nextSendAt) >= 0) {
    sendReading();
    nextSendAt = millis() + SEND_INTERVAL_MS;
  }

  delay(20);
}
