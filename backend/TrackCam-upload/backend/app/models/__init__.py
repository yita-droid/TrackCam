"""
ORM models package.

Every model must be imported here so that:
  - `Base.metadata.create_all()` (dev bootstrapping) discovers every table
  - Alembic autogeneration (once alembic/env.py is added) sees every model
  - SQLAlchemy can resolve string-based relationship() references between
    models that live in different modules
"""

from app.models.alert import Alert
from app.models.camera import Camera
from app.models.detection import Detection
from app.models.frame import Frame
from app.models.license_plate import LicensePlate
from app.models.vehicle import Vehicle
from app.models.vehicle_event import VehicleEvent
from app.models.video import Video

__all__ = [
    "Camera",
    "Video",
    "Frame",
    "Detection",
    "LicensePlate",
    "Vehicle",
    "VehicleEvent",
    "Alert",
]
