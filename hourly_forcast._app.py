import requests
import sqlite3
from datetime import datetime   # <--- thêm dòng này
# ========================
# Hàm gọi API Open-Meteo
# ========================
def fetch_api_data(url):
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
def save_to_db(hourly):
    conn = sqlite3.connect("data1.db")
    cursor = conn.cursor()

    times = hourly.get("time", [])
    for i, t in enumerate(times):
        # ✅ Chuyển '2025-10-02T00:00' → '2025-10-02 00:00:00'
        ts = datetime.strptime(t, "%Y-%m-%dT%H:%M").strftime("%Y-%m-%d %H:%M:%S")

        cursor.execute("""
            INSERT INTO weather_hourly (
                temperature, humidity, precipitation, precipitation_probability,
                cloudcover, windspeed, winddirection, soil_temperature,
                soil_moisture, shortwave_radiation, timestamp
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            hourly.get("temperature_2m", [None])[i],
            hourly.get("relative_humidity_2m", [None])[i],
            hourly.get("precipitation", [None])[i],
            hourly.get("precipitation_probability", [None])[i],
            hourly.get("cloudcover", [None])[i],
            hourly.get("windspeed_10m", [None])[i],
            hourly.get("winddirection_10m", [None])[i],
            hourly.get("soil_temperature_0cm", [None])[i],
            hourly.get("soil_moisture_0_1cm", [None])[i],
            hourly.get("shortwave_radiation", [None])[i],
            ts   # <-- timestamp chuẩn
        ))

    conn.commit()
    conn.close()
    print("💾 Đã lưu dữ liệu thời tiết vào DB.")

# ========================
# Main app
# ========================
if __name__ == "__main__":
    url = ("https://api.open-meteo.com/v1/forecast?"
           "latitude=10.7769&longitude=106.7008"
           "&hourly=temperature_2m,relative_humidity_2m,precipitation,"
           "precipitation_probability,cloudcover,windspeed_10m,"
           "winddirection_10m,soil_temperature_0cm,soil_moisture_0_1cm,"
           "shortwave_radiation&timezone=Asia/Bangkok")

    data = fetch_api_data(url)
    if data:
        hourly = data.get("hourly", {})
        if hourly:
            print(f"✅ Nhận {len(hourly.get('time', []))} bản ghi dự báo giờ.")
            save_to_db(hourly)
        else:
            print("⚠️ Không có dữ liệu hourly từ API.")
