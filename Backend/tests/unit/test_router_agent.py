"""
tests/unit/test_router_agent.py
────────────────────────────────
Unit tests for RouterAgent — intent classification and language detection.
"""
import pytest
import asyncio
from app.agents.router_agent import RouterAgent, IntentType, RoutingResult


@pytest.fixture
def router_agent():
    """Create a RouterAgent instance for testing."""
    return RouterAgent()


@pytest.mark.asyncio
async def test_router_classify_clinical_question(router_agent):
    """Test that clinical questions are classified correctly."""
    message = "I have chest pain and shortness of breath"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=False,
    )

    assert isinstance(result, RoutingResult)
    assert result.intent == IntentType.CLINICAL_QUESTION
    assert result.confidence > 0.5
    assert result.language == "en"


@pytest.mark.asyncio
async def test_router_classify_care_plan_update(router_agent):
    """Test that care plan update intents are detected."""
    message = "I want to add a new medication to my care plan"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=False,
    )

    assert result.intent == IntentType.CARE_PLAN_UPDATE
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_router_detect_arabic_language(router_agent):
    """Test language detection for Arabic."""
    message = "أنا أشعر بالدوار والغثيان"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=False,
    )

    assert result.language == "ar"


@pytest.mark.asyncio
async def test_router_detect_image_analysis_intent(router_agent):
    """Test image analysis intent detection."""
    message = "What does this rash look like?"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=True,
    )

    assert result.intent == IntentType.IMAGE_ANALYSIS
    assert result.confidence > 0.5


@pytest.mark.asyncio
async def test_router_classify_onboarding(router_agent):
    """Test onboarding flow detection."""
    message = "I'm ready to set up my profile"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=False,
    )

    assert result.intent in [
        IntentType.ONBOARDING,
        IntentType.GENERAL_CHAT,
    ]


@pytest.mark.asyncio
async def test_router_classify_general_chat(router_agent):
    """Test general chat classification."""
    message = "Hi, how are you today?"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=False,
    )

    assert result.intent == IntentType.GENERAL_CHAT
    assert result.confidence >= 0.5


@pytest.mark.asyncio
async def test_router_with_session_history(router_agent):
    """Test routing with conversation history."""
    history = [
        {"role": "user", "content": "I have diabetes"},
        {"role": "assistant", "content": "I see. Let's discuss your diabetes management."},
    ]

    message = "Should I take my insulin before or after meals?"
    result = await router_agent.run(
        message=message,
        session_history=history,
        has_image=False,
    )

    assert result.intent == IntentType.CLINICAL_QUESTION
    assert result.language == "en"


@pytest.mark.asyncio
async def test_router_confidence_score(router_agent):
    """Test that confidence scores are in valid range."""
    message = "I have a headache"
    result = await router_agent.run(
        message=message,
        session_history=[],
        has_image=False,
    )

    assert 0.0 <= result.confidence <= 1.0
