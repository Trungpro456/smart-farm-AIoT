import sqlite3
import gspread
from google.oauth2.service_account import Credentials

# ====== Config ======
DB_NAME = "sensor_data.db"  # Dùng đúng DB mới
CREDENTIALS_FILE = "credentials.json"
SHEET_ID = "14GAT3aSC59ug2FfB1ObnorkohJofakxFI8MTaU8zwnc"
LIMIT_ROWS = 20  # số dòng mới nhất muốn đẩy
# ====================

# Google API xác thực
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
client = gspread.authorize(creds)
sheet = client.open_by_key(SHEET_ID).sheet1  # sheet1 = sheet đầu tiên


def fetch_data_from_db(limit=LIMIT_ROWS):
    """
    Lấy đúng cột theo thứ tự cần đẩy:
    (server_timestamp, device, temp, humi, sensor, device_timestamp)
    -> Thứ tự thời gian giảm dần (mới -> cũ)
    """
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        SELECT server_timestamp, device, temp, humi, sensor, device_timestamp
        FROM sensor_data
        ORDER BY id DESC
        LIMIT ?
    """, (limit,))
    rows = cur.fetchall()
    conn.close()

    # ⚡ Không đảo ngược danh sách => giữ nguyên thứ tự mới -> cũ
    return rows


def push_to_google_sheet(rows):
    if not rows:
        print("⚠️ Không có dữ liệu để đẩy.")
        return

    header = ["Server Time", "Device", "Temperature (°C)", "Humidity (%)", "Sensor", "Device Time"]

    # Nếu Sheet đang trống, thêm header
    if not sheet.get_all_values():
        sheet.append_row(header)

    payload = [list(r) for r in rows]
    sheet.append_rows(payload, value_input_option="USER_ENTERED")
    print(f"✅ Đã đẩy {len(rows)} dòng dữ liệu (mới → cũ) lên Google Sheet.")


if __name__ == "__main__":
    data = fetch_data_from_db()
    push_to_google_sheet(data)
