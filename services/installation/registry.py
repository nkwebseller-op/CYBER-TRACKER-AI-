"""InstallationRequest persistence abstraction — same split as
services/tools/registry.py: a storage-independent Protocol plus an
in-memory reference implementation used by tests and available to the API
as a dependency override; apps/api backs this with the database in
production (see apps/api/app/db/installation_repository.py)."""

from typing import Protocol
from uuid import UUID

from services.installation.errors import InstallationNotFoundError
from services.installation.models import InstallationRequest, InstallationState


class InstallationRegistry(Protocol):
    async def create(self, request: InstallationRequest) -> InstallationRequest: ...
    async def get(self, request_id: UUID) -> InstallationRequest: ...
    async def save(self, request: InstallationRequest) -> InstallationRequest: ...
    async def list_for_tool(self, tool_id: UUID) -> list[InstallationRequest]: ...
    async def list_installed(self) -> list[InstallationRequest]: ...
    async def list_all(self) -> list[InstallationRequest]: ...


class InMemoryInstallationRegistry:
    def __init__(self) -> None:
        self._requests: dict[UUID, InstallationRequest] = {}

    async def create(self, request: InstallationRequest) -> InstallationRequest:
        self._requests[request.id] = request
        return request

    async def get(self, request_id: UUID) -> InstallationRequest:
        request = self._requests.get(request_id)
        if request is None:
            raise InstallationNotFoundError(f"Installation request {request_id} was not found.")
        return request

    async def save(self, request: InstallationRequest) -> InstallationRequest:
        request.touch()
        self._requests[request.id] = request
        return request

    async def list_for_tool(self, tool_id: UUID) -> list[InstallationRequest]:
        return [r for r in self._requests.values() if r.tool_id == tool_id]

    async def list_installed(self) -> list[InstallationRequest]:
        return [r for r in self._requests.values() if r.state == InstallationState.INSTALLED]

    async def list_all(self) -> list[InstallationRequest]:
        return list(self._requests.values())
