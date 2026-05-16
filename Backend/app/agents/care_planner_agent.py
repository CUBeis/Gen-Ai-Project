"""
app/agents/care_planner_agent.py
─────────────────────────────────
Care Planner Agent — builds and updates the patient's personalised schedule.

Model : Cohere Command R
Role  : Parse a care plan change request from conversation, apply it to the
        existing plan, and return the updated plan + a confirmation message.

Handles actions:
  - add_medication      → adds dosage + time slots to schedule
  - add_exercise        → adds activity with safety constraints from memory
  - add_appointment     → adds one-off or recurring appointment
  - remove_activity     → removes by name or id
  - full_rebuild        → rebuilds the entire plan from patient profile
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from typing import Optional

import cohere

from app.agents.base import BaseAgent, llm_retry
from app.core.exceptions import AgentError


# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class Activity:
    id:        str
    type:      str          # "medication" | "exercise" | "appointment" | "measurement"
    name:      str
    time:      str          # "08:00"
    days:      list[str]    # ["daily"] or ["Mon", "Wed", "Fri"]
    notes:     Optional[str] = None
    completed_today: bool   = False

    def to_dict(self) -> dict:
        return {
            "id":              self.id,
            "type":            self.type,
            "name":            self.name,
            "time":            self.time,
            "days":            self.days,
            "notes":           self.notes,
            "completed_today": self.completed_today,
        }


@dataclass
class CarePlanResult:
    confirmation_message: str          # shown in chat
    updated_activities:   list[dict]   # full updated plan (list of Activity dicts)
    care_plan_patch:      dict         # delta to push via WebSocket
    action_taken:         str          # what was actually done
    care_plan_updated:    bool = True


# ── Prompts ────────────────────────────────────────────────────────────────────
_SYSTEM_PROMPT = """You are the Care Planner AI for Nerve AI — a personal health management platform.
Your job is to manage a patient's daily care schedule based on what they tell you in the chat.

LANGUAGE RULE: Always respond in the same language the patient used.

INPUT you will receive:
- PATIENT PROFILE: name, age, conditions, medications, allergies, known physical limitations
- CURRENT CARE PLAN: list of existing activities in JSON
- USER REQUEST: what the patient just asked to add/change/remove
- REQUESTED ACTION: one of [add_medication, add_exercise, add_appointment, remove_activity, full_rebuild]

YOUR TASK:
1. Parse the request carefully. Extract: name, dosage (if medication), timing, frequency.
2. Apply the change to the existing care plan.
3. Check for conflicts:
   - Medications: warn if same drug already exists.
   - Exercise: if patient has physical limitations (e.g. knee pain), suggest safer alternatives.
   - Timing: avoid scheduling two activities at the exact same time.
4. Return your response as ONLY valid JSON in this exact format:

{
  "confirmation_message": "<warm conversational message in patient's language confirming what was done>",
  "action_taken": "<what you actually did, e.g. 'Added Metformin 500mg at 08:00 and 20:00'>",
  "updated_activities": [
    {
      "id": "<uuid — keep existing ids, generate new ones for new activities>",
      "type": "<medication|exercise|appointment|measurement>",
      "name": "<display name>",
      "time": "<HH:MM>",
      "days": ["<day>" or "daily"],
      "notes": "<optional note>"
    }
  ]
}

IMPORTANT: Include ALL existing activities in updated_activities — not just the new one.
If removing an activity, omit it from the list.
Never recommend stopping existing medications — only add or schedule."""


# ── Agent ──────────────────────────────────────────────────────────────────────
class CarePlannerAgent(BaseAgent):

    def __init__(self) -> None:
        super().__init__()
        self._client = cohere.AsyncClient(api_key=self.settings.COHERE_API_KEY)
        self._model  = self.settings.COHERE_MODEL

    async def run(
        self,
        user_message: str,
        action: str,
        patient_context: dict,
        current_activities: list[dict],
        language: str = "en",
    ) -> CarePlanResult:
        """
        Apply a care plan change.

        Args:
            user_message       : Raw patient message that triggered this agent.
            action             : One of the action types (add_medication, etc.).
            patient_context    : Dict from ConversationState.patient_context.
            current_activities : Existing activities from PostgreSQL.
            language           : Language code from Router agent.
        """
        t0    = self._now_ms()
        trace = self._start_trace("care_planner_agent", {"action": action, "message": user_message[:200]})

        result = await self._plan(user_message, action, patient_context, current_activities, language)

        latency = self._elapsed(t0)
        self._log_generation(
            trace, "care_plan", self._model,
            prompt=user_message, completion=result.confirmation_message,
            latency_ms=latency,
            metadata={"action": action, "care_plan_updated": result.care_plan_updated},
        )
        self.logger.info(
            "care_planner.done",
            action=action,
            activity_count=len(result.updated_activities),
            latency_ms=latency,
        )
        return result

    @llm_retry(max_attempts=3, reraise_as=AgentError)
    async def _plan(
        self,
        user_message: str,
        action: str,
        patient_context: dict,
        current_activities: list[dict],
        language: str,
    ) -> CarePlanResult:

        user_block = f"""PATIENT PROFILE:
{json.dumps(patient_context, ensure_ascii=False, indent=2)}

CURRENT CARE PLAN:
{json.dumps(current_activities, ensure_ascii=False, indent=2)}

REQUESTED ACTION: {action}
USER REQUEST: {user_message}
LANGUAGE: {language}"""

        response = await self._client.chat(
            model=self._model,
            preamble=_SYSTEM_PROMPT,
            message=user_block,
            temperature=0.3,
            max_tokens=1200,
        )

        raw = response.text.strip()

        # Strip markdown code fences if model added them
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        try:
            data = json.loads(raw)
        except json.JSONDecodeError:
            self.logger.warning("care_planner.json_parse_failed", raw=raw[:300])
            raise AgentError(detail="Care planner returned invalid JSON.")

        # Ensure every activity has an id
        updated = []
        for act in data.get("updated_activities", []):
            if not act.get("id"):
                act["id"] = str(uuid.uuid4())
            updated.append(act)

        # Build the minimal patch for the WebSocket event
        existing_ids = {a.get("id") for a in current_activities}
        new_activities = [a for a in updated if a.get("id") not in existing_ids]

        care_plan_patch = {
            "activities": updated,
            "patch_summary": {
                "action": action,
                "new_activities": new_activities,
            },
        }

        return CarePlanResult(
            confirmation_message=data.get("confirmation_message", "Your care plan has been updated."),
            updated_activities=updated,
            care_plan_patch=care_plan_patch,
            action_taken=data.get("action_taken", action),
        )
