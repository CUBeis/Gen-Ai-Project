import uuid
from datetime import datetime
from typing import List, Optional, Literal
from pydantic import BaseModel, Field

class ActivityBase(BaseModel):
    type: Literal["medication", "exercise", "appointment", "measurement"]
    name: str
    time: str
    days: List[str]
    notes: Optional[str] = None
    completed_today: bool = False

class Activity(ActivityBase):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))

class CarePlanBase(BaseModel):
    title: Optional[str] = None
    activities: List[Activity] = Field(default_factory=list)

class CarePlanCreate(CarePlanBase):
    patient_id: uuid.UUID

class CarePlanUpdate(BaseModel):
    title: Optional[str] = None
    activities: Optional[List[Activity]] = None

class CarePlanResponse(CarePlanBase):
    id: uuid.UUID
    patient_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CarePlanUpdateRequest(BaseModel):
    action: str
    activity: Optional[dict] = None
    activities: Optional[List[Activity]] = None
    title: Optional[str] = None


class CarePlanUpdateResponse(BaseModel):
    care_plan: CarePlanResponse
    message: str = "Care plan updated"


class ActivityToggleResponse(BaseModel):
    activity_id: str
    completed_today: bool
    care_plan: CarePlanResponse
