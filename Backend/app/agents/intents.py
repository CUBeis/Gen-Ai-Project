"""Shared intent taxonomy for all agents."""
from enum import Enum


class IntentType(str, Enum):
    ONBOARDING = "onboarding"
    CARE_PLAN_UPDATE = "care_plan_update"
    CLINICAL_QUESTION = "clinical_question"
    IMAGE_ANALYSIS = "image_analysis"
    GENERAL_CHAT = "general_chat"
