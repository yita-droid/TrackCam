"""
Manual end-to-end smoke script (not part of the pytest suite — run directly)
that exercises every router against a live Postgres instance.

Usage:
    export DATABASE_URL="postgresql+psycopg2://postgres:postgres@localhost:5432/trackcam"
    PYTHONPATH=. python scripts/e2e_smoke.py
"""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def check(resp, expected):
    status_ok = resp.status_code == expected
    print(f"{'OK ' if status_ok else 'FAIL'} {resp.request.method} {resp.request.url.path} -> {resp.status_code}")
    if not status_ok:
        print("   body:", resp.text[:300])
    return resp


def main():
    # health
    check(client.get("/health"), 200)

    # cameras
    r = check(
        client.post("/api/cameras", json={"camera_id": "CAM-E2E-1", "name": "E2E Cam", "status": "online"}),
        201,
    )
    camera = r.json()
    check(client.get("/api/cameras"), 200)
    check(client.get(f"/api/cameras/{camera['id']}"), 200)
    check(client.patch(f"/api/cameras/{camera['id']}", json={"status": "maintenance"}), 200)
    # duplicate camera_id should 409
    check(
        client.post("/api/cameras", json={"camera_id": "CAM-E2E-1", "name": "dup", "status": "online"}),
        409,
    )

    # videos
    r = check(
        client.post(
            "/api/videos",
            json={
                "video_id": "VID-E2E-1",
                "camera_id": camera["id"],
                "video_name": "e2e video",
                "file_path": "test/e2e.mp4",
            },
        ),
        201,
    )
    video = r.json()

    # frames
    r = check(
        client.post(
            "/api/frames",
            json={"video_id": video["id"], "frame_number": 1, "image_path": "test/e2e_frame_1.jpg"},
        ),
        201,
    )
    frame = r.json()
    # duplicate frame_number for same video should 409
    check(
        client.post("/api/frames", json={"video_id": video["id"], "frame_number": 1}),
        409,
    )

    # detections — valid ground_truth
    r = check(
        client.post(
            "/api/detections",
            json={
                "frame_id": frame["id"],
                "class_id": 0,
                "class_name": "number_plate",
                "x_center": 0.44,
                "y_center": 0.65,
                "width": 0.05,
                "height": 0.02,
                "source": "ground_truth",
            },
        ),
        201,
    )
    detection = r.json()

    # detections — invalid coordinate should 422 (pydantic validation)
    check(
        client.post(
            "/api/detections",
            json={
                "frame_id": frame["id"],
                "class_id": 0,
                "class_name": "number_plate",
                "x_center": 1.5,
                "y_center": 0.5,
                "width": 0.1,
                "height": 0.1,
                "source": "ground_truth",
            },
        ),
        422,
    )

    # ground_truth with confidence should 422 (model_validator)
    check(
        client.post(
            "/api/detections",
            json={
                "frame_id": frame["id"],
                "class_id": 0,
                "class_name": "number_plate",
                "confidence": 0.9,
                "x_center": 0.1,
                "y_center": 0.1,
                "width": 0.1,
                "height": 0.1,
                "source": "ground_truth",
            },
        ),
        422,
    )

    # license plate
    r = check(
        client.post("/api/license-plates", json={"detection_id": detection["id"]}),
        201,
    )
    plate = r.json()
    check(client.patch(f"/api/license-plates/{plate['id']}", json={"plate_number": "TEST-1234"}), 200)
    check(client.get("/api/license-plates?recognized_only=true"), 200)

    # vehicle
    r = check(
        client.post(
            "/api/vehicles",
            json={"vehicle_id": "VEH-E2E-1", "plate_id": plate["id"], "vehicle_type": "car"},
        ),
        201,
    )
    vehicle = r.json()

    # vehicle event
    check(
        client.post(
            "/api/vehicle-events",
            json={
                "vehicle_id": vehicle["id"],
                "camera_id": camera["id"],
                "frame_id": frame["id"],
                "event_type": "detected",
                "timestamp": "2026-01-01T00:00:00",
            },
        ),
        201,
    )
    check(client.get(f"/api/vehicles/{vehicle['id']}/journey"), 200)

    # alert
    r = check(
        client.post(
            "/api/alerts",
            json={
                "vehicle_id": vehicle["id"],
                "camera_id": camera["id"],
                "alert_type": "watchlist",
                "severity": "high",
                "message": "e2e test alert",
            },
        ),
        201,
    )
    alert = r.json()
    check(client.patch(f"/api/alerts/{alert['id']}", json={"status": "resolved"}), 200)
    check(client.get("/api/alerts?status_filter=resolved"), 200)

    # stats
    check(client.get("/api/stats/cameras/vehicle-counts"), 200)
    check(client.get("/api/stats/detections/daily-count"), 200)
    check(client.get("/api/stats/traffic"), 200)

    # cleanup (cascades handle the rest)
    check(client.delete(f"/api/cameras/{camera['id']}"), 204)

    print("\nAll e2e checks executed.")


if __name__ == "__main__":
    main()
