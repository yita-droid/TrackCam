# =============================================================================
# TrackCam Backend — Dockerfile
#
# CPU image by default. For GPU (CUDA) inference, swap the base image for an
# nvidia/cuda-* runtime image and install matching torch/paddlepaddle CUDA
# wheels — see README.md "Model installation" for exact commands. The app
# code itself auto-detects CUDA vs CPU at runtime (app/ai/model_manager.py,
# added in Stage 3+), so no code changes are required either way.
# =============================================================================
FROM python:3.11-slim

# System deps required by OpenCV / PaddleOCR at runtime
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgl1 \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

COPY . .

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
