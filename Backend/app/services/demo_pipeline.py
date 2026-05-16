"""
app/services/demo_pipeline.py
─────────────────────────────
Demo chat pipeline — uses OpenRouter (Gemini) + Cohere RAG without Groq/Postgres.
"""
from __future__ import annotations

import structlog
from starlette.concurrency import run_in_threadpool

from app.agents.rag_agent import ClinicalRAGAgent
from app.agents.intents import IntentType
from app.core.exceptions import LLMProviderError
from app.llm.factory import get_chat_llm, primary_llm_model_name
from app.llm.provider_utils import primary_llm_configured
from app.orchestrator.intent_heuristics import classify_intent_heuristic
from app.rag.retrieval.hybrid_retriever import HybridClinicalRetriever
from app.tracking.workflow_tracker import workflow_tracker

logger = structlog.get_logger(__name__)

_DISCLAIMER = (
    "\n\n⚕️ *This schedule is a general template for planning only. "
    "Confirm all times and doses with your doctor before following it.*"
)
_DISCLAIMER_AR = (
    "\n\nتنبيه طبي: هذه معلومات عامة للمساعدة في التخطيط فقط، ولا تغني عن مراجعة الطبيب "
    "أو الصيدلي، خصوصا قبل تغيير أي جرعة أو دواء."
)


async def run_demo_chat(
    *,
    session_id: str,
    message: str,
    patient_context: dict,
    history: list[dict] | None = None,
) -> tuple[str, dict]:
    history = history or []
    trace_id = workflow_tracker.start(session_id, message)
    intent, confidence, language = classify_intent_heuristic(message)
    patient_context = {**patient_context, "language": language}

    workflow_tracker.update_meta(trace_id, intent=intent, language=language)
    workflow_tracker.step(
        trace_id,
        "demo_router",
        output_summary={"intent": intent, "confidence": confidence},
    )

    try:
        if intent == IntentType.CARE_PLAN_UPDATE.value:
            answer = await _run_schedule_planner(message, patient_context, trace_id, language)
        else:
            rag = ClinicalRAGAgent()
            result = await rag.run(
                user_message=message,
                session_history=history,
                patient_context=patient_context,
                patient_id="demo-patient",
                language=language,
                workflow_trace_id=trace_id,
            )
            answer = result.answer

        if intent != IntentType.GENERAL_CHAT.value:
            disclaimer = _DISCLAIMER_AR if language == "ar" else _DISCLAIMER
            has_disclaimer = "⚕️" in answer or "تنبيه طبي" in answer or disclaimer in answer
            if not has_disclaimer:
                answer = answer.rstrip() + disclaimer

        workflow_tracker.complete(trace_id, response_preview=answer)
        meta = {
            "intent": intent,
            "language": language,
            "workflow_trace_id": trace_id,
            "workflow_steps": workflow_tracker.get_workflow_summary(trace_id),
        }
        return answer, meta

    except Exception as exc:
        logger.error("demo_pipeline.failed", error=str(exc))
        workflow_tracker.fail(trace_id, str(exc))
        raise


