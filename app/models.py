from typing import Literal
from pydantic import BaseModel, ConfigDict, Field

class StrictModel(BaseModel):
    model_config = ConfigDict(extra='forbid')

class ToolCall(StrictModel):
    name: str
    resource_id: str | None = None
    period: Literal['current_month', 'this_week', 'all'] = 'all'

class Plan(StrictModel):
    intent: str
    selected_agents: list[str]
    required_tools: list[ToolCall]
    requires_rag: bool
    requires_pin: bool
    requires_confirmation: bool
    missing_information: list[str] = Field(default_factory=list)

class ChatInput(StrictModel):
    conversation_id: str
    message: str = Field(min_length=1, max_length=2000)

class PinInput(StrictModel):
    request_id: str
    pin: str = Field(min_length=4, max_length=12, repr=False)

class ConfirmInput(StrictModel):
    request_id: str
    confirmed: bool
