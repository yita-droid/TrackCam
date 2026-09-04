
# TrackCam — integrated prototype

This package contains the TrackCam Next.js frontend and FastAPI backend wired together.

## Run locally

### 1. Backend
```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Backend:
- API: http://localhost:8000
- Swagger: http://localhost:8000/docs
- Health: http://localhost:8000/health
- Dashboard data: http://localhost:8000/api/dashboard

PostgreSQL is optional for this prototype API. If it is not running, `/health` reports `degraded` but the dashboard API still works.

### 2. Frontend
Open a second PowerShell:
```powershell
cd frontend
Copy-Item .env.local.example .env.local
npm install
npm run dev
```

Open http://localhost:3000.

## What is integrated

- Frontend polls `/health` and `/api/dashboard` every 15 seconds.
- Overview KPIs, camera network, and alerts are populated from the backend.
- ANPR local-file upload sends the image/video to `POST /api/anpr/analyze`.
- Vehicle tracking and alerts use backend dashboard data.
- WebSocket endpoint is available at `/ws/live` for future real-time inference events.
- If the backend is unavailable, the UI falls back to the original local prototype data.

## Important

The supplied backend is Stage 2 and does not contain trained model weights or a completed YOLO/plate/OCR inference pipeline. The upload endpoint therefore reports `model_not_available` instead of inventing a plate result.

Put real model weights in `backend/models/` and implement the inference service behind the existing `/api/anpr/analyze` contract when your trained models are ready.
