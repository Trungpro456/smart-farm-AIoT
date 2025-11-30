#include <WiFi.h>
#include <PubSubClient.h>
#include "DHT.h"

#define DHTPIN 4
#define DHTTYPE DHT22

const char* ssid = "Nguyen Thi Chat";
const char* password = "20101940";
const char* mqtt_server = "192.168.1.50";

WiFiClient espClient;
PubSubClient client(espClient);
DHT dht(DHTPIN, DHTTYPE);

void setup_wifi() {
  delay(10);
  Serial.begin(115200);
  Serial.println();
  Serial.print("Kết nối WiFi: ");
  Serial.println(ssid);

  WiFi.begin(ssid, password);
  while (WiFi.status() != WL_CONNECTED) {
    delay(500);
    Serial.print(".");
  }

  Serial.println("\nWiFi đã kết nối!");
  Serial.print("IP ESP32: ");
  Serial.println(WiFi.localIP());
}

void reconnect() {
  while (!client.connected()) {
    Serial.print("Kết nối MQTT...");
    if (client.connect("ESP32_Node1")) {  // ⚠️ khác ID với node1
      Serial.println("Thành công!");
    } else {
      Serial.print("Lỗi, rc=");
      Serial.print(client.state());
      Serial.println(" thử lại sau 5s");
      delay(5000);
    }
  }
}

void setup() {
  setup_wifi();
  client.setServer(mqtt_server, 1883);
  dht.begin();
}

void loop() {
  if (!client.connected()) {
    reconnect();
  }
  client.loop();

  float h = dht.readHumidity();
  float t = dht.readTemperature();

  if (isnan(h) || isnan(t)) {
    Serial.println("Không đọc được từ DHT22!");
    return;
  }

  String payload = "{";
  payload += "\"device\":\"device1\",";
  payload += "\"sensor\":\"DHT22\",";
  payload += "\"temp\":" + String(t, 1) + ",";
  payload += "\"humi\":" + String(h, 1);
  payload += "}";

  client.publish("device1/dht22", payload.c_str());

  Serial.print("Đã gửi device 1: ");
  Serial.println(payload);

  delay(15000);
}
