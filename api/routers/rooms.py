import os

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from deps import get_current_user
from models import Room, User
from schemas import RoomCreate, RoomOut

router = APIRouter()

WORKSPACE_ROOT = os.path.abspath(
    os.getenv("WORKSPACE_ROOT", os.path.join(os.path.dirname(__file__), "../../.socialweb-workspace"))
)


def _workspace_path(room_name: str) -> str:
    """Build and validate the workspace path for a room.
    Guards against path traversal — room_name is already slug-validated in schema."""
    path = os.path.abspath(os.path.join(WORKSPACE_ROOT, room_name))
    if not path.startswith(WORKSPACE_ROOT + os.sep) and path != WORKSPACE_ROOT:
        raise ValueError(f"Invalid room name: path escapes workspace root")
    return path


@router.get("/", response_model=list[RoomOut])
async def list_rooms(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Room).where(Room.owner_id == current_user.id))
    return result.scalars().all()


@router.post("/", response_model=RoomOut, status_code=status.HTTP_201_CREATED)
async def create_room(
    payload: RoomCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    existing = await db.execute(select(Room).where(Room.name == payload.name))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Room name already taken")

    workspace_path = _workspace_path(payload.name)
    os.makedirs(workspace_path, exist_ok=True)

    room = Room(
        name=payload.name,
        display_name=payload.display_name,
        owner_id=current_user.id,
        workspace_path=workspace_path,
    )
    db.add(room)
    await db.commit()
    await db.refresh(room)
    return room


@router.get("/{room_id}", response_model=RoomOut)
async def get_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room or room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    return room


@router.delete("/{room_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_room(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room or room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")
    await db.delete(room)
    await db.commit()
