"""
Test fixtures: async httpx client + fresh Postgres test DB per session.

Requires a running Postgres. Override via env `TEST_DATABASE_URL`.
Defaults to the compose `db` service (localhost:5432 with dotto/dotto creds).
"""
import os
import uuid
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL",
    "postgresql+asyncpg://dotto:dotto_dev@localhost:5432/dotto_test",
)
os.environ["DATABASE_URL"] = TEST_DATABASE_URL
os.environ.setdefault("JWT_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CORS_ORIGINS", "http://testserver")
os.environ.setdefault("APP_URL", "http://testserver")
os.environ.setdefault("DEBUG", "false")

from app.config import get_settings  # noqa: E402
from app.database import Base, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app.services.auth import hash_pin, create_access_token  # noqa: E402

get_settings.cache_clear()


@pytest_asyncio.fixture(scope="session")
async def engine():
    eng = create_async_engine(TEST_DATABASE_URL, echo=False, pool_pre_ping=True)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield eng
    await eng.dispose()


@pytest_asyncio.fixture
async def db_session(engine) -> AsyncSession:
    """Function-scoped session. Truncates tables between tests."""
    async with engine.begin() as conn:
        for table in reversed(Base.metadata.sorted_tables):
            await conn.execute(table.delete())
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with session_maker() as s:
        yield s


@pytest_asyncio.fixture
async def client(engine, db_session) -> AsyncClient:
    """Async HTTP client bound to the test DB."""
    session_maker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _override_get_db():
        async with session_maker() as s:
            try:
                yield s
                await s.commit()
            except Exception:
                await s.rollback()
                raise

    app.dependency_overrides[get_db] = _override_get_db
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as c:
        yield c
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def admin(db_session):
    from app.models.operator import Operator
    op = Operator(
        name="Admin Test",
        phone="+390000000001",
        pin_hash=hash_pin("1234"),
        is_admin=True,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)
    return op


@pytest_asyncio.fixture
async def operator(db_session):
    from app.models.operator import Operator
    op = Operator(
        name="Operator Test",
        phone="+390000000002",
        pin_hash=hash_pin("5678"),
        is_admin=False,
        is_active=True,
    )
    db_session.add(op)
    await db_session.commit()
    await db_session.refresh(op)
    return op


@pytest.fixture
def admin_token(admin):
    return create_access_token(admin.id)


@pytest.fixture
def operator_token(operator):
    return create_access_token(operator.id)


@pytest_asyncio.fixture
async def seed_event(db_session):
    from app.models.event import Event
    from app.models.rack import Rack
    now = datetime.now(timezone.utc)
    event = Event(
        name="Evento Test",
        slug="evento-test",
        location="Milano",
        start_date=now + timedelta(hours=1),
        end_date=now + timedelta(days=1),
        checkin_opens_at=now - timedelta(minutes=5),
        total_capacity=24,
        fast_mode_threshold=80,
        is_active=True,
    )
    db_session.add(event)
    await db_session.flush()
    for n in range(1, 3):
        db_session.add(Rack(event_id=event.id, rack_number=n, slots=12, label=f"Rast. {n}"))
    await db_session.commit()
    await db_session.refresh(event)
    return event


def auth_headers(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}
