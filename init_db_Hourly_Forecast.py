import sqlite3

def init_db():
    conn = sqlite3.connect("data1.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS weather_hourly (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            temperature REAL,
            humidity REAL,
            precipitation REAL,
            precipitation_probability REAL,
            cloudcover REAL,
            windspeed REAL,
            winddirection REAL,
            soil_temperature REAL,
            soil_moisture REAL,
            shortwave_radiation REAL,
            timestamp TEXT NOT NULL
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database & bảng weather_hourly đã được tạo (Open-Meteo).")

if __name__ == "__main__":
    init_db()
