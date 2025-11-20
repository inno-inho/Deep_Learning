from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
# ----------------------------
# YOLOv8n  추가
# ----------------------------
from ultralytics import YOLO

app = FastAPI()
STREAM_URL = "https://safecity.busan.go.kr/playlist/cnRzcDovL2d1ZXN0Omd1ZXN0QDEwLjEuMjEwLjIxMDo1NTQvdXM2NzZyM0RMY0RuczYwdE1ESXdMVEk9/index.m3u8"
# ----------------------------
# YOLOv8n  추가
# ----------------------------
model = None

def get_model():
    global model
    if model is None:
        model = YOLO("best.pt") # model = YOLO("yolov8n.pt")
    return model

def gen_frames():
    cap = cv2.VideoCapture(STREAM_URL)
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        # ----------------------------
        # YOLOv8n  추가
        # ----------------------------
        results = get_model()(frame)
        frame = results[0].plot()
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

@app.get("/init", response_class=HTMLResponse)
def init():
    return """
    <html>
        <head><title>Stream Viewer</title></head>
        <body >
            <h1>Stream Viewer</h1>
            <img src="/video_feed" style='width:100%;height:100%;'>
        </body>
    </html>
    """

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

