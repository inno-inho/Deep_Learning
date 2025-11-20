from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
import cv2
import time
import logging
import numpy as np
import os
from pathlib import Path
import yaml
# ----------------------------
# YOLOv8n  추가
# ----------------------------
from ultralytics import YOLO

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI()
STREAM_URL = "https://safecity.busan.go.kr/playlist/cnRzcDovL2d1ZXN0Omd1ZXN0QDEwLjEuMjEwLjIxMDo1NTQvdXM2NzZyM0RMY0RuczYwdE1ESXdMVEk9/index.m3u8"
LABELS_DIR = "labels"  # 라벨 파일 디렉토리
DATA_YAML = "data.yaml"  # 클래스 정보 파일
# ----------------------------
# YOLOv8n  추가
# ----------------------------
model = None
predefined_masks = []  # 미리 정의된 마스크 저장
class_names_from_yaml = {}  # data.yaml에서 읽은 클래스명

# 클래스별 색상 정의 (클래스 ID: BGR 색상)
CLASS_COLORS = {
    0: (0, 255, 0),      # 초록색
    1: (255, 0, 0),      # 파란색
    2: (0, 0, 255),      # 빨간색
    3: (255, 255, 0),    # 시안
    4: (255, 0, 255),    # 마젠타
    5: (0, 255, 255),    # 노란색
    6: (128, 0, 128),    # 보라색
    7: (0, 128, 128),    # 틸
}

# 클래스별 어두운 배경 색상 (라벨 박스용)
CLASS_DARK_COLORS = {
    0: (0, 100, 0),      # 어두운 초록
    1: (100, 0, 0),      # 어두운 파랑
    2: (0, 0, 100),      # 어두운 빨강
    3: (100, 100, 0),    # 어두운 시안
    4: (100, 0, 100),    # 어두운 마젠타
    5: (0, 100, 100),    # 어두운 노랑
    6: (64, 0, 64),      # 어두운 보라
    7: (0, 64, 64),      # 어두운 틸
}

def load_class_names_from_yaml():
    """data.yaml 파일에서 클래스명 로드"""
    global class_names_from_yaml
    
    if not os.path.exists(DATA_YAML):
        logger.warning(f"data.yaml 파일이 없습니다: {DATA_YAML}")
        return
    
    try:
        with open(DATA_YAML, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            
        if 'names' in data:
            names_list = data['names']
            # 리스트를 딕셔너리로 변환 (인덱스: 이름)
            class_names_from_yaml = {i: name for i, name in enumerate(names_list)}
            logger.info(f"data.yaml에서 {len(class_names_from_yaml)}개 클래스 로드: {class_names_from_yaml}")
        else:
            logger.warning("data.yaml에 'names' 필드가 없습니다.")
    except Exception as e:
        logger.error(f"data.yaml 읽기 오류: {e}")

def load_label_files():
    """labels 폴더의 모든 라벨 파일 로드"""
    global predefined_masks
    predefined_masks = []
    
    if not os.path.exists(LABELS_DIR):
        logger.warning(f"라벨 디렉토리가 없습니다: {LABELS_DIR}")
        return
    
    label_files = list(Path(LABELS_DIR).glob("*.txt"))
    logger.info(f"{len(label_files)}개의 라벨 파일을 찾았습니다.")
    
    for label_file in label_files:
        try:
            with open(label_file, 'r') as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) < 5:  # 최소한 class_id + 2개 좌표 필요
                        continue
                    
                    class_id = int(parts[0])
                    # 나머지는 x, y 좌표 쌍 (정규화된 값 0~1)
                    coords = list(map(float, parts[1:]))
                    
                    # x, y 좌표 쌍으로 분리
                    points = []
                    for i in range(0, len(coords), 2):
                        if i + 1 < len(coords):
                            points.append((coords[i], coords[i+1]))
                    
                    if len(points) >= 3:  # 최소 3개 점 필요
                        predefined_masks.append({
                            'class_id': class_id,
                            'points': points,
                            'file': label_file.name
                        })
        except Exception as e:
            logger.error(f"라벨 파일 읽기 오류 ({label_file}): {e}")
    
    logger.info(f"총 {len(predefined_masks)}개의 세그멘테이션 마스크를 로드했습니다.")

