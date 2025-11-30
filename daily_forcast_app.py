import requests
import sqlite3
from datetime import datetime

# ========================
# Hàm gọi API Open-Meteo
# ========================
def fetch_weather():
    url = ("https://api.open-meteo.com/v1/forecast"
           "?latitude=10.7769&longitude=106.7008"
           "&daily=temperature_2m_max,temperature_2m_min,"
           "rain_sum,windspeed_10m_max,et0_fao_evapotranspiration_sum,"
           "sunrise,sunset&timezone=Asia/Bangkok")
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print("❌ Lỗi khi gọi API:", e)
        return None

# ========================
# Lưu dữ liệu xuống DB
# ========================
def save_to_db(data):
    conn = sqlite3.connect("data2.db")
    cursor = conn.cursor()

    daily = data.get("daily", {})
    dates = daily.get("time", [])

    for i, date in enumerate(dates):
        cursor.execute("""
            INSERT INTO daily_forecast (
                date, temperature_max, temperature_min, rain_sum,
                windspeed_max, evapotranspiration, sunrise, sunset, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date,
            daily.get("temperature_2m_max", [None])[i],
            daily.get("temperature_2m_min", [None])[i],
            daily.get("rain_sum", [None])[i],
            daily.get("windspeed_10m_max", [None])[i],
            daily.get("et0_fao_evapotranspiration_sum", [None])[i],
            daily.get("sunrise", [None])[i],
            daily.get("sunset", [None])[i],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))

    conn.commit()
    conn.close()
    print("💾 Đã lưu dự báo thời tiết theo ngày vào DB.")

# ========================
# Main app
# ========================
if __name__ == "__main__":
    weather_data = fetch_weather()
    if weather_data:
        print("✅ Dữ liệu nhận được:", weather_data.get("daily", {}))
        save_to_db(weather_data)
