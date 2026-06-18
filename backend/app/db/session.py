"""SQLite engine + session. WAL mode and FK enforcement are enabled per connection."""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import event
from sqlalchemy.engine import Engine
from sqlmodel import Session, SQLModel, create_engine

from app.config import settings

connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, echo=False, connect_args=connect_args)


@event.listens_for(Engine, "connect")
def _sqlite_pragmas(dbapi_connection, _connection_record) -> None:  # noqa: ANN001
    """Enable WAL + foreign keys on every SQLite connection (DESIGN.md 6.1)."""
    try:
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA foreign_keys=ON")
        cur.close()
    except Exception:  # pragma: no cover - non-sqlite backends
        pass


def init_db() -> None:
    """Create tables if they don't exist and guarantee the sentinel dimension members.

    (Alembic owns migrations in production; create_all is the local-dev convenience.)
    """
    import app.db.models as m  # noqa: F401  (register models on the metadata)

    SQLModel.metadata.create_all(engine)
    _ensure_sentinels()


def _ensure_sentinels() -> None:
    """Insert the id=0 'All/Unallocated' member in every dimension (DESIGN.md 5.1)."""
    from app.db.models import DimDepartment, DimEntity, DimProject, DimRegion

    seeds = [
        (DimEntity, "entity_id", "ALL", "All Entities"),
        (DimDepartment, "department_id", "UNALLOC", "Unallocated"),
        (DimProject, "project_id", "NONE", "No Project"),
        (DimRegion, "region_id", "ALL", "All Regions"),
    ]
    with Session(engine) as s:
        changed = False
        for model, pk, code, name in seeds:
            if s.get(model, 0) is None:
                obj = model(code=code, name=name)
                setattr(obj, pk, 0)
                s.add(obj)
                changed = True
        if changed:
            s.commit()


def get_session() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    with Session(engine) as session:
        yield session
