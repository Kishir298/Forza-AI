from app.db.database import Base, engine
from app.models import Memory  # noqa: F401


def initialize_database() -> None:
    Base.metadata.create_all(bind=engine)
