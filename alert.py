import json
import threading
from datetime import datetime

import telegram
from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
)

import socketio
import asyncio
import requests
import sqlite3

import os
from dotenv import load_dotenv

load_dotenv()

# ================= CẤU HÌNH =================
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

SERVER_URL = "http://localhost:5000"
DB_PATH = "/home/pi/Documents/python_programme/do_an_test/do_an_iot/sensor_data.db"

NGUONG_NONG = 25
NGUONG_LANH = 20

# ================= CACHE =================
relay_cache = {"1": "off", "2": "off", "3": "off", "4": "off"}
sensor_cache = {}  # {"device1": {"temp":.., "humi":.., "timestamp":..}, ...}
cache_lock = threading.Lock()

# ================= ACTIVE MENUS =================
active_relay_menu = {}
active_sensor_menu = {}

# ================= MODE AUTO/MANUAL =================
relay_mode = {}  # chat_id: "auto" or "manual"
mode_lock = threading.Lock()

# ================= ALERT STATE =================
last_alert_temp = None
last_alert_device = {"device1": False, "device2": False, "device3": False, "device4": False}

# ================== HÀM CHECK CHUỖI RỖNG ==================
def is_missing(v):
    if v is None:
        return True
    if isinstance(v, str) and v.strip() == "":
        return True
    if str(v).strip().lower() in ["none", "null", "nan"]:
        return True
    return False

# ================== ĐỌC DB ==================
def read_latest_from_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    data = {}
    try:
        cur.execute("SELECT DISTINCT device FROM sensor_data")
        devices = [row["device"] for row in cur.fetchall()]

        for dev in devices:
            cur.execute("""
                SELECT temp, humi, device_timestamp, server_timestamp
                FROM sensor_data
                WHERE device = ?
                ORDER BY id DESC LIMIT 1
            """, (dev,))
            row = cur.fetchone()
            if row:
                ts = row["server_timestamp"] or row["device_timestamp"]
                data[dev] = {"temp": row["temp"], "humi": row["humi"], "timestamp": ts}
    except Exception as e:
        print(f"❌ Lỗi đọc DB: {e}")
    conn.close()
    return data

# ================= TELEGRAM SEND =================
async def safe_send(bot, chat_id, msg):
    try:
        await bot.send_message(chat_id=chat_id, text=msg)
    except telegram.error.NetworkError as e:
        print(f"⚠ Lỗi mạng khi gửi message: {e}")
    except Exception as e:
        print(f"❌ Lỗi khác khi gửi message: {e}")

# ================= SOCKET.IO CLIENT =================
sio = socketio.Client()

@sio.event
def connect():
    print("✅ Kết nối SocketIO thành công")

@sio.event
def disconnect():
    print("❌ SocketIO bị ngắt kết nối")

@sio.on("relay_status")
def handle_relay_status(data):
    relay = str(data.get("relay"))
    state = data.get("state")
    with cache_lock:
        relay_cache[relay] = state
    print(f"🟢 Cập nhật relay: {relay} -> {state}")
    for chat_id, message_id in active_relay_menu.items():
        asyncio.run_coroutine_threadsafe(update_relay_menu(chat_id, message_id), loop)

@sio.on("sensor_update")
def handle_sensor_update(data):
    with cache_lock:
        for dev, val in data.items():
            if dev == "timestamp":
                continue
            sensor_cache[dev] = {"temp": val.get("temp"), "humi": val.get("humi"), "timestamp": val.get("server_timestamp")}
    print("📊 Cập nhật sensor cache")

# ================= UPDATE RELAY MENU =================
async def update_relay_menu(chat_id, message_id):
    msg, keyboard = control_keyboard(chat_id)
    bot = application.bot
    try:
        await bot.edit_message_text(chat_id=chat_id, message_id=message_id,
                                    text=msg, reply_markup=keyboard,
                                    parse_mode="Markdown")
    except telegram.error.BadRequest:
        pass

