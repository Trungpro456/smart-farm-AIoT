from pymodbus.client.sync import ModbusSerialClient
import sqlite3
import time

# ===== Kết nối SQLite =====
conn = sqlite3.connect("sensor_rs485_data.db")
cursor = conn.cursor()

# Tạo bảng nếu chưa có
cursor.execute("""
CREATE TABLE IF NOT EXISTS soil_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
    temperature REAL,
    humidity REAL,
    ec REAL
)
""")
conn.commit()

# ===== Kết nối Modbus =====
client = ModbusSerialClient(
    method="rtu",
    port="/dev/ttyUSB0",   # 🔴 Đổi lại đúng cổng USB của bạn
    baudrate=9600,
    parity="N",
    stopbits=1,
    bytesize=8,
    timeout=3
)

if client.connect():
    print("✅ Đã kết nối Modbus...")

    try:
        while True:
            rr = client.read_holding_registers(address=0, count=10, unit=1)
            if rr.isError():
                print("⚠️ Lỗi khi đọc:", rr)
            else:
                temp = rr.registers[1] / 10.0
                hum  = rr.registers[0] / 10.0
                ec   = rr.registers[2]

                print(f"Nhiệt độ đất: {temp} °C, Độ ẩm đất: {hum} %, EC đất: {ec} µS/cm")

                # Lưu vào DB
                cursor.execute(
                    "INSERT INTO soil_data (temperature, humidity, ec) VALUES (?, ?, ?)",
                    (temp, hum, ec)
                )
                conn.commit()

            print("-----------------------")
            time.sleep(60)

    except KeyboardInterrupt:
        print("\n⏹ Dừng chương trình...")

    finally:
        client.close()
        conn.close()
        print("❌ Đã đóng kết nối Modbus & SQLite.")
else:
    print("❌ Không mở được cổng /dev/ttyUSB0")
