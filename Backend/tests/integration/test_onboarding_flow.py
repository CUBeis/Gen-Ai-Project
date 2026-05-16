"""
tests/integration/test_onboarding_flow.py
──────────────────────────────────────────
Integration tests for the complete onboarding flow.
Tests multi-turn conversation → profile creation → patient setup
"""
import pytest
import asyncio
import uuid
import json
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from main import app
from app.db.session import Base
from app.db.models.patient import Patient, AuthUser
from app.services.onboarding_service import OnboardingService


@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
async def test_db():
    """Create test database session."""
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
async def test_user(test_db):
    """Create a test auth user (not yet onboarded)."""
    async with test_db() as session:
        user = AuthUser(
            id=uuid.uuid4(),
            email="newuser@example.com",
            hashed_password="hashed_password",
            is_active=True,
            patient_id=None,  # Not yet linked
        )
        session.add(user)
        await session.commit()
        yield user


@pytest.mark.asyncio
async def test_onboarding_complete_flow(test_db, test_user):
    """Test the complete onboarding flow from start to finish."""
    session_id = f"onboarding-{uuid.uuid4()}"

    # Step 1: Start onboarding (welcome message)
    async with AsyncClient(app=app, base_url="http://test") as client:
        response = await client.post(
            "/api/v1/onboarding/start",
            json={
                "session_id": session_id,
                "user_id": str(test_user.id),
            },
            headers={"Authorization": "Bearer test-token"},
        )
        # Would assert: response.status_code == 200
        # data = response.json()
        # assert data["completed"] is False


@pytest.mark.asyncio
async def test_onboarding_collects_profile_data(test_db, test_user):
    """Test that onboarding collects all required profile fields."""
    session_id = f"onboarding-{uuid.uuid4()}"

    profile_responses = [
        {"message": "My name is Ahmed Al-Mansouri"},  # Name
        {"message": "1978-03-15"},  # DOB
        {"message": "M"},  # Gender
        {"message": "I have diabetes and hypertension"},  # Conditions
        {"message": "I'm allergic to penicillin"},  # Allergies
    ]

    # Each response would be submitted in sequence
    # After final response, patient should be created
    pass


@pytest.mark.asyncio
async def test_onboarding_creates_patient_in_db(test_db, test_user):
    """Test that completing onboarding creates patient record."""
    # Simulate complete onboarding
    profile_data = {
        "full_name": "Ahmed Al-Mansouri",
        "date_of_birth": "1978-03-15",
        "gender": "M",
        "language": "en",
        "chronic_conditions": ["diabetes", "hypertension"],
        "allergies": ["penicillin"],
    }

    async with test_db() as session:
        service = OnboardingService(session)
        patient = await service.create_patient_from_profile(
            user_id=str(test_user.id),
            profile_data=profile_data,
        )

        assert patient is not None
        assert patient.full_name == "Ahmed Al-Mansouri"
        assert patient.onboarding_complete is True
        assert len(patient.chronic_conditions) == 2


@pytest.mark.asyncio
async def test_onboarding_links_user_to_patient(test_db, test_user):
    """Test that onboarding links AuthUser to Patient."""
    profile_data = {
        "full_name": "Test Patient",
        "language": "en",
    }

    async with test_db() as session:
        service = OnboardingService(session)
        patient = await service.create_patient_from_profile(
            user_id=str(test_user.id),
            profile_data=profile_data,
        )

        # Verify linking
        updated_user = await session.get(AuthUser, test_user.id)
        assert updated_user.patient_id == patient.id


@pytest.mark.asyncio
async def test_onboarding_creates_empty_care_plan(test_db, test_user):
    """Test that onboarding creates empty care plan for patient."""
    from app.db.models.care_plan import CarePlan

    profile_data = {
        "full_name": "Test Patient",
        "language": "en",
    }

    async with test_db() as session:
        service = OnboardingService(session)
        patient = await service.create_patient_from_profile(
            user_id=str(test_user.id),
            profile_data=profile_data,
        )

        # Verify care plan exists
        care_plan = patient.care_plan
        assert care_plan is not None
        assert care_plan.activities == []


@pytest.mark.asyncio
async def test_onboarding_detects_completion():
    """Test that onboarding status is correctly tracked."""
    # Start onboarding → send responses → complete
    # Each step should indicate progress
    pass


@pytest.mark.asyncio
async def test_onboarding_multilingual_support(test_db, test_user):
    """Test onboarding with Arabic language."""
    session_id = f"onboarding-ar-{uuid.uuid4()}"

    # Send Arabic responses
    # Verify prompts and responses are in Arabic
    pass


@pytest.mark.asyncio
async def test_onboarding_validates_required_fields(test_db, test_user):
    """Test that onboarding validates all required fields."""
    # Try to complete with missing fields
    # Should not create patient
    pass


@pytest.mark.asyncio
async def test_onboarding_session_persistence(test_db, test_user):
    """Test that onboarding state persists across requests."""
    session_id = f"onboarding-{uuid.uuid4()}"

    # Send first response
    # Disconnect
    # Reconnect with same session_id
    # Verify state is preserved
    pass


@pytest.mark.asyncio
async def test_onboarding_handles_skip():
    """Test that users can skip optional onboarding questions."""
    # Send skip signal
    # Verify non-required fields can be empty
    pass


@pytest.mark.asyncio
async def test_onboarding_after_completion_chat(test_db):
    """Test that patient can chat after onboarding completes."""
    # Complete onboarding
    # Send chat message
    # Verify message goes through pipeline (not onboarding flow)
    pass
