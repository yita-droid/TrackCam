"""
Database seeding utilities.

Placeholder for Stage 2 — intentionally empty of table-specific logic since
no ORM models exist yet (cameras, vehicles, etc. arrive in later stages).

Once app/models/*.py exist, this module will grow a `seed_demo_data(db)`
function that inserts a handful of demo cameras and a clean baseline so the
frontend has something to render before any real video has been processed.
"""

from app.utils.logger import get_logger

logger = get_logger(__name__)


def seed_all() -> None:
    """Entry point for `python -m app.database.seed`. No-op until Stage 3+."""
    logger.info("No seed data defined yet — models are introduced in later stages.")


if __name__ == "__main__":
    seed_all()
