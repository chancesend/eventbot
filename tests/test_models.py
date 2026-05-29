import pytest
from datetime import datetime, UTC
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker

from eventbot.models import Base, User, Event, Recommendation, Feedback, Run


@pytest.fixture
async def session_factory():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    yield factory
    await engine.dispose()


async def test_user_and_event_creation(session_factory):
    async with session_factory() as session:
        async with session.begin():
            user = User(slug="alice", display_name="Alice")
            session.add(user)
            await session.flush()

            run = Run(user_id=user.id, is_household=False, started_at=datetime.now(UTC))
            session.add(run)
            await session.flush()

            event = Event(
                title="Jazz Night",
                title_slug="jazz-night",
                venue="Blue Moon",
                event_date="2026-05-15",
                url="http://example.com",
            )
            session.add(event)
            await session.flush()

            rec = Recommendation(
                event_id=event.id,
                user_id=user.id,
                run_id=run.id,
                score=0.9,
            )
            session.add(rec)

    async with session_factory() as session:
        from sqlalchemy import select
        fetched = await session.scalar(select(User).where(User.slug == "alice"))
        assert fetched is not None
        assert fetched.display_name == "Alice"


async def test_feedback_upsert_constraint(session_factory):
    from sqlalchemy.exc import IntegrityError
    async with session_factory() as session:
        async with session.begin():
            user = User(slug="bob", display_name="Bob")
            session.add(user)
            await session.flush()
            run = Run(user_id=user.id, started_at=datetime.now(UTC))
            session.add(run)
            await session.flush()
            event = Event(title="X", title_slug="x", venue="V", event_date="2026-06-01", url="http://x.com")
            session.add(event)
            await session.flush()
            session.add(Feedback(event_id=event.id, user_id=user.id, rating=1))

    async with session_factory() as session:
        async with session.begin():
            from sqlalchemy import select
            u = await session.scalar(select(User).where(User.slug == "bob"))
            e = await session.scalar(select(Event).where(Event.title_slug == "x"))
            with pytest.raises(IntegrityError):
                session.add(Feedback(event_id=e.id, user_id=u.id, rating=-1))
                await session.flush()
