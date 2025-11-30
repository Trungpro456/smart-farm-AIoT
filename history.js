document.addEventListener("DOMContentLoaded", () => {
    const tempCtx = document.getElementById("tempChart").getContext("2d");
    const humiCtx = document.getElementById("humiChart").getContext("2d");
    const dataTableBody = document.getElementById("dataTableBody");
    const deviceSelect = document.getElementById("deviceSelect");
    const startDateInput = document.getElementById("startDate");
    const endDateInput = document.getElementById("endDate");
    const filterBtn = document.getElementById("filterBtn");

    let tempChart, humiChart;
    let currentDevice = "device1";

    // 🎨 Màu & tên cho từng vườn
    const deviceInfo = {
        device1: { name: "Vườn 1", color: "#ff0000", humiColor: "#00aa00" },
        device2: { name: "Vườn 2", color: "#007bff", humiColor: "#ffa500" },
        device3: { name: "Vườn 3", color: "#800080", humiColor: "#008080" },
        device4: { name: "Vườn 4", color: "#8b4513", humiColor: "#808080" },
    };

    // 🧩 HEX → RGBA
    function hexToRgba(hex, alpha) {
        const shorthandRegex = /^#?([a-f\d])([a-f\d])([a-f\d])$/i;
        hex = hex.replace(shorthandRegex, (m, r, g, b) => r + r + g + g + b + b);
        const result = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(hex);
        return result
            ? `rgba(${parseInt(result[1], 16)}, ${parseInt(result[2], 16)}, ${parseInt(result[3], 16)}, ${alpha})`
            : hex;
    }

    // 🗓️ Ngày hôm nay mặc định
    const today = new Date().toISOString().split("T")[0];
    startDateInput.value = today;
    endDateInput.value = today;

    // 🔥 Load dữ liệu lịch sử
    async function loadHistory(device = "device1") {
        const start = startDateInput.value;
        const end = endDateInput.value;

        try {
            const res = await fetch(`/api/history?device=${device}&start=${start}&end=${end}`);
            const data = await res.json();

            if (!data || data.error) {
                console.error("⚠️ Lỗi fetch history:", data.error || "Empty data");
                dataTableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-gray-500">Không có dữ liệu</td></tr>`;
                return;
            }

            const labels = data.map(d => d.server_timestamp);
            const temps = data.map(d => d.temp);
            const hums = data.map(d => d.humi);

            renderCharts(labels, temps, hums, device);
            renderTable(data);
        } catch (err) {
            console.error("⚠️ Lỗi tải dữ liệu:", err);
        }
    }

    // 📊 Vẽ Chart.js
    function renderCharts(labels, temps, hums, device) {
        const { name, color, humiColor } = deviceInfo[device] || { name: device, color: "#000", humiColor: "#666" };

        if (tempChart) tempChart.destroy();
        if (humiChart) humiChart.destroy();

        tempChart = new Chart(tempCtx, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: `${name} - Nhiệt độ (°C)`,
                    data: temps,
                    borderColor: color,
                    backgroundColor: hexToRgba(color, 0.3),
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } },
                scales: { y: { beginAtZero: false } },
            },
        });

        humiChart = new Chart(humiCtx, {
            type: "line",
            data: {
                labels,
                datasets: [{
                    label: `${name} - Độ ẩm (%)`,
                    data: hums,
                    borderColor: humiColor,
                    backgroundColor: hexToRgba(humiColor, 0.3),
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointRadius: 2,
                }],
            },
            options: {
                responsive: true,
                plugins: { legend: { display: true } },
                scales: { y: { beginAtZero: false } },
            },
        });
    }

    // 📋 Update bảng
    function renderTable(data) {
        dataTableBody.innerHTML = "";
        if (!data || data.length === 0) {
            dataTableBody.innerHTML = `<tr><td colspan="5" class="text-center py-4 text-gray-500">Không có dữ liệu</td></tr>`;
            return;
        }

        data.slice(-20).reverse().forEach(row => {
            const tr = document.createElement("tr");
            tr.innerHTML = `
                <td class="px-4 py-2">${row.server_timestamp}</td>
                <td class="px-4 py-2">${row.device}</td>
                <td class="px-4 py-2">${row.temp ?? "-"}</td>
                <td class="px-4 py-2">${row.humi ?? "-"}</td>
                <td class="px-4 py-2">${row.sensor}</td>
            `;
            dataTableBody.appendChild(tr);
        });
    }

    // 🎛️ Khi đổi device
    deviceSelect.addEventListener("change", e => {
        currentDevice = e.target.value;
        loadHistory(currentDevice);
    });

    // 🔍 Khi bấm Lọc
    filterBtn.addEventListener("click", () => {
        loadHistory(currentDevice);
    });

    // 🚀 Load mặc định
    loadHistory(currentDevice);

    // ⏱️ Refresh mỗi 60 giây
    setInterval(() => loadHistory(currentDevice), 60000);
});
