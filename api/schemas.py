import re
from datetime import datetime

from pydantic import BaseModel, EmailStr, field_validator

from models import TaskStatus

# ---------------------------------------------------------------------------
# Auth
# ---------------------------------------------------------------------------

SLUG_RE = re.compile(r"^[a-z0-9-]+$")


class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str

    @field_validator("username")
    @classmethod
    def username_valid(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_-]{3,64}$", v):
            raise ValueError("username must be 3-64 alphanumeric characters, _ or -")
        return v

    @field_validator("password")
    @classmethod
    def password_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("password must be at least 8 characters")
        return v


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: str
    username: str
    email: str
    created_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---------------------------------------------------------------------------
# Rooms
# ---------------------------------------------------------------------------


class RoomCreate(BaseModel):
    name: str
    display_name: str

    @field_validator("name")
    @classmethod
    def name_is_slug(cls, v: str) -> str:
        if not SLUG_RE.match(v):
            raise ValueError("name must be lowercase alphanumeric and hyphens only (^[a-z0-9-]+$)")
        if len(v) > 128:
            raise ValueError("name must be 128 characters or fewer")
        return v


class RoomOut(BaseModel):
    id: str
    name: str
    display_name: str
    owner_id: str
    workspace_path: str
    created_at: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Agents
# ---------------------------------------------------------------------------


class AgentInvokeRequest(BaseModel):
    room_id: str
    prompt: str
    task_id: str | None = None
    history: list[dict] | None = None  # [{role, content}]


class AgentInvokeResponse(BaseModel):
    content: str
    task_id: str
    task_status: str
    agent_id: str


class AgentTaskOut(BaseModel):
    id: str
    room_id: str
    created_by: str
    title: str
    description: str | None
    status: TaskStatus
    assigned_agent: str | None
    result: str | None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
