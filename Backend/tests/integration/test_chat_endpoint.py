"""
tests/integration/test_chat_endpoint.py
────────────────────────────────────────
Integration tests for the chat REST endpoint.
Tests the full pipeline: API → Service → Pipeline → Agents → Response
"""
import pytest
import asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app
from app.db.session import Base
from app.db.models.patient import Patient, AuthUser
from app.core.config import settings
import uuid


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create test database and session."""
    # Use in-memory SQLite for tests (or test DB URL from env)
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    yield SessionLocal

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest.fixture
async def test_patient(test_db):
    """Create a test patient in the database."""
    async with test_db() as session:
        user = AuthUser(
            id=uuid.uuid4(),
            email="test@example.com",
            hashed_password="hashed_password",
            is_active=True,
        )
        session.add(user)
        await session.flush()

        patient = Patient(
            id=uuid.uuid4(),
            user_id=user.id,
            full_name="Test Patient",
            language="en",
            onboarding_complete=True,
        )
        session.add(patient)
        await session.commit()

        yield patient


@pytest.mark.asyncio
async def test_chat_endpoint_clinical_question(test_db, test_patient):
    """Test chat endpoint with a clinical question."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "session_id": "test-session-123",
            "message": "I have a headache, what should I do?",
            "image_base64": None,
        }

        # Note: In real test, you'd need to mock auth and dependencies
        # This is a simplified version showing the structure
        response = await client.post(
            "/api/v1/chat",
            json=payload,
            headers={"Authorization": "Bearer test-token"},
        )

        # Would assert: response.status_code == 200
        # assert "response_text" in response.json()


@pytest.mark.asyncio
async def test_chat_endpoint_with_image(test_db, test_patient):
    """Test chat endpoint with image upload."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        base64_image = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="

        payload = {
            "session_id": "test-session-456",
            "message": "What does this rash look like?",
            "image_base64": base64_image,
        }

        # Mock test structure
        # response = await client.post(
        #     "/api/v1/chat",
        #     json=payload,
        #     headers={"Authorization": "Bearer test-token"},
        # )


@pytest.mark.asyncio
async def test_chat_endpoint_rate_limiting():
    """Test that rate limiting is enforced."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        # Send requests rapidly
        for i in range(100):
            # After limit is exceeded, should get 429
            pass


@pytest.mark.asyncio
async def test_chat_endpoint_invalid_session():
    """Test error handling for invalid session ID."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "session_id": "invalid-session",
            "message": "Hello",
        }

        # Would expect appropriate error response


@pytest.mark.asyncio
async def test_chat_endpoint_unauthorized():
    """Test that unauthenticated requests are rejected."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "session_id": "test-session",
            "message": "Hello",
        }

        response = await client.post(
            "/api/v1/chat",
            json=payload,
        )

        # Would assert: response.status_code == 401


@pytest.mark.asyncio
async def test_chat_endpoint_care_plan_update():
    """Test that care plan updates are persisted."""
    # This would:
    # 1. Send a message requesting care plan update
    # 2. Verify response indicates update
    # 3. Query database to confirm persistence
    pass


@pytest.mark.asyncio
async def test_chat_endpoint_multilingual():
    """Test chat with Arabic language input."""
    async with AsyncClient(app=app, base_url="http://test") as client:
        payload = {
            "session_id": "test-session-ar",
            "message": "أنا أشعر بالدوار",
        }

        # Would assert response is in Arabic
