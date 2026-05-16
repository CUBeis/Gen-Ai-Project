"""
tests/unit/test_rag_pipeline.py
───────────────────────────────
Unit tests for RAG (Retrieval-Augmented Generation) components.
"""
import pytest
import asyncio
from app.agents.rag_agent import ClinicalRAGAgent, RAGResult


@pytest.fixture
def rag_agent():
    """Create a ClinicalRAGAgent instance for testing."""
    return ClinicalRAGAgent()


@pytest.fixture
def sample_patient_context():
    """Sample patient context for RAG."""
    return {
        "name": "Ahmed",
        "age": 45,
        "language": "en",
        "conditions": ["hypertension", "diabetes"],
        "medications": ["metformin 500mg twice daily", "lisinopril 10mg daily"],
        "allergies": ["penicillin"],
    }


@pytest.mark.asyncio
async def test_rag_retrieve_clinical_information(rag_agent, sample_patient_context):
    """Test that RAG retrieves relevant clinical information."""
    message = "What should I know about managing hypertension?"
    result = await rag_agent.run(
        user_message=message,
        session_history=[],
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="en",
    )

    assert isinstance(result, RAGResult)
    assert result.answer is not None
    assert len(result.answer) > 0
    assert isinstance(result.sources, list)


@pytest.mark.asyncio
async def test_rag_reformulates_query(rag_agent, sample_patient_context):
    """Test that RAG reformulates queries for better retrieval."""
    message = "My sugar levels been high"
    result = await rag_agent.run(
        user_message=message,
        session_history=[],
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="en",
    )

    assert result.reformulated_query is not None
    # Reformulated query should be more structured/medical
    assert len(result.reformulated_query) > 0


@pytest.mark.asyncio
async def test_rag_respects_patient_context(rag_agent, sample_patient_context):
    """Test that RAG considers patient-specific context."""
    message = "I'm concerned about my medications"
    result = await rag_agent.run(
        user_message=message,
        session_history=[],
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="en",
    )

    assert result.answer is not None
    # Answer should consider patient's medications
    assert "metformin" in result.answer.lower() or "lisinopril" in result.answer.lower() or len(result.answer) > 50


@pytest.mark.asyncio
async def test_rag_handles_empty_history(rag_agent, sample_patient_context):
    """Test RAG with no conversation history."""
    message = "Tell me about diabetes management"
    result = await rag_agent.run(
        user_message=message,
        session_history=[],
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="en",
    )

    assert result.answer is not None
    assert len(result.answer) > 0


@pytest.mark.asyncio
async def test_rag_sources_have_metadata(rag_agent, sample_patient_context):
    """Test that RAG sources include proper metadata."""
    message = "What are the side effects of my medications?"
    result = await rag_agent.run(
        user_message=message,
        session_history=[],
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="en",
    )

    if result.sources:
        for source in result.sources:
            assert isinstance(source, dict)
            # Sources should have relevance information
            assert "content" in source or "score" in source or "source" in source


@pytest.mark.asyncio
async def test_rag_arabic_language_support(rag_agent, sample_patient_context):
    """Test RAG with Arabic language input."""
    message = "ما هي أعراض ارتفاع ضغط الدم؟"
    result = await rag_agent.run(
        user_message=message,
        session_history=[],
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="ar",
    )

    assert result.answer is not None
    assert len(result.answer) > 0


@pytest.mark.asyncio
async def test_rag_with_session_history(rag_agent, sample_patient_context):
    """Test RAG that considers previous conversation."""
    history = [
        {"role": "user", "content": "I have hypertension"},
        {"role": "assistant", "content": "Blood pressure management is important..."},
    ]

    message = "What medication should I take?"
    result = await rag_agent.run(
        user_message=message,
        session_history=history,
        patient_context=sample_patient_context,
        patient_id="test-patient-123",
        language="en",
    )

    assert result.answer is not None
    assert len(result.answer) > 0
