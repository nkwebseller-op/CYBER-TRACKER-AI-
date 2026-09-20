"""Dependency wiring for Tool Discovery & the Trusted Tool Registry."""

from functools import lru_cache

from fastapi import Depends
from services.tools.discovery import ToolDiscoveryService
from services.tools.policy import ToolPolicyGate
from services.tools.registry import ToolRegistry
from services.tools.research import CuratedToolResearchProvider
from services.tools.verification import VerificationPipeline
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.db.tool_repository import SqlAlchemyToolRegistry


def get_tool_registry(db: AsyncSession = Depends(get_db)) -> ToolRegistry:
    return SqlAlchemyToolRegistry(db)


@lru_cache
def get_discovery_service() -> ToolDiscoveryService:
    return ToolDiscoveryService(CuratedToolResearchProvider())


@lru_cache
def get_verification_pipeline() -> VerificationPipeline:
    return VerificationPipeline()


@lru_cache
def get_policy_gate() -> ToolPolicyGate:
    return ToolPolicyGate()
