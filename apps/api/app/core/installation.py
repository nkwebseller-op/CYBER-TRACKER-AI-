"""Dependency wiring for Tool Installation & Environment Preparation."""

from fastapi import Depends
from services.installation.config import InstallationServiceConfig
from services.installation.registry import InstallationRegistry
from services.installation.service import ToolInstallationService
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.tools import get_tool_registry
from app.db.installation_repository import SqlAlchemyInstallationRegistry
from app.db.session import get_db
from app.db.tool_repository import SqlAlchemyToolRegistry


def get_installation_registry(db: AsyncSession = Depends(get_db)) -> InstallationRegistry:
    return SqlAlchemyInstallationRegistry(db)


def get_installation_service(
    tools: SqlAlchemyToolRegistry = Depends(get_tool_registry),
    installations: InstallationRegistry = Depends(get_installation_registry),
) -> ToolInstallationService:
    return ToolInstallationService(
        tools=tools, installations=installations, config=InstallationServiceConfig()
    )
