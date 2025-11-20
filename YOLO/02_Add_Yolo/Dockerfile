FROM python:3.11-slim

# 필요한 시스템 라이브러리 설치
# libgl1: OpenGL 라이브러리 (libgl1-mesa-glx의 일반적인 대체재)
# libxext6, libsm6: X-Window 관련 (OpenCV/GUI 환경에 필요할 수 있음)
# ffmpeg: 비디오 스트림 처리 (m3u8 포함)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libxext6 \
    libsm6 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# main.py 파일에 'app' 인스턴스가 정의되어 있는지 확인 (현재 파일명을 main.py라고 가정)
COPY main.py yolov8n.pt .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]