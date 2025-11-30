# ================== MONKEY PATCH PHẢI ĐỨNG ĐẦU ==================
import eventlet
eventlet.monkey_patch()

import json
import sqlite3
from datetime import datetime, timedelta
from flask import Flask, render_template, jsonify, request, redirect, url_for, session
from flask_socketio import SocketIO, emit
from flask_mqtt import Mqtt

import os
from dotenv import load_dotenv

load_dotenv()

# ================== CẤU HÌNH CHUNG ==================
app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", "secret-key-smartfarm")

# MQTT broker
app.config["MQTT_BROKER_URL"] = "localhost"
app.config["MQTT_BROKER_PORT"] = 1883
app.config["MQTT_KEEPALIVE"] = 60

# ================== SOCKET.IO ==================
socketio = SocketIO(app, async_mode="eventlet", cors_allowed_origins="*")

# ================== MQTT ==================
mqtt = Mqtt(app)

# ================== DATABASE ==================
SENSOR_DB = "/home/pi/Documents/python_programme/do_an_test/do_an_iot/sensor_data.db"
SOIL_DB = "/home/pi/Documents/python_programme/do_an_test/do_an_iot/sensor_rs485_data.db"
RELAY_DB = "/home/pi/Documents/python_programme/do_an_test/do_an_iot/relay_data.db"

# ================== HỖ TRỢ THỜI GIAN ==================
def to_vn_time(utc_str):
    try:
        utc_time = datetime.strptime(utc_str, "%Y-%m-%d %H:%M:%S")
        vn_time = utc_time + timedelta(hours=7)
        return vn_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception:
        return utc_str

