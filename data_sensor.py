import json
import time
import threading
import sqlite3
from datetime import datetime
import paho.mqtt.client as mqtt

# ⚙️ Cấu hình MQTT
BROKER = "192.168.1.50"
PORT = 1883
TOPICS = [("device1/dht22", 0), ("device2/dht22", 0),("device3/dht22",0),("device4/dht11",0)]
DB_PATH = "/home/pi/Documents/python_programme/do_an_test/do_an_iot/sensor_data.db"

# Danh sách thiết bị & loại cảm biến tương ứng
EXPECTED_DEVICES = {
    "device1": "DHT22",
    "device2": "DHT22",
    "device3":"DHT22",
    "device4":"DHT11"
}
WAIT_TIME = 30  # chờ tối đa 30 giây

device_data = {}
start_wait_time = None


# -------------------------------
# 🗄️ Ghi dữ liệu vào database SQLite
# -------------------------------
def insert_data_to_db(merged_data):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        server_time = merged_data["timestamp"]

        for device in EXPECTED_DEVICES.keys():
            values = merged_data.get(device, {})
            cursor.execute("""
                INSERT INTO sensor_data (device, temp, humi, sensor, device_timestamp, server_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                device,
                values.get("temp", None),
                values.get("humi", None),
                values.get("sensor", None),
                values.get("timestamp", None),
                server_time
            ))

        conn.commit()
        conn.close()
        print("💾 Đã ghi dữ liệu vào database (UTC)!")
    except Exception as e:
        print("❌ Lỗi ghi database:", e)


# -------------------------------
# 🕒 Kiểm tra timeout 30 giây
# -------------------------------
def check_timeout(client):
    global start_wait_time, device_data

    if start_wait_time and (time.time() - start_wait_time >= WAIT_TIME):
        print("⏰ Quá 30 giây mà chưa đủ dữ liệu → gửi dữ liệu rỗng cho phần thiếu.")

        merged = {"timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
        for dev, sensor_type in EXPECTED_DEVICES.items():
            merged[dev] = device_data.get(dev, {
                "temp": "",
                "humi": "",
                "sensor": sensor_type,
                "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            })

        json_str = json.dumps(merged, ensure_ascii=False, indent=2)
        print("⚠️ Dữ liệu gửi sau timeout (UTC):")
        print(json_str)

        client.publish("devices/all", json_str)
        insert_data_to_db(merged)

        device_data.clear()
        start_wait_time = None

    threading.Timer(1, check_timeout, args=[client]).start()


# -------------------------------
# 📡 Khi nhận dữ liệu MQTT
# -------------------------------
def on_message(client, userdata, msg):
    global device_data, start_wait_time

    try:
        data = json.loads(msg.payload.decode())
        device_name = data.get("device", "unknown")

        device_data[device_name] = {
            "temp": data.get("temp"),
            "humi": data.get("humi"),
            "sensor": data.get("sensor", EXPECTED_DEVICES.get(device_name, "")),
            "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        }

        if start_wait_time is None:
            start_wait_time = time.time()

        # Nếu đủ dữ liệu cho tất cả device
        if all(d in device_data for d in EXPECTED_DEVICES.keys()):
            merged = {"timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")}
            for dev, sensor_type in EXPECTED_DEVICES.items():
                merged[dev] = device_data.get(dev, {
                    "temp": "",
                    "humi": "",
                    "sensor": sensor_type,
                    "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
                })

            json_str = json.dumps(merged, ensure_ascii=False, indent=2)
            print("📦 Dữ liệu đầy đủ (UTC), gửi ngay:")
            print(json_str)

            client.publish("devices/all", json_str)
            insert_data_to_db(merged)

            device_data.clear()
            start_wait_time = None

    except Exception as e:
        print("❌ Lỗi xử lý dữ liệu:", e)


# -------------------------------
# 🔗 Khi kết nối MQTT
# -------------------------------
def on_connect(client, userdata, flags, rc):
    print("✅ Đã kết nối MQTT broker!")
    for topic, qos in TOPICS:
        client.subscribe(topic)
        print(f"🔔 Đã subscribe: {topic}")


# -------------------------------
# 🚀 Main
# -------------------------------
def main():
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message

    client.connect(BROKER, PORT, 60)
    check_timeout(client)
    client.loop_forever()


if __name__ == "__main__":
    main()
