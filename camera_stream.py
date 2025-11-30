from flask import Flask, Response, request, abort
import cv2

# ===== CONFIG =====
SNAPSHOT_TOKEN = "secret_123"
PORT = 5001

app = Flask(__name__)

# MỞ CAMERA VỚI ĐỘ PHÂN GIẢI THẤP
camera = cv2.VideoCapture(0)
camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)   # Giảm độ phân giải ngang
camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)  # Giảm độ phân giải dọc
camera.set(cv2.CAP_PROP_FPS, 30)            # Giới hạn FPS (tăng ổn định)

def generate_frames():
    while True:
        success, frame = camera.read()
        if not success:
            continue

        ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
        frame = buffer.tobytes()

        yield (
            b'--frame\r\n'
            b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
        )

@app.route("/video")
def video():
    return Response(
        generate_frames(),
        mimetype="multipart/x-mixed-replace; boundary=frame"
    )

@app.route("/snapshot")
def snapshot():
    token = request.args.get("token", "")
    if token != SNAPSHOT_TOKEN:
        abort(403)

    success, frame = camera.read()
    ret, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 60])
    return Response(buffer.tobytes(), mimetype="image/jpeg")

if __name__ == "__main__":
    print(f"📷 Camera stream running on port {PORT}")
    app.run(host="0.0.0.0", port=PORT, threaded=True)
