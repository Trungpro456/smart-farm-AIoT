// ==================== FETCH DỮ LIỆU CẢM BIẾN ====================
async function fetchData() {
    try {
        const res = await fetch("/data_all");
        const data = await res.json();
        updateSensorUI(data);
    } catch (err) {
        console.error("Lỗi fetch /data_all:", err);
    }
}

function updateSensorUI(data) {
    const gardens = [1, 2, 3, 4];
    gardens.forEach(i => {
        const key = "device" + i;
        const tempEl = document.getElementById(`temp-${i}`);
        const humEl = document.getElementById(`hum-${i}`);
        const timeEl = document.getElementById(`time-${i}`);

        if (data[key]) {
            tempEl.textContent = data[key].temp ? data[key].temp + " °C" : "--";
            humEl.textContent = data[key].humi ? data[key].humi + " %" : "--";
            timeEl.textContent = data[key].server_timestamp ?? "--";
        } else {
            tempEl.textContent = "Đang chờ dữ liệu...";
            humEl.textContent = "";
            timeEl.textContent = "";
        }
    });
}

// ==================== FETCH DỮ LIỆU CẢM BIẾN ĐẤT ====================
async function fetchSoilData() {
    try {
        const res = await fetch("/soil_data");
        const data = await res.json();
        if (!data || !data.soil) return;

        document.getElementById("soil-temp").textContent =
            data.soil.temperature != null ? data.soil.temperature + " °C" : "--";
        document.getElementById("soil-hum").textContent =
            data.soil.humidity != null ? data.soil.humidity + " %" : "--";
        document.getElementById("soil-ec").textContent =
            data.soil.ec != null ? data.soil.ec + " µS/cm" : "--";
        document.getElementById("soil-time").textContent =
            data.soil.timestamp ?? "--";
    } catch (err) {
        console.error("Lỗi fetch /soil_data:", err);
    }
}
// ==================== SOCKET.IO ====================
document.addEventListener("DOMContentLoaded", () => {
    const socket = io();
    socket.on("connect", () => {
        console.log("✅ Socket connected:", socket.id);
    });
    // Điều khiển bơm
    document.querySelectorAll(".relay-btn").forEach(btn => {
        btn.addEventListener("click", () => {
            const relay = btn.dataset.relay;
            const newState = btn.dataset.state === "on" ? "off" : "on";
            btn.dataset.state = newState;
            console.log('toggle_replay')
            socket.emit("toggle_relay", { relay_id: relay, state: newState });
        });
    });

    // Hàm cập nhật UI nút relay (chung cho load ban đầu & socket)
    function updateRelayUI(relayID, state) {
        const btn = document.querySelector(`.relay-btn[data-relay='${relayID}']`);
        if (!btn) return;

        btn.dataset.state = state;

        if (state === "on") {
            btn.textContent = `💡 Tắt Bơm ${relayID}`;
            btn.classList.remove("bg-green-500", "hover:bg-green-600");
            btn.classList.add("bg-red-500", "hover:bg-red-600");
        } else {
            btn.textContent = `🚿 Bật Bơm ${relayID}`;
            btn.classList.remove("bg-red-500", "hover:bg-red-600");
            btn.classList.add("bg-green-500", "hover:bg-green-600");
        }
    }

    // Nhận phản hồi trạng thái bơm từ server
    socket.on("relay_status", data => { // <-- SỬA TÊN EVENT TẠI ĐÂY
        console.log("Relay update received:", data);
        if (data.relay && data.state) {
            updateRelayUI(data.relay, data.state);
        }
    });
    // Cập nhật realtime cảm biến
    socket.on("sensor_update", data => {
        updateSensorUI(data);
    });

    // Cập nhật lần đầu
    fetchData();
    fetchSoilData();
});
async function fetchBom() {

    const res = await fetch("/api/relay_states");
    const data = await res.json();
    data.forEach((d) => {
        console.log(d);

        const btn = document.querySelector(
            `.relay-btn[data-relay='${d.relayId}']`
        );
        console.log(btn);

        if (!btn) return;
        if (d.state === "on") {
            btn.textContent = `💡 Tắt Bơm ${d.relayId}`;
            btn.classList.remove("bg-green-500", "hover:bg-green-600");
            btn.classList.add("bg-red-500", "hover:bg-red-600");
        } else {
            btn.textContent = `🚿 Bật Bơm ${d.relayId}`;
            btn.classList.remove("bg-red-500", "hover:bg-red-600");
            btn.classList.add("bg-green-500", "hover:bg-green-600");
        }
    })
}
// Cập nhật định kỳ 10s
fetchBom();
setInterval(fetchData, 10000);
setInterval(fetchSoilData, 10000);