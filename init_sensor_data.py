import sqlite3

# Kết nối (tự tạo file nếu chưa có)
conn = sqlite3.connect("sensor_data.db")
cursor = conn.cursor()

# Tạo bảng sensor_data
cursor.execute("""
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    device TEXT,
    temp REAL,
    humi REAL,
    sensor TEXT,
    device_timestamp TEXT,
    server_timestamp TEXT
)
""")

conn.commit()
conn.close()

print("✅ Bảng 'sensor_data' đã được tạo thành công trong file 'sensor_data.db'")
