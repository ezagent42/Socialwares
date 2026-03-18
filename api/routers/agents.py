import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agent_bridge import AgentRequest, invoke
from database import get_db
from deps import get_current_user
from models import AgentTask, Room, TaskStatus, User
from schemas import AgentInvokeRequest, AgentInvokeResponse, AgentTaskOut

router = APIRouter()


@router.post("/invoke", response_model=AgentInvokeResponse)
async def invoke_agent(
    payload: AgentInvokeRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify room ownership
    result = await db.execute(select(Room).where(Room.id == payload.room_id))
    room = result.scalar_one_or_none()
    if not room or room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    # Load or create AgentTask
    task: AgentTask | None = None
    if payload.task_id:
        t_result = await db.execute(
            select(AgentTask).where(
                AgentTask.id == payload.task_id,
                AgentTask.room_id == room.id,
            )
        )
        task = t_result.scalar_one_or_none()

    if not task:
        task = AgentTask(
            id=str(uuid.uuid4()),
            room_id=room.id,
            created_by=current_user.id,
            title=payload.prompt[:128],  # use prompt start as title
            status=TaskStatus.open,
            assigned_agent="claude-opus-4-6",
        )
        db.add(task)
        await db.flush()

    # Call agent
    request = AgentRequest(
        room_name=room.name,
        workspace_path=room.workspace_path,
        prompt=payload.prompt,
        task_id=task.id,
        task_status=task.status.value,
        history=payload.history or [],
    )
    agent_response = await invoke(request)

    # Persist result and advance status
    task.result = agent_response.content
    try:
        task.status = TaskStatus(agent_response.task_status)
    except ValueError:
        pass  # unknown status — keep current

    await db.commit()
    await db.refresh(task)

    return AgentInvokeResponse(
        content=agent_response.content,
        task_id=task.id,
        task_status=task.status.value,
        agent_id=agent_response.agent_id,
    )


@router.get("/tasks", response_model=list[AgentTaskOut])
async def list_tasks(
    room_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    # Verify room ownership
    result = await db.execute(select(Room).where(Room.id == room_id))
    room = result.scalar_one_or_none()
    if not room or room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Room not found")

    tasks_result = await db.execute(
        select(AgentTask).where(AgentTask.room_id == room_id).order_by(AgentTask.created_at.desc())
    )
    return tasks_result.scalars().all()


@router.get("/tasks/{task_id}", response_model=AgentTaskOut)
async def get_task(
    task_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(AgentTask).where(AgentTask.id == task_id))
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    # Verify ownership via room
    room_result = await db.execute(select(Room).where(Room.id == task.room_id))
    room = room_result.scalar_one_or_none()
    if not room or room.owner_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")

    return task