def draw_predefined_masks(frame):
    """프레임에 미리 정의된 영역을 클래스별 색상 박스로 그리기"""
    if not predefined_masks:
        return frame
    
    height, width = frame.shape[:2]
    
    # data.yaml에서 읽은 클래스명 사용
    class_names = class_names_from_yaml if class_names_from_yaml else {
        0: "Class_0",
        1: "Class_1", 
        2: "Class_2",
        3: "Class_3",
        4: "Class_4",
        5: "Class_5",
        6: "Class_6",
        7: "Class_7"
    }
    
    for mask_info in predefined_masks:
        class_id = mask_info['class_id']
        normalized_points = mask_info['points']
        
        # 정규화된 좌표를 실제 픽셀 좌표로 변환
        points = np.array([
            [int(x * width), int(y * height)] 
            for x, y in normalized_points
        ], dtype=np.int32)
        
        # 클래스별 색상 가져오기
        color = CLASS_COLORS.get(class_id, (255, 255, 255))
        dark_color = CLASS_DARK_COLORS.get(class_id, (50, 50, 50))
        
        # 윤곽선 그리기 (두께 3)
        cv2.polylines(frame, [points], isClosed=True, color=color, thickness=3)
        
        # 바운딩 박스 계산 (라벨 표시용)
        x_coords = [p[0] for p in points]
        y_coords = [p[1] for p in points]
        x_min, x_max = min(x_coords), max(x_coords)
        y_min, y_max = min(y_coords), max(y_coords)
        
        # 클래스명 가져오기
        class_name = class_names.get(class_id, f"Class_{class_id}")
        
        # 라벨 배경 박스
        label_text = f"{class_name}"
        (text_width, text_height), baseline = cv2.getTextSize(
            label_text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 2
        )
        
        # 라벨 위치 (영역 상단)
        label_x = x_min
        label_y = y_min - 10 if y_min - 10 > text_height else y_min + text_height + 10
        
        # 라벨 배경 (어두운 색상)
        cv2.rectangle(
            frame, 
            (label_x, label_y - text_height - baseline),
            (label_x + text_width, label_y + baseline),
            dark_color,  # 어두운 색상 사용
            -1
        )
        
        # 라벨 텍스트 (흰색)
        cv2.putText(
            frame, 
            label_text, 
            (label_x, label_y - baseline),
            cv2.FONT_HERSHEY_SIMPLEX, 
            0.6, 
            (255, 255, 255),  # 흰색
            2
        )
    
    return frame, predefined_masks

def calculate_overlap_and_overstep(seg_mask, label_mask):
    """세그멘테이션과 라벨 영역의 겹침 및 이탈 정도 계산"""
    if seg_mask is None or label_mask is None:
        return 0.0
    
    # 라벨 영역 내부
    inside = cv2.bitwise_and(seg_mask, label_mask)
    inside_area = np.sum(inside > 0)
    
    # 세그멘테이션 전체 영역
    seg_area = np.sum(seg_mask > 0)
    
    if seg_area == 0:
        return 0.0
    
    # 이탈 비율 = (전체 - 내부) / 전체
    overstep_ratio = (seg_area - inside_area) / seg_area
    
    return overstep_ratio

def get_lighter_color(color):
    """색상을 더 밝게(연하게) 만들기"""
    # BGR 값을 증가시켜 연한 색상 생성
    b, g, r = color
    lighter_b = min(255, b + int((255 - b) * 0.5))
    lighter_g = min(255, g + int((255 - g) * 0.5))
    lighter_r = min(255, r + int((255 - r) * 0.5))
    return (lighter_b, lighter_g, lighter_r)

def find_matching_label_class(seg_mask, predefined_masks, width, height):
    """세그멘테이션이 어느 라벨 영역과 가장 많이 겹치는지 찾기"""
    max_overlap = 0
    matching_class_id = None
    
    for mask_info in predefined_masks:
        # 라벨 마스크 생성
        label_mask = np.zeros((height, width), dtype=np.uint8)
        normalized_points = mask_info['points']
        points = np.array([
            [int(x * width), int(y * height)] 
            for x, y in normalized_points
        ], dtype=np.int32)
        cv2.fillPoly(label_mask, [points], 255)
        
        # 겹침 정도 계산
        overlap = cv2.bitwise_and(seg_mask, label_mask)
        overlap_area = np.sum(overlap > 0)
        
        if overlap_area > max_overlap:
            max_overlap = overlap_area
            matching_class_id = mask_info['class_id']
    
    return matching_class_id

