/*
 * SENTINEL · ESP32/LoRa sector gateway
 * -----------------------------------------------------------------------------
 * Receives JSON packets from field nodes over LoRa, adds link metadata and a
 * UTC timestamp, batches up to 24 readings, and posts them to the SENTINEL API.
 *
 * Board:      ESP32 DevKit v1 + SX1276/RFM95W (865-867 MHz, India)
 * Libraries:  LoRa (sandeepmistry), ArduinoJson 7.x
 * Setup:      copy secrets.example.h to secrets.h and set WiFi + server values.
 *
 * The HTTP path is authenticated with X-Gateway-Key. An equivalent WebSocket
 * uplink is documented in docs/esp32-integration.md.
 */

#include <Arduino.h>
#include <SPI.h>
#include <LoRa.h>
#include <WiFi.h>
#include <HTTPClient.h>
#include <ArduinoJson.h>
#include <time.h>
#include "secrets.h"

#ifndef WIFI_SSID
#error "Create firmware/sentinel-gateway/secrets.h from secrets.example.h"
#endif

// ── Pin map (same radio wiring as the node) ──────────────────────────────────
#define PIN_LORA_SCK    18
#define PIN_LORA_MISO   19
#define PIN_LORA_MOSI   23
#define PIN_LORA_SS     5
#define PIN_LORA_RST    14
#define PIN_LORA_DIO0   26
#define PIN_STATUS_LED  2

// ── Gateway configuration ────────────────────────────────────────────────────
#define GATEWAY_ID      "GW-NSK-01"
#define FIRMWARE_ID     "sentinel-gw 1.5.0"
constexpr float LORA_FREQUENCY = 866E6f;
constexpr uint8_t MAX_BATCH = 24;
constexpr uint32_t FLUSH_INTERVAL_MS = 10000;
constexpr uint32_t WIFI_RETRY_MS = 15000;
constexpr size_t MAX_PACKET_CHARS = 1024;
constexpr size_t DEDUPE_SLOTS = 32;

String pending[MAX_BATCH];
uint8_t pendingCount = 0;
uint32_t lastFlushMs = 0;
uint32_t lastWifiAttemptMs = 0;
uint32_t lastWifiOkMs = 0;

String seenIds[DEDUPE_SLOTS];
uint8_t seenIndex = 0;

bool timeConfigured = false;
uint32_t lastNtpSyncMs = 0;

bool isNumber(JsonVariantConst value) {
  return !value.isNull() && (value.is<float>() || value.is<int>() || value.is<long>() || value.is<double>());
}

String isoUtcNow() {
  const time_t now = time(nullptr);
  if (now < 1700000000) return "";
  struct tm timeinfo;
  gmtime_r(&now, &timeinfo);
  char buffer[24];
  strftime(buffer, sizeof(buffer), "%Y-%m-%dT%H:%M:%SZ", &timeinfo);
  return String(buffer);
}

bool seenPacket(const String &packetId) {
  for (uint8_t index = 0; index < DEDUPE_SLOTS; index++) {
    if (seenIds[index] == packetId) return true;
  }
  seenIds[seenIndex] = packetId;
  seenIndex = (seenIndex + 1) % DEDUPE_SLOTS;
  return false;
}

void dropOldestPending() {
  if (pendingCount == 0) return;
  for (uint8_t index = 1; index < pendingCount; index++) {
    pending[index - 1] = pending[index];
  }
  pendingCount--;
}