# ================= CONTROL MENU & KEYBOARD =================
def control_keyboard(chat_id):
    with cache_lock, mode_lock:
        states_copy = relay_cache.copy()
        mode = relay_mode.get(chat_id, "auto")

    msg = f"⚙️ **TRẠNG THÁI THIẾT BỊ** (Chế độ: {mode.upper()})\n\n"
    keyboard = []

    if mode == "manual":
        for i in range(1, 5):
            s = states_copy.get(str(i), "off")
            msg += f"• Bơm {i}: {'🟢 ON' if s == 'on' else '🔴 OFF'}\n"
            keyboard.append([
                InlineKeyboardButton(f"Bơm {i} ON", callback_data=f"on_{i}"),
                InlineKeyboardButton(f"Bơm {i} OFF", callback_data=f"off_{i}")
            ])
    else:
        for i in range(1, 5):
            s = states_copy.get(str(i), "off")
            msg += f"• Bơm {i}: {'🟢 ON' if s == 'on' else '🔴 OFF'}\n"

    toggle_text = "Chuyển sang Manual" if mode == "auto" else "Chuyển sang Auto"
    keyboard.append([InlineKeyboardButton(toggle_text, callback_data="toggle_mode")])
    keyboard.append([InlineKeyboardButton("🏠 Menu chính", callback_data="back")])
    return msg, InlineKeyboardMarkup(keyboard)

# ================= CONTROL MENU =================
async def control_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    chat_id = query.message.chat_id

    # Khởi tạo mặc định Auto nếu chưa có
    with mode_lock:
        if chat_id not in relay_mode:
            relay_mode[chat_id] = "auto"

    if query.data == "toggle_mode":
        with mode_lock:
            current = relay_mode.get(chat_id, "auto")
            relay_mode[chat_id] = "manual" if current == "auto" else "auto"
            # Nếu chuyển sang Auto, reset trạng thái alert nhiệt để monitor_alert hoạt động
            if relay_mode[chat_id] == "auto":
                global last_alert_temp
                last_alert_temp = None
        msg, keyboard = control_keyboard(chat_id)
        await query.edit_message_text(msg, reply_markup=keyboard, parse_mode="Markdown")
        return

    # Chỉ cho bật/tắt relay khi Manual
    with mode_lock:
        if relay_mode.get(chat_id, "auto") == "auto" and query.data.startswith(("on_", "off_")):
            await query.answer("⚠ Chỉ có thể bật/tắt khi ở chế độ Manual", show_alert=True)
            return

    # Xử lý ON/OFF relay
    if query.data.startswith("on_") or query.data.startswith("off_"):
        action, relay = query.data.split("_")
        state = "on" if action == "on" else "off"
        try:
            url = f"{SERVER_URL}/api/relay_control"
            payload = {"relay": int(relay), "state": state}
            r = requests.post(url, json=payload, timeout=5)
            r.raise_for_status()
            res = r.json()
            if res.get("success"):
                with cache_lock:
                    relay_cache[relay] = state
            else:
                await query.edit_message_text(f"❌ Không thể điều khiển Bơm {relay}: {res.get('message')}")
                return
        except Exception as e:
            await query.edit_message_text(f"❌ Lỗi khi gọi server: {e}")
            return

    # Cập nhật menu
    msg, keyboard = control_keyboard(chat_id)
    await query.edit_message_text(msg, reply_markup=keyboard, parse_mode="Markdown")
    active_relay_menu[chat_id] = query.message.message_id


# ================= SENSOR MENU =================
async def sensor_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    with cache_lock:
        local_cache = sensor_cache.copy()
    if not local_cache:
        local_cache = read_latest_from_db()

    msg = "📊 **DỮ LIỆU CẢM BIẾN (Realtime)**\n"
    has_data = False
    for dev, v in local_cache.items():
        temp = v.get("temp")
        humi = v.get("humi")
        ts = v.get("timestamp", "N/A")
        if is_missing(temp) and is_missing(humi):
            continue
        has_data = True
        temp_str = temp if not is_missing(temp) else "N/A"
        humi_str = humi if not is_missing(humi) else "N/A"
        msg += f"\n🔹 **{dev.upper()}**\n🌡 {temp_str}°C\n💧 {humi_str}%\n⏱ {ts}\n"

    if not has_data:
        msg = "⚠ Không có dữ liệu realtime!"

    keyboard = [[InlineKeyboardButton("🔙 Quay lại", callback_data="back")]]
    await query.edit_message_text(msg, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")
    active_sensor_menu[query.message.chat_id] = query.message.message_id

# ================= MAIN MENU =================
def main_menu():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📊 Dữ liệu cảm biến", callback_data="sensor")],
        [InlineKeyboardButton("⚙️ Điều khiển thiết bị", callback_data="control")],
        [InlineKeyboardButton("❌ Thoát", callback_data="exit")]
    ])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    intro = "🌱 **SMART FARM BOT**\nGiám sát & điều khiển AIoT\n\n**Chọn chức năng:**"
    await update.message.reply_markdown(intro, reply_markup=main_menu())

