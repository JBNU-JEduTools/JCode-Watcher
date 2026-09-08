from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class EventBatchItem(BaseModel):
    type: Literal["snapshot", "build", "run"]
    payload: dict


class EventBatchRequest(BaseModel):
    events: list[EventBatchItem] = Field(min_length=1, max_length=500)


class EventBatchResponse(BaseModel):
    acknowledged_event_ids: list[UUID]
