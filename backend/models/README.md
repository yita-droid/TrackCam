# Model weights

These files are **git-ignored** (see `backend/.gitignore`) because they are large
binaries. Place them here manually before running the backend:

| File | What it is | Where to get it |
|------|------------|-----------------|
| `plate.pt` | YOLO license-plate detector (required for ANPR) | the AIML dev's `license_plate_detector.pt` |
| `yolo11n.pt` | vehicle detector (optional; `yolov8n.pt` also works) | Ultralytics auto-download or the demo repo |

The ANPR endpoint (`POST /api/anpr/analyze`) reports `model_not_available`
until at least `plate.pt` is present. OCR uses **EasyOCR** (installed via
`requirements.txt`); its recognition models (~100 MB) download automatically on
first inference.