# ================== KHỞI TẠO RELAY TABLE ==================
def init_relay_table():
    conn = sqlite3.connect(RELAY_DB)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS relay_states (
            relay_id INTEGER PRIMARY KEY,
            state TEXT NOT NULL
        )
    """)
    for i in range(1, 5):
        c.execute("INSERT OR IGNORE INTO relay_states (relay_id, state) VALUES (?, ?)", (i, "off"))
    conn.commit()
    conn.close()

init_relay_table()

# ================== TRẠNG THÁI RELAY ==================
def get_relay_states_db():
    conn = sqlite3.connect(RELAY_DB)
    cursor = conn.cursor()
    cursor.execute("SELECT relay_id, state FROM relay_states")
    rows = cursor.fetchall()
    conn.close()
    return {str(r[0]): r[1] for r in rows}

def update_relay_state_db(relay_id, state):
    conn = sqlite3.connect(RELAY_DB)
    cursor = conn.cursor()
    cursor.execute("UPDATE relay_states SET state=? WHERE relay_id=?", (state, relay_id))
    conn.commit()
    conn.close()

# ================== MQTT CALLBACK ==================
@mqtt.on_connect()
def handle_connect(client, userdata, flags, rc):
    print("✅ Kết nối MQTT thành công")
    mqtt.subscribe("relay/status")
    mqtt.subscribe("sensor/data")

@mqtt.on_message()
def handle_mqtt_message(client, userdata, message):
    topic = message.topic
    payload = message.payload.decode()
    print(f"📩 MQTT [{topic}]: {payload}")

    if topic == "sensor/data":
        try:
            data = json.loads(payload)
            save_sensor_data(data)
            socketio.emit("sensor_update", get_latest_sensor_data(), broadcast=True)
        except Exception as e:
            print("❌ Lỗi xử lý sensor/data:", e)
    elif topic == "relay/status":
        try:
            data = json.loads(payload)
            relay_id = str(data.get("relay"))
            state = data.get("state")
            update_relay_state_db(relay_id, state)
            socketio.emit("relay_status", {"relay": relay_id, "state": state}, broadcast=True)
            print(f"✅ Relay {relay_id} -> {state}")
        except Exception as e:
            print("❌ Lỗi xử lý relay/status:", e)

# ================== SOCKET.IO EVENTS ==================
@socketio.on("toggle_relay")
def handle_toggle_relay(data):
    # Khai báo relay_id bên ngoài để dùng trong 'except' nếu cần
    relay_id = "unknown" 
    try:
        # Kiểm tra xem 'data' có phải là kiểu dict không
        if not isinstance(data, dict):
            print(f"❌ Dữ liệu 'toggle_relay' không hợp lệ (không phải dict): {data}")
            emit("relay_error", {"message": "Dữ liệu gửi lên không hợp lệ."})
            return

        relay_id = str(data.get("relay_id"))

        # Lấy trạng thái hiện tại và xác định trạng thái mới
        current_state = get_relay_states_db().get(relay_id, "off")
        new_state = "off" if current_state == "on" else "on"
        
        # 1. Cập nhật cơ sở dữ liệu
        update_relay_state_db(relay_id, new_state)
        
        # 2. Gửi lệnh tới MQTT broker
        mqtt.publish("relay/control", json.dumps({"relay": relay_id, "state": new_state}))
        
        print('event active !')
        
        # 3. Phát sự kiện cập nhật trạng thái tới TẤT CẢ client
        emit("relay_status", {"relay": relay_id, "state": new_state}, broadcast=True)
        
        print(f"🟢 Yêu cầu đổi Relay {relay_id} -> {new_state}")

    except Exception as e:
        # Bắt tất cả các lỗi có thể xảy ra (lỗi DB, lỗi MQTT, ...)
        print(f"❌ Lỗi nghiêm trọng trong 'handle_toggle_relay' cho relay {relay_id}: {e}")
        
        # Gửi thông báo lỗi về CHỈ client đã yêu cầu
        # Rất hữu ích để gỡ lỗi trên giao diện
        emit("relay_error", {
            "message": f"Không thể điều khiển relay {relay_id}. Lỗi: {str(e)}",
            "relay_id": relay_id
        })
# ================== SENSOR DATA ==================
def save_sensor_data(data):
    try:
        conn = sqlite3.connect(SENSOR_DB)
        cursor = conn.cursor()
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
        cursor.execute("""
            INSERT INTO sensor_data (device, temp, humi, sensor, device_timestamp, server_timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            data.get("device", "device1"),
            data.get("temp"),
            data.get("humi"),
            data.get("sensor"),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
            datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
    except Exception as e:
        print("❌ Lỗi ghi sensor DB:", e)

def get_latest_sensor_data():
    try:
        conn = sqlite3.connect(SENSOR_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM sensor_data
            WHERE (device, server_timestamp) IN (
                SELECT device, MAX(server_timestamp)
                FROM sensor_data
                GROUP BY device
            )
            ORDER BY device;
        """)
        rows = cursor.fetchall()
        conn.close()

        data = {}
        for row in rows:
            vn_device_ts = to_vn_time(row["device_timestamp"])
            data[row["device"]] = {
                "temp": row["temp"],
                "humi": row["humi"],
                "sensor": row["sensor"],
                "device_timestamp": vn_device_ts,
                "server_timestamp": (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
            }

        data["timestamp"] = (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        return data
    except Exception as e:
        print("❌ Lỗi đọc sensor DB:", e)
        return {}
def get_latest_soil_data():
    try:
        conn = sqlite3.connect(SOIL_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT *
            FROM soil_data
            ORDER BY id DESC
            LIMIT 1
        """)
        row = cursor.fetchone()
        conn.close()

        if not row:
            return {"soil": None, "timestamp": None}

        vn_time = to_vn_time(row["timestamp"])

        return {
            "soil": {
                "temperature": row["temperature"],
                "humidity": row["humidity"],
                "ec": row["ec"],
                "timestamp": vn_time
            },
            "timestamp": (datetime.utcnow() + timedelta(hours=7)).strftime("%Y-%m-%d %H:%M:%S")
        }

    except Exception as e:
        print("❌ Lỗi đọc soil_data:", e)
        return {"soil": None, "timestamp": None}

# ================== SOIL DATA ==================
@app.route("/soil_data")
def soil_data():
    return jsonify(get_latest_soil_data())

# ================== API ROUTES ==================
@app.route("/data")
@app.route("/data_all")
def api_data_all():
    return jsonify(get_latest_sensor_data())

@app.route("/api/relay_states")
def api_relay_states():
    relay_dict = get_relay_states_db()

    relay_list = [{"relayId": k, "state": v} for k, v in relay_dict.items()]
    return jsonify(relay_list)

@app.route("/api/relay_control", methods=["POST"])
def api_relay_control():
    data = request.get_json()
    relay_id = str(data.get("relay"))
    state = data.get("state")
    if relay_id not in ["1", "2", "3", "4"]:
        return jsonify({"error": "Relay không tồn tại!"}), 400
    update_relay_state_db(relay_id, state)
    mqtt.publish("relay/control", json.dumps({"relay": relay_id, "state": state}))
    print('event active !')

    socketio.emit("relay_status", {"relay": relay_id, "state": state})      
    return jsonify({"success": True, "relay": relay_id, "state": state})
# ================== LOGIN ==================
@app.before_request
def require_login():
    path = (request.path or "").lower()
    public_prefixes = ("/api/", "/data", "/data_all", "/soil_data", "/socket.io", "/static", "/favicon.ico")
    for p in public_prefixes:
        if path.startswith(p):
            return
    if path in ("/login", "/api/login"):
        return
    if not session.get("logged_in"):
        return redirect(url_for("login_page"))

@app.route("/login")
def login_page():
    return render_template("login.html")

@app.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json() if request.is_json else {
        "username": request.form.get("username"),
        "password": request.form.get("password")
    }
    username = data.get("username")
    password = data.get("password")
    if username == "smartfarmAIOT" and password == "trungnlu2004":
        session["logged_in"] = True
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Sai tài khoản hoặc mật khẩu!"})

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    return redirect(url_for("login_page"))

# ================== FRONTEND ROUTES ==================
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/history")
def history():
    return render_template("history.html")
@app.route("/api/history")
def api_history():
    """
    Trả về lịch sử dữ liệu sensor theo device và khoảng thời gian.
    Query params:
        device: device1/device2/...
        start: YYYY-MM-DD (tùy chọn)
        end: YYYY-MM-DD (tùy chọn)
    """
    device = request.args.get("device", "device1")
    start_date = request.args.get("start")
    end_date = request.args.get("end")

    try:
        conn = sqlite3.connect(SENSOR_DB)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        query = "SELECT * FROM sensor_data WHERE device=?"
        params = [device]

        if start_date:
            query += " AND date(server_timestamp) >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date(server_timestamp) <= ?"
            params.append(end_date)

        query += " ORDER BY server_timestamp ASC"

        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()

        result = []
        for row in rows:
            result.append({
                "id": row["id"],
                "device": row["device"],
                "temp": row["temp"],
                "humi": row["humi"],
                "sensor": row["sensor"],
                "device_timestamp": row["device_timestamp"],
                "server_timestamp": row["server_timestamp"]
            })

        return jsonify(result)
    except Exception as e:
        print("❌ Lỗi API /api/history:", e)
        return jsonify({"error": str(e)}), 500

# ================== RUN APP ==================
if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=5000, debug=True)