async def _run_schedule_planner(
    message: str,
    patient_context: dict,
    trace_id: str,
    language: str,
) -> str:
    workflow_tracker.step(trace_id, "schedule_retrieval", status="started")

    retriever = HybridClinicalRetriever()
    chunks = await run_in_threadpool(
        retriever.retrieve,
        message,
        top_k=5,
        use_hybrid=True,
        use_mmr=True,
        use_rerank=True,
    )

    context = "\n\n".join(
        f"[{c.source}] {c.text[:500]}" for c in chunks[:5]
    ) or "No extra clinical references retrieved."

    meds = ", ".join(patient_context.get("medications", [])) or "none listed"
    conditions = ", ".join(patient_context.get("conditions", [])) or "none listed"

    workflow_tracker.step(
        trace_id,
        "schedule_retrieval",
        output_summary={"chunks": len(chunks)},
    )

    if not primary_llm_configured():
        return _fallback_schedule_text(message, patient_context, chunks, language)

    llm = get_chat_llm()
    system = """You are Nerve AI, a medical care-planning assistant.

Create a clear, friendly DAILY medication schedule for the patient.
Use ONLY medications already listed in their profile unless the user explicitly asks to add a new one.
Use clinical context only for timing guidance (with meals, morning/evening) — do NOT invent new drugs or change prescribed doses.

Format:
- Title: Daily Diabetes Medication Schedule (Template)
- Sections: Morning | Midday | Evening | Bedtime (skip empty sections)
- Each line: time — medication — short note (e.g. "with breakfast")
- End with 2 bullet reminders to confirm with their doctor.

Language rule:
- If language is ar, write the entire answer in Arabic.
- Otherwise write the entire answer in English.

Be concise and practical."""

    user = f"""Patient request: {message}
Language: {language}

Patient profile:
- Name: {patient_context.get('name', 'Patient')}
- Age: {patient_context.get('age', 'unknown')}
- Conditions: {conditions}
- Current medications: {meds}

Clinical reference excerpts:
{context}

Build the schedule now."""

    workflow_tracker.step(trace_id, "schedule_generation", status="started")
    try:
        answer = await llm.chat(
            [{"role": "system", "content": system}, {"role": "user", "content": user}],
            temperature=0.3,
            max_tokens=900,
        )
        workflow_tracker.step(
            trace_id,
            "schedule_generation",
            output_summary={"model": primary_llm_model_name(), "chars": len(answer)},
        )
        return answer.strip()
    except LLMProviderError as exc:
        logger.warning("demo_pipeline.llm_failed_using_template", error=str(exc))
        workflow_tracker.step(
            trace_id,
            "schedule_generation",
            status="completed",
            output_summary={"fallback": "template"},
        )
        return _fallback_schedule_text(message, patient_context, chunks, language)


def _fallback_schedule_text(message: str, patient_context: dict, chunks: list, language: str = "en") -> str:
    meds = patient_context.get("medications", [])
    conditions = ", ".join(patient_context.get("conditions", [])) or "your conditions"

    if language == "ar":
        med_lines = "\n".join(f"- {med}" for med in meds) or "- لا توجد أدوية مسجلة في ملفك التجريبي."
        return "\n".join([
            "## جدول أدوية يومي مقترح",
            "",
            f"هذا قالب عام مبني على ملفك التجريبي ({conditions}). عدل الأوقات حسب وصف طبيبك.",
            "",
            "### الأدوية المسجلة",
            med_lines,
            "",
            "### اقتراح عملي",
            "- خذ ميتفورمين مع الطعام إذا كان موصوفا لك لتقليل اضطراب المعدة.",
            "- خذ دواء الضغط في وقت ثابت يوميا حسب وصف الطبيب.",
            "- لا تغير الجرعات أو توقيت الدواء بدون مراجعة الطبيب أو الصيدلي.",
        ])

    lines = [
        "## Daily Diabetes Medication Schedule (Template)",
        "",
        f"Here is a simple daily plan based on your profile ({conditions}). "
        "Adjust times to match what your doctor prescribed.",
        "",
        "### Morning (with breakfast) — ~8:00 AM",
    ]

    morning, midday, evening = [], [], []
    for med in meds:
        low = med.lower()
        if "metformin" in low or "morning" in low:
            morning.append(med)
        elif "statin" in low or "atorvastatin" in low:
            evening.append(med)
        elif "lisinopril" in low or "amlodipine" in low or "losartan" in low:
            morning.append(med)
        else:
            midday.append(med)

    if morning:
        for m in morning:
            lines.append(f"- {m}")
    else:
        lines.append("- (No morning meds in profile — add per your prescription)")

    lines.extend(["", "### Midday — ~2:00 PM"])
    if midday:
        for m in midday:
            lines.append(f"- {m}")
    else:
        lines.append("- —")

    lines.extend(["", "### Evening (with dinner) — ~8:00 PM"])
    if evening:
        for m in evening:
            lines.append(f"- {m}")
    elif len(meds) > len(morning) + len(midday):
        for m in meds:
            if m not in morning and m not in midday:
                lines.append(f"- {m}")
    else:
        lines.append("- Second dose of metformin if prescribed twice daily")

    lines.extend([
        "",
        "### Reminders",
        "- Take metformin with meals to reduce stomach upset.",
        "- Do not skip blood pressure medication on the same days each week.",
        "- Log blood sugar if your care team asked you to.",
        "",
        "Please confirm exact times and doses with your clinician before following this template.",
    ])
    return "\n".join(lines)
