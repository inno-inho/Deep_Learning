from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2

app = FastAPI()
STREAM_URL = "https://safecity.busan.go.kr/playlist/cnRzcDovL2d1ZXN0Omd1ZXN0QDEwLjEuMjEwLjIwNTo1NTQvdXM2NzZyM0RMY0RuczYwdE1UY3g=/index.m3u8"

def gen_frames():
    cap = cv2.VideoCapture(STREAM_URL)
    while True:
        ret, frame = cap.read()
        if not ret:
            # 스트림이 끊기면 자원 해제 없이 단순히 제너레이터 종료 (최소화 목적)
            break
        _, buffer = cv2.imencode('.jpg', frame)
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
    # 자원 해제 로직도 생략 (최소화 목적이지만, 실제 서비스에서는 권장되지 않음)
    # cap.release()

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

