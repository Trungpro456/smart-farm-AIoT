#include <WiFi.h>
#include <PubSubClient.h>
#include <ArduinoJson.h>

// ================= WIFI & MQTT CONFIG =================
const char* ssid = "Nguyen Thi Chat";
const char* password = "20101940";
const char* mqtt_server = "192.168.1.50";   // Raspberry Pi MQTT

// ================= RELAY PINS =================
#define RELAY1  23
#define RELAY2  22
#define RELAY3  19
#define RELAY4  18

WiFiClient espClient;
PubSubClient client(espClient);

// ================= PUBLISH RELAY STATUS =================
void publishRelayStatus(int relay, bool state) {
  StaticJsonDocument<128> doc;
  doc["relay"] = relay;
  doc["state"] = state ? "on" : "off";

  char buffer[128];
  size_t len = serializeJson(doc, buffer);

  client.publish("relay/status", buffer, len);
  Serial.printf("📤 STATUS: Relay %d -> %s\n", relay, state ? "ON" : "OFF");
}

// ================= MQTT CALLBACK =================
void callback(char* topic, byte* payload, unsigned int length) {
  payload[length] = '\0';
  String msg = (char*)payload;

  Serial.printf("📩 MQTT (%s): %s\n", topic, msg.c_str());

  StaticJsonDocument<256> doc;
  auto err = deserializeJson(doc, msg);

  if (err) {
    Serial.println("⚠️ JSON lỗi hoặc payload rác!");
    return;
  }

  // Relay có thể nhận kiểu string -> chuyển sang int an toàn
  String relayStr = doc["relay"].as<String>();
  int relay = relayStr.toInt();

  String state = doc["state"].as<String>();
  bool isOn = (state == "on");

  switch (relay) {
    case 1: digitalWrite(RELAY1, isOn); break;
    case 2: digitalWrite(RELAY2, isOn); break;
    case 3: digitalWrite(RELAY3, isOn); break;
    case 4: digitalWrite(RELAY4, isOn); break;
    default:
      Serial.println("⚠️ Relay ID không hợp lệ!");
      return;
  }

  Serial.printf("✅ Relay %d -> %s\n", relay, isOn ? "ON" : "OFF");
  publishRelayStatus(relay, isOn);
}

// ================= WIFI =================
void setup_wifi() {
  Serial.printf("🔌 Đang kết nối WiFi: %s\n", ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(400);
    Serial.print(".");

  }

  Serial.println("\n✅ WiFi OK");
  Serial.print("🌐 ESP32 IP: ");

  Serial.println(WiFi.localIP());
}

// ================= MQTT RECONNECT =================
void reconnect() {
  while (!client.connected()) {
    Serial.print("🔁 MQTT reconnect... ");

    if (client.connect("esp32_relay")) {
      Serial.println("OK");
      client.subscribe("relay/control");

      // gửi trạng thái ban đầu
      publishRelayStatus(1, digitalRead(RELAY1));
      publishRelayStatus(2, digitalRead(RELAY2));
      publishRelayStatus(3, digitalRead(RELAY3));
      publishRelayStatus(4, digitalRead(RELAY4));

    } else {
      Serial.println("❌ Lỗi! Thử lại sau 2s");
      delay(2000);
    }
  }
}

// ================= SETUP =================
void setup() {
  Serial.begin(115200);

  pinMode(RELAY1, OUTPUT);
  pinMode(RELAY2, OUTPUT);
  pinMode(RELAY3, OUTPUT);
  pinMode(RELAY4, OUTPUT);

  // default OFF
  digitalWrite(RELAY1, LOW);
  digitalWrite(RELAY2, LOW);
  digitalWrite(RELAY3, LOW);
  digitalWrite(RELAY4, LOW);

  setup_wifi();
  client.setServer(mqtt_server, 1883);
  client.setCallback(callback);
}

// ================= LOOP =================
void loop() {
  if (!client.connected()) reconnect();
  client.loop();
}
