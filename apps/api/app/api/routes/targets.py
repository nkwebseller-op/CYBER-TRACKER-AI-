"""Targets (authorized scope) CRUD — the foundation of the authorization
model. Nothing can be executed against a target that doesn't exist here
with valid, active authorization evidence."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import ScopeType, Target
from app.db.session import get_db

router = APIRouter(prefix="/targets", tags=["targets"])


class TargetCreate(BaseModel):
    name: str
    scope_type: ScopeType
    scope_value: str
    authorization_evidence: str
    authorized_by: str
    expires_at: datetime | None = None


class TargetOut(BaseModel):
    id: uuid.UUID
    name: str
    scope_type: ScopeType
    scope_value: str
    authorized_by: str
    authorized_at: datetime
    expires_at: datetime | None
    is_active: bool

    model_config = {"from_attributes": True}


@router.get("", response_model=list[TargetOut])
async def list_targets(db: AsyncSession = Depends(get_db)) -> list[Target]:
    result = await db.execute(select(Target).order_by(Target.created_at.desc()))
    return list(result.scalars().all())


@router.post("", response_model=TargetOut, status_code=201)
async def create_target(payload: TargetCreate, db: AsyncSession = Depends(get_db)) -> Target:
    target = Target(
        name=payload.name,
        scope_type=payload.scope_type,
        scope_value=payload.scope_value,
        authorization_evidence=payload.authorization_evidence,
        authorized_by=payload.authorized_by,
        authorized_at=datetime.utcnow(),
        expires_at=payload.expires_at,
    )
    db.add(target)
    await db.commit()
    await db.refresh(target)
    return target


@router.get("/{target_id}", response_model=TargetOut)
async def get_target(target_id: uuid.UUID, db: AsyncSession = Depends(get_db)) -> Target:
    target = await db.get(Target, target_id)
    if target is None:
        raise HTTPException(status_code=404, detail="Target not found")
    return target
