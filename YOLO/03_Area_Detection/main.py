#============================================
# 라이브러리 임포트
#============================================
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import numpy as np
from ultralytics import YOLO
from collections import defaultdict

#============================================
# FastAPI 앱 및 전역 설정
#============================================
app = FastAPI()
STREAM_URL = "https://safecity.busan.go.kr/playlist/cnRzcDovL2d1ZXN0Omd1ZXN0QDEwLjEuMjEwLjIxMDo1NTQvdXM2NzZyM0RMY0RuczYwdE1ESXdMVEk9/index.m3u8"

#============================================
# 전역 변수 (영역 감지 관련)
#============================================
model = None
zone = []  # ROI 좌표
tracks = {}  # {id: "in"/"out"}
count = defaultdict(int)  # 진입 카운트

#============================================
# YOLO 모델 로딩
#============================================
def get_model():
    global model
    if model is None:
        model = YOLO("yolov8n.pt")
    return model

#============================================
# API: 감지 영역 설정
#============================================
@app.post("/set_zone")
async def set_zone(request: Request):
    global zone
    zone = (await request.json()).get("points", [])
    return {"ok": True}

#============================================
# 비디오 프레임 생성 (스트리밍 처리)
#============================================
def gen_frames():
    import time
    cap = None
    retry_count = 0
    fail_count = 0
    
    while True:
        try:
            #--------------------------------------------
            # 1. 스트림 연결 및 재연결 처리
            #--------------------------------------------
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                
                print(f"🔄 스트림 연결 중... (시도 {retry_count + 1})")
                cap = cv2.VideoCapture(STREAM_URL)
                
                # VideoCapture 설정 (중요!)
                cap.set(cv2.CAP_PROP_BUFFERSIZE, 3)  # 버퍼 크기 줄임
                cap.set(cv2.CAP_PROP_FPS, 15)  # FPS 제한
                
                if not cap.isOpened():
                    retry_count += 1
                    print(f"❌ 연결 실패 (재시도 대기 중...)")
                    time.sleep(2)
                    if retry_count > 10:
                        retry_count = 0
                        time.sleep(5)
                    continue
                
                print("✅ 스트림 연결 성공!")
                retry_count = 0
                fail_count = 0
            
            #--------------------------------------------
            # 2. 프레임 읽기 및 실패 처리
            #--------------------------------------------
            ret, frame = cap.read()
            
            if not ret:
                fail_count += 1
                print(f"⚠️  프레임 읽기 실패 ({fail_count}회)")
                
                # 3회 연속 실패 시 재연결
                if fail_count >= 3:
                    print("🔄 재연결 필요...")
                    if cap is not None:
                        cap.release()
                    cap = None
                    fail_count = 0
                
                time.sleep(0.1)
                continue
            
            fail_count = 0  # 성공 시 리셋
            
            #--------------------------------------------
            # 3. YOLO 객체 추적 (핵심!)
            #--------------------------------------------
            try:
                results = get_model().track(frame, persist=True, verbose=False)
            except Exception as e:
                print(f"⚠️  YOLO 추적 에러: {e}")
                # 기본 프레임 전송
                _, buffer = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                continue
            
            #--------------------------------------------
            # 4. ROI(관심 영역) 그리기
            #--------------------------------------------
            if len(zone) >= 3:
                pts = np.array(zone, np.int32)
                cv2.polylines(frame, [pts], True, (0,255,0), 2)
            
            #--------------------------------------------
            # 5. 객체 바운딩 박스 그리기 & 진입 감지
            #--------------------------------------------
            if results[0].boxes is not None and len(results[0].boxes) > 0 and results[0].boxes.id is not None:
                for i, tid in enumerate(results[0].boxes.id.int().tolist()):
                    try:
                        box = results[0].boxes.xyxy[i].tolist()
                        cx, cy = int((box[0]+box[2])/2), int((box[1]+box[3])/2)
                        cls = results[0].names[int(results[0].boxes.cls[i])]
                        conf = results[0].boxes.conf[i]
                        
                        # 영역 내부 판정
                        inside = False
                        if len(zone) >= 3:
                            inside = cv2.pointPolygonTest(pts, (cx,cy), False) >= 0
                            state = "in" if inside else "out"
                            
                            # 진입 이벤트
                            if tid not in tracks:
                                tracks[tid] = state
                            elif tracks[tid] == "out" and state == "in":
                                count[cls] += 1
                            tracks[tid] = state
                        
                        # 박스 색상: 영역 내부=빨강, 외부=초록
                        color = (0, 0, 255) if inside else (0, 255, 0)
                        
                        # 바운딩 박스 그리기
                        cv2.rectangle(frame, 
                                     (int(box[0]), int(box[1])), 
                                     (int(box[2]), int(box[3])), 
                                     color, 2)
                        
                        # 라벨 (클래스, ID, 신뢰도)
                        label = f"{cls} ID:{tid} {conf:.2f}"
                        cv2.putText(frame, label, 
                                   (int(box[0]), int(box[1])-10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 2)
                    except Exception as e:
                        print(f"⚠️  객체 처리 에러: {e}")
                        continue
            elif results[0].boxes is not None and len(results[0].boxes) > 0:
                # 추적 ID 없을 때 기본 표시
                frame = results[0].plot()
            
            # 카운트 표시
            y = 30
            for cls, cnt in count.items():
                cv2.putText(frame, f"{cls}: {cnt}", (10,y), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0,255,255), 2)
                y += 30
            
            #--------------------------------------------
            # 7. 프레임 인코딩 및 전송
            #--------------------------------------------
            success, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if success:
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
            else:
                print("⚠️  프레임 인코딩 실패")
        
        #--------------------------------------------
        # 8. 예외 처리
        #--------------------------------------------
        except GeneratorExit:
            print("🛑 클라이언트 연결 종료")
            if cap is not None:
                cap.release()
            break
        
        except Exception as e:
            print(f"❌ 예상치 못한 에러: {e}")
            time.sleep(0.1)
            continue

