import enum
import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class TaskStatus(str, enum.Enum):
    open = "open"
    in_progress = "in_progress"
    submitted = "submitted"
    completed = "completed"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str | None] = mapped_column(String, nullable=True)
    # Reserved for future GitHub OAuth support
    github_id: Mapped[str | None] = mapped_column(String, unique=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    rooms: Mapped[list["Room"]] = relationship(back_populates="owner")
    tasks: Mapped[list["AgentTask"]] = relationship(back_populates="creator")


class Room(Base):
    """Maps to the Arena (Scope) primitive in RSCF.
    Each room isolates its agent work under .socialware-workspace/{name}/"""

    __tablename__ = "rooms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    # slug: validated as ^[a-z0-9-]+$ in schema layer to prevent path traversal
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    display_name: Mapped[str] = mapped_column(String(256), nullable=False)
    owner_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    # Absolute path: WORKSPACE_ROOT / name (set at creation time)
    workspace_path: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))

    owner: Mapped["User"] = relationship(back_populates="rooms")
    tasks: Mapped[list["AgentTask"]] = relationship(back_populates="room")


class AgentTask(Base):
    """Maps to Commitment + Flow primitive in RSCF.
    status transitions mirror the TaskArena flow: open → in_progress → submitted → completed."""

    __tablename__ = "agent_tasks"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id: Mapped[str] = mapped_column(ForeignKey("rooms.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(512), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[TaskStatus] = mapped_column(SAEnum(TaskStatus), default=TaskStatus.open)
    assigned_agent: Mapped[str | None] = mapped_column(String, nullable=True)
    result: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON string
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    room: Mapped["Room"] = relationship(back_populates="tasks")
    creator: Mapped["User"] = relationship(back_populates="tasks")