# ================= MENU HANDLER =================
async def menu_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    if query.data == "exit":
        await query.edit_message_text("✅ Bạn đã thoát menu.", parse_mode="Markdown")
    elif query.data == "back":
        await query.edit_message_text("🌱 **SMART FARM BOT**\nChọn chức năng:",
                                      reply_markup=main_menu(), parse_mode="Markdown")
    elif query.data == "sensor":
        await sensor_menu(update, context)
    elif query.data.startswith("control") or query.data.startswith(("on_", "off_", "toggle_mode")):
        await control_menu(update, context)

# ================= ALERT MONITOR =================
async def monitor_alert(context: ContextTypes.DEFAULT_TYPE):
    global last_alert_temp, last_alert_device
    bot = context.application.bot

    try:
        db_data = read_latest_from_db()
        now = datetime.utcnow()

        # Check timeout và dữ liệu rỗng
        for device, val in db_data.items():
            temp = val.get("temp")
            humi = val.get("humi")
            ts_str = val.get("timestamp")
            try:
                ts = datetime.strptime(ts_str, "%Y-%m-%d %H:%M:%S")
            except:
                ts = None

            if ts is None or (now - ts).total_seconds() > 120:
                if not last_alert_device.get(device, False):
                    await safe_send(bot, CHAT_ID, f"🚨 {device.upper()} không cập nhật dữ liệu hơn 2 phút!")
                    last_alert_device[device] = True
                continue

            if is_missing(temp) or is_missing(humi):
                if not last_alert_device.get(device, False):
                    await safe_send(bot, CHAT_ID, f"🚨 {device.upper()} báo dữ liệu rỗng (temp/humi)!")
                    last_alert_device[device] = True
                continue
            else:
                if last_alert_device.get(device, False):
                    await safe_send(bot, CHAT_ID, f"✅ {device.upper()} đã hoạt động trở lại.")
                last_alert_device[device] = False

        # Lấy danh sách chat đang Auto
        with mode_lock:
            auto_chats = [cid for cid, mode in relay_mode.items() if mode == "auto"]

        if not auto_chats:
            return  # Không có chat nào đang Auto → bỏ qua

        # Xử lý nhiệt độ toàn hệ thống (relay 2) chỉ khi Auto
        temps = []
        for dv in db_data.values():
            try:
                temps.append(float(dv.get("temp")))
            except:
                pass

        # Kiểm tra bật/tắt relay 2
        if any(t > NGUONG_NONG for t in temps):
            if last_alert_temp != "relay2_on":
                for chat_id in auto_chats:
                    await safe_send(bot, chat_id, f"🔥 Một trong các cảm biến vượt {NGUONG_NONG}°C → **BẬT BƠM 2**")
                try:
                    url = f"{SERVER_URL}/api/relay_control"
                    payload = {"relay": 2, "state": "on"}
                    r = requests.post(url, json=payload, timeout=5)
                    r.raise_for_status()
                    with cache_lock:
                        relay_cache["2"] = "on"
                    for chat_id, message_id in active_relay_menu.items():
                        asyncio.run_coroutine_threadsafe(update_relay_menu(chat_id, message_id), loop)
                except Exception as e:
                    print(f"❌ Lỗi bật relay 2: {e}")
                last_alert_temp = "relay2_on"
        else:
            if last_alert_temp == "relay2_on":
                for chat_id in auto_chats:
                    await safe_send(bot, chat_id, f"✅ Nhiệt độ đã về mức an toàn → **TẮT BƠM 2**")
                try:
                    url = f"{SERVER_URL}/api/relay_control"
                    payload = {"relay": 2, "state": "off"}
                    r = requests.post(url, json=payload, timeout=5)
                    r.raise_for_status()
                    with cache_lock:
                        relay_cache["2"] = "off"
                    for chat_id, message_id in active_relay_menu.items():
                        asyncio.run_coroutine_threadsafe(update_relay_menu(chat_id, message_id), loop)
                except Exception as e:
                    print(f"❌ Lỗi tắt relay 2: {e}")
                last_alert_temp = None

    except Exception as e:
        print(f"❌ Lỗi monitor_alert: {e}")

# ================= MAIN =================
def main():
    global loop, application

    application = ApplicationBuilder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(menu_handler))

    application.job_queue.run_repeating(monitor_alert, interval=10, first=1)

    loop = asyncio.get_event_loop()

    sio.connect(SERVER_URL)

    print("🤖 Telegram bot đang chạy...")
    application.run_polling()

if __name__ == "__main__":
    main()