#============================================
# API: HTML UI 페이지
#============================================
@app.get("/init", response_class=HTMLResponse)
def init():
    return """
    <html>
    <head><title>Area Detection</title></head>
    <body style="margin:0">
        <div style="position:relative;width:100%;height:90vh;object-fit:contain;">
            <img id="s" src="/video_feed" style="width:100%;height:100%;cursor:crosshair">
            <canvas id="c" style="position:absolute;top:0;left:0;pointer-events:none"></canvas>
        </div>
        <button onclick="done()">완료</button>
        <button onclick="reset()">초기화</button>
        <script>
        let pts=[], c=document.getElementById('c'), ctx=c.getContext('2d'), s=document.getElementById('s');
        s.onload=()=>{c.width=s.offsetWidth;c.height=s.offsetHeight};
        s.onclick=e=>{
            let r=s.getBoundingClientRect();
            pts.push([Math.round((e.clientX-r.left)*s.naturalWidth/r.width),
                     Math.round((e.clientY-r.top)*s.naturalHeight/r.height)]);
            ctx.clearRect(0,0,c.width,c.height);
            ctx.strokeStyle='#0f0';ctx.lineWidth=2;
            if(pts.length>1){
                ctx.beginPath();
                ctx.moveTo(pts[0][0]*r.width/s.naturalWidth,pts[0][1]*r.height/s.naturalHeight);
                pts.forEach(p=>ctx.lineTo(p[0]*r.width/s.naturalWidth,p[1]*r.height/s.naturalHeight));
                ctx.closePath();ctx.stroke();
            }
            pts.forEach(p=>{
                ctx.fillStyle='#f00';
                ctx.fillRect(p[0]*r.width/s.naturalWidth-3,p[1]*r.height/s.naturalHeight-3,6,6);
            });
        };
        async function done(){
            if(pts.length<3){alert('최소 3점 필요');return}
            await fetch('/set_zone',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({points:pts})});
            ctx.clearRect(0,0,c.width,c.height);alert('영역 설정 완료');
        }
        function reset(){pts=[];ctx.clearRect(0,0,c.width,c.height)}
        </script>
    </body>
    </html>
    """

#============================================
# API: 비디오 스트리밍 피드
#============================================
@app.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