bool radioReady() {
  SPI.begin(PIN_LORA_SCK, PIN_LORA_MISO, PIN_LORA_MOSI, PIN_LORA_SS);
  LoRa.setPins(PIN_LORA_SS, PIN_LORA_RST, PIN_LORA_DIO0);

  for (uint8_t attempt = 0; attempt < 5; attempt++) {
    if (LoRa.begin(LORA_FREQUENCY)) {
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

bool ensureWifi() {
  if (WiFi.status() == WL_CONNECTED) {
    lastWifiOkMs = millis();
    return true;
  }

  const uint32_t now = millis();
  if (now - lastWifiAttemptMs < WIFI_RETRY_MS) return false;
  lastWifiAttemptMs = now;

  Serial.println("[wifi] reconnecting");
  WiFi.disconnect();
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  return false;
}

void ensureClock() {
  if (WiFi.status() != WL_CONNECTED) return;
  const uint32_t now = millis();
  if (!timeConfigured) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    timeConfigured = true;
    lastNtpSyncMs = now;
    Serial.println("[ntp] sync requested");
    return;
  }
  if (now - lastNtpSyncMs > 6UL * 60UL * 60UL * 1000UL) {
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    lastNtpSyncMs = now;
  }
}

void addReading(JsonDocument &document, int rssi, float snr) {
  const char *nodeId = document["nodeId"];
  if (nodeId == nullptr || strlen(nodeId) < 3) {
    Serial.println("[packet] rejected: missing nodeId");
    return;
  }

  const char *requiredNumbers[] = { "temp", "humidity", "rain", "waterLevel", "aqi", "battery" };
  for (const char *field : requiredNumbers) {
    if (!isNumber(document[field])) {
      Serial.printf("[packet] rejected %s: missing numeric %s\n", nodeId, field);
      return;
    }
  }

  const JsonVariant vibration = document["vibration"];
  if (vibration.isNull() || (!vibration.is<bool>() && !isNumber(vibration))) {
    Serial.printf("[packet] rejected %s: invalid vibration\n", nodeId);
    return;
  }
  if (!document["sos"].is<bool>()) document["sos"] = false;

  String packetId = document["packetId"] | "";
  if (packetId.length() == 0) {
    packetId = String("GW-") + String(static_cast<uint32_t>(ESP.getEfuseMac()), HEX) + "-" + String(millis());
    document["packetId"] = packetId;
  }
  if (seenPacket(packetId)) {
    Serial.printf("[packet] duplicate %s ignored\n", packetId.c_str());
    return;
  }

  document["rssi"] = rssi;
  document["snr"] = snr;
  if (document["timestamp"].isNull()) {
    const String timestamp = isoUtcNow();
    if (timestamp.length() > 0) document["timestamp"] = timestamp;
  }

  String serialized;
  serializeJson(document, serialized);
  if (serialized.length() > MAX_PACKET_CHARS) {
    Serial.printf("[packet] rejected %s: payload too large\n", nodeId);
    return;
  }

  if (pendingCount >= MAX_BATCH) flushBatch();
  if (pendingCount >= MAX_BATCH) {
    Serial.println("[batch] server unavailable; dropping oldest pending reading");
    dropOldestPending();
  }
  pending[pendingCount++] = serialized;
  Serial.printf("[batch] queued %s (%u/%u)\n", nodeId, pendingCount, MAX_BATCH);
}

void flushBatch() {
  if (pendingCount == 0) return;
  if (WiFi.status() != WL_CONNECTED) {
    Serial.println("[batch] WiFi down; keeping readings queued");
    return;
  }

  String body = String("{\"gatewayId\":\"") + GATEWAY_ID + "\",\"firmware\":\"" + FIRMWARE_ID + "\",\"readings\":[";
  for (uint8_t index = 0; index < pendingCount; index++) {
    if (index > 0) body += ',';
    body += pending[index];
  }
  body += "]}";

  HTTPClient http;
  const String endpoint = String(SENTINEL_URL) + "/api/v1/telemetry";
  http.setTimeout(12000);
  http.setReuse(false);
  if (!http.begin(endpoint)) {
    Serial.println("[http] unable to open connection");
    return;
  }
  http.addHeader("Content-Type", "application/json");
  http.addHeader("X-Gateway-Key", SENTINEL_GATEWAY_KEY);
  http.addHeader("X-Gateway-Id", GATEWAY_ID);

  const int status = http.POST(body);
  String response = http.getString();
  http.end();

  if (status == 202 || status == 200) {
    Serial.printf("[http] flushed %u readings (%d)\n", pendingCount, status);
    pendingCount = 0;
    lastFlushMs = millis();
    return;
  }

  Serial.printf("[http] flush failed (%d): %s\n", status, response.c_str());
  // A 4xx means the batch itself is invalid. Keep it would block the queue
  // forever, so discard after logging. Network/5xx failures are retried.
  if (status >= 400 && status < 500 && status != 401 && status != 429) {
    pendingCount = 0;
    lastFlushMs = millis();
  }
}

void readRadioPacket() {
  const int packetSize = LoRa.parsePacket();
  if (packetSize <= 0) return;

  String raw;
  raw.reserve(packetSize + 1);
  while (LoRa.available()) {
    raw += static_cast<char>(LoRa.read());
  }
  if (raw.length() == 0 || raw.length() > MAX_PACKET_CHARS) {
    Serial.println("[lora] invalid packet length");
    return;
  }

  JsonDocument document;
  const DeserializationError error = deserializeJson(document, raw);
  if (error) {
    Serial.printf("[lora] JSON error: %s\n", error.c_str());
    return;
  }

  const int rssi = LoRa.packetRssi();
  const float snr = LoRa.packetSnr();
  addReading(document, rssi, snr);
}

void setup() {
  Serial.begin(115200);
  delay(250);
  pinMode(PIN_STATUS_LED, OUTPUT);

  WiFi.mode(WIFI_STA);
  WiFi.setAutoReconnect(true);
  WiFi.begin(WIFI_SSID, WIFI_PASSWORD);
  Serial.printf("[wifi] connecting to %s\n", WIFI_SSID);

  const uint32_t wifiStarted = millis();
  while (WiFi.status() != WL_CONNECTED && millis() - wifiStarted < 20000) {
    delay(500);
    Serial.print('.');
  }
  Serial.println();
  if (WiFi.status() == WL_CONNECTED) {
    Serial.printf("[wifi] connected %s\n", WiFi.localIP().toString().c_str());
    configTime(0, 0, "pool.ntp.org", "time.nist.gov");
    timeConfigured = true;
    lastNtpSyncMs = millis();
  } else {
    Serial.println("[wifi] offline; gateway will buffer and retry");
  }

  if (!radioReady()) {
    Serial.println("[lora] radio not detected; restarting in 10 s");
    for (uint8_t index = 0; index < 12; index++) {
      digitalWrite(PIN_STATUS_LED, HIGH);
      delay(100);
      digitalWrite(PIN_STATUS_LED, LOW);
      delay(100);
    }
    delay(10000);
    ESP.restart();
  }

  lastFlushMs = millis();
  lastWifiAttemptMs = millis();
  digitalWrite(PIN_STATUS_LED, HIGH);
  delay(250);
  digitalWrite(PIN_STATUS_LED, LOW);
  Serial.println("[sentinel] gateway ready");
}

void loop() {
  ensureWifi();
  ensureClock();
  readRadioPacket();

  const bool batchDue = pendingCount > 0 && millis() - lastFlushMs >= FLUSH_INTERVAL_MS;
  if (batchDue || pendingCount >= MAX_BATCH) {
    flushBatch();
  }

  // Solid while connected and queue empty; slow pulse while buffering.
  if (WiFi.status() == WL_CONNECTED) {
    digitalWrite(PIN_STATUS_LED, pendingCount == 0 ? HIGH : (millis() / 500) % 2 ? HIGH : LOW);
  } else {
    digitalWrite(PIN_STATUS_LED, (millis() / 150) % 2 ? HIGH : LOW);
  }

  delay(25);
}
