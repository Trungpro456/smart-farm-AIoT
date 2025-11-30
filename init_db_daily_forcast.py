import sqlite3

def init_db():
    conn = sqlite3.connect("data2.db")
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS daily_forecast (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            temperature_max REAL,
            temperature_min REAL,
            rain_sum REAL,
            windspeed_max REAL,
            evapotranspiration REAL,
            sunrise TEXT,
            sunset TEXT,
            created_at TEXT
        )
    """)

    conn.commit()
    conn.close()
    print("✅ Database & bảng daily_forecast đã được tạo.")

if __name__ == "__main__":
    init_db()