def draw_segmentation_contours(frame, results, predefined_masks):
    """세그멘테이션 윤곽선만 그리기 (이탈 정도에 따라 색상 변경)"""
    if not results or len(results) == 0:
        return frame
    
    result = results[0]
    height, width = frame.shape[:2]
    
    # 전체 라벨 영역 마스크 생성
    label_mask = np.zeros((height, width), dtype=np.uint8)
    for mask_info in predefined_masks:
        normalized_points = mask_info['points']
        points = np.array([
            [int(x * width), int(y * height)] 
            for x, y in normalized_points
        ], dtype=np.int32)
        cv2.fillPoly(label_mask, [points], 255)
    
    # 세그멘테이션 결과 처리
    if result.masks is not None:
        for i, mask in enumerate(result.masks.data):
            # 마스크를 numpy 배열로 변환
            mask_np = mask.cpu().numpy()
            mask_resized = cv2.resize(mask_np, (width, height))
            mask_binary = (mask_resized > 0.5).astype(np.uint8) * 255
            
            # 이탈 정도 계산
            overstep_ratio = calculate_overlap_and_overstep(mask_binary, label_mask)
            
            # 매칭되는 라벨 클래스 찾기
            matching_class_id = find_matching_label_class(mask_binary, predefined_masks, width, height)
            
            # 이탈 정도에 따른 색상 결정
            if overstep_ratio < 0.1:  # 10% 미만 이탈 - 정상
                if matching_class_id is not None:
                    # 해당 클래스 색상의 연한 버전
                    base_color = CLASS_COLORS.get(matching_class_id, (255, 255, 255))
                    color = get_lighter_color(base_color)
                else:
                    color = (128, 255, 128)  # 연한 초록
            elif overstep_ratio < 0.3:  # 30% 미만 이탈 - 경고
                color = (0, 165, 255)  # 주황색
            else:  # 30% 이상 이탈 - 위험
                color = (0, 0, 255)  # 빨간색
            
            # 윤곽선 찾기
            contours, _ = cv2.findContours(mask_binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
            
            # 윤곽선 그리기 (굵기 2)
            cv2.drawContours(frame, contours, -1, color, 2)
    
    return frame

def draw_detection_info(frame, results):
    """상단에 감지된 객체 정보 표시 (박스 없이 텍스트만)"""
    if not results or len(results) == 0:
        return frame
    
    result = results[0]
    
    # 감지된 객체 정보 수집
    detected_objects = {}
    
    if result.boxes is not None and len(result.boxes) > 0:
        for box in result.boxes:
            # 클래스 ID와 이름
            class_id = int(box.cls[0])
            class_name = result.names[class_id] if class_id in result.names else f"Class_{class_id}"
            confidence = float(box.conf[0])
            
            # 신뢰도가 일정 이상인 것만 카운트
            if confidence > 0.3:
                if class_name not in detected_objects:
                    detected_objects[class_name] = 0
                detected_objects[class_name] += 1
    
    # 상단에 반투명 배경 그리기
    if detected_objects:
        overlay = frame.copy()
        # 배경 높이 계산 (객체 개수에 따라)
        info_height = 40 + (len(detected_objects) * 35)
        cv2.rectangle(overlay, (0, 0), (frame.shape[1], info_height), (0, 0, 0), -1)
        frame = cv2.addWeighted(overlay, 0.6, frame, 0.4, 0)
        
        # 제목
        cv2.putText(frame, "Detected Objects:", (10, 30), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.8, (255, 255, 255), 2)
        
        # 각 객체 정보 표시
        y_offset = 65
        for class_name, count in detected_objects.items():
            text = f"{class_name}: {count}"
            
            # 객체별 색상 (클래스 이름 해시로 일관된 색상)
            color_hash = hash(class_name) % 6
            colors = [
                (0, 255, 255),    # 노란색
                (255, 0, 255),    # 마젠타
                (255, 255, 0),    # 시안
                (0, 165, 255),    # 오렌지
                (255, 0, 0),      # 파란색
                (0, 255, 0),      # 초록색
            ]
            text_color = colors[color_hash]
            
            # 텍스트 표시
            cv2.putText(frame, text, (20, y_offset), 
                       cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
            
            y_offset += 35
    
    return frame

def get_model():
    global model
    if model is None:
        model = YOLO("best.pt") # model = YOLO("yolov8n.pt")
        # 앱 시작 시 클래스명 및 라벨 파일 로드
        load_class_names_from_yaml()
        load_label_files()
    return model

def create_video_capture():
    """비디오 캡처 객체 생성"""
    cap = cv2.VideoCapture(STREAM_URL)
    
    # 버퍼 크기 최소화
    try:
        cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
    except Exception as e:
        logger.warning(f"버퍼 크기 설정 실패: {e}")
    
    # 타임아웃 설정 (OpenCV 버전에 따라 지원 여부 다름)
    try:
        if hasattr(cv2, 'CAP_PROP_TIMEOUT'):
            cap.set(cv2.CAP_PROP_TIMEOUT, 10000)  # 타임아웃 10초
    except Exception as e:
        logger.warning(f"타임아웃 설정 실패: {e}")
    
    return cap

def gen_frames():
    cap = None
    retry_count = 0
    max_retries = 3
    consecutive_failures = 0
    max_consecutive_failures = 10
    
    try:
        while True:
            # 캡처 객체가 없거나 유효하지 않으면 생성/재생성
            if cap is None or not cap.isOpened():
                if cap is not None:
                    cap.release()
                
                logger.info(f"스트림 연결 시도 중... (시도 {retry_count + 1}/{max_retries})")
                cap = create_video_capture()
                
                if not cap.isOpened():
                    retry_count += 1
                    if retry_count >= max_retries:
                        logger.error("최대 재시도 횟수 초과")
                        break
                    time.sleep(2)  # 재연결 대기
                    continue
                
                logger.info("스트림 연결 성공")
                retry_count = 0
                consecutive_failures = 0
            
            # 프레임 읽기
            ret, frame = cap.read()
            
            if not ret:
                consecutive_failures += 1
                logger.warning(f"프레임 읽기 실패 ({consecutive_failures}/{max_consecutive_failures})")
                
                if consecutive_failures >= max_consecutive_failures:
                    logger.error("연속 실패 횟수 초과. 재연결 시도...")
                    if cap is not None:
                        cap.release()
                    cap = None
                    consecutive_failures = 0
                    time.sleep(1)
                continue
            
            # 프레임 읽기 성공
            consecutive_failures = 0
            
            try:
                # ----------------------------
                # 1. YOLOv8n 실시간 감지 (원본 프레임에서 먼저 실행)
                # ----------------------------
                results = get_model()(frame)
                
                # ----------------------------
                # 2. 미리 정의된 라벨 영역을 클래스별 색상 박스로 그리기
                # ----------------------------
                frame, masks_info = draw_predefined_masks(frame)
                
                # ----------------------------
                # 3. 세그멘테이션 윤곽선만 그리기 (이탈 정도에 따라 색상 변경)
                # ----------------------------
                frame = draw_segmentation_contours(frame, results, masks_info)
                
                # ----------------------------
                # 4. 상단에 감지된 객체 정보 텍스트 표시
                # ----------------------------
                frame = draw_detection_info(frame, results)
                
                # JPEG 인코딩
                ret_encode, buffer = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
                
                if not ret_encode:
                    logger.warning("프레임 인코딩 실패")
                    continue
                
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')
                
            except Exception as e:
                logger.error(f"프레임 처리 중 오류: {e}")
                continue
                
    except GeneratorExit:
        logger.info("클라이언트 연결 종료")
    except Exception as e:
        logger.error(f"스트리밍 중 오류 발생: {e}")
    finally:
        # 리소스 정리
        if cap is not None:
            cap.release()
            logger.info("비디오 캡처 리소스 해제")

@app.get("/init", response_class=HTMLResponse)
def init():
    return """
    <html>
        <head>
            <title>Stream Viewer with Segmentation</title>
            <style>
                body { margin: 0; padding: 20px; font-family: Arial, sans-serif; }
                h1 { color: #333; }
                .info { 
                    background: #f0f0f0; 
                    padding: 15px; 
                    margin: 10px 0; 
                    border-radius: 5px;
                }
                .button {
                    background: #4CAF50;
                    color: white;
                    padding: 10px 20px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    margin: 5px;
                }
                .button:hover { background: #45a049; }
            </style>
        </head>
        <body>
            <h1>YOLO 세그멘테이션 스트림 뷰어</h1>
            <div class="info">
                <p><strong>기준선 (굵기 3)</strong>: labels 영역, 클래스별 색상 (data.yaml)</p>
                <p><strong>세그멘테이션 윤곽선 (굵기 2)</strong>: YOLO 실시간 감지</p>
                <p><strong>색상 표시</strong>: 연한색(정상, 기준선 내) / 주황(경고) / 빨강(위험)</p>
                <p><strong>상단 텍스트</strong>: 감지된 객체명과 개수 정보</p>
                <button class="button" onclick="window.location.reload()">새로고침</button>
                <button class="button" onclick="location.href='/labels/info'">라벨 정보</button>
            </div>
            <img src="/video_feed" style='width:100%; max-width:1280px; border: 2px solid #333;'>
        </body>
    </html>
    """

@app.get("/video_feed")
def video_feed():
    return StreamingResponse(gen_frames(), media_type="multipart/x-mixed-replace; boundary=frame")

@app.get("/labels/info")
def labels_info():
    """로드된 라벨 정보 확인"""
    return {
        "total_masks": len(predefined_masks),
        "masks": [
            {
                "class_id": mask['class_id'],
                "points_count": len(mask['points']),
                "source_file": mask['file']
            }
            for mask in predefined_masks
        ]
    }

@app.post("/labels/reload")
def reload_labels():
    """라벨 파일 다시 로드"""
    load_label_files()
    return {
        "status": "success",
        "message": f"{len(predefined_masks)}개의 마스크를 다시 로드했습니다."
    }

