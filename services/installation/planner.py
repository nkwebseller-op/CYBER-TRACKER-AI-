"""InstallationPlanner: turns an APPROVED ToolRecord + EnvironmentCheck
into a structural InstallationPlan the UI can render before any command
runs. Building a plan never touches the OS — see EnvironmentInspector for
the (also read-only) detection step this consumes."""

from services.installation.errors import (
    PackageManagerUnavailableError,
    UnsupportedPlatformForToolError,
)
from services.installation.models import (
    DependencyCheck,
    DependencyStatus,
    EnvironmentCheck,
    InstallationPlan,
    InstallationStep,
    PackageManager,
)
from services.policy.engine import RiskTier
from services.terminal.command_templates import INSTALL_ACTION_TYPE
from services.tools.models import ToolRecord

# Preference order when a tool doesn't pin a specific package manager via
# `installation_method` — prefers a native OS package manager over pip.
_PLATFORM_PREFERENCE: dict[str, tuple[PackageManager, ...]] = {
    "WINDOWS": (PackageManager.WINGET, PackageManager.PIP),
    "LINUX": (PackageManager.APT, PackageManager.DNF, PackageManager.PACMAN, PackageManager.PIP),
    "MACOS": (PackageManager.BREW, PackageManager.PIP),
    "ANDROID_TERMUX": (PackageManager.TERMUX_PKG, PackageManager.PIP),
}


class InstallationPlanner:
    def build_plan(
        self, tool: ToolRecord, environment: EnvironmentCheck, *, target_platform: str
    ) -> InstallationPlan:
        if target_platform not in tool.supported_platforms:
            raise UnsupportedPlatformForToolError(
                f"Tool '{tool.name}' does not declare support for platform '{target_platform}'."
            )

        package_manager = self._choose_package_manager(target_platform, environment)

        dependency_checks = [
            DependencyCheck(
                name=dep,
                status=DependencyStatus.UNKNOWN,
                note="Declared by the tool; not independently resolved before installation.",
            )
            for dep in tool.dependencies
        ]

        steps = [
            InstallationStep(
                description=f"Install '{tool.name}' via {package_manager.value}.",
                package_manager=package_manager,
                action_type=INSTALL_ACTION_TYPE,
                package_name=tool.name,
                version=tool.version,
            )
        ]
        verification_steps = [
            f"Run a read-only {package_manager.value} presence/version check for '{tool.name}'."
        ]
        if tool.entrypoint:
            verification_steps.append(f"Run '{tool.entrypoint} --version' and confirm it responds.")

        approval_required = tool.risk_level in (RiskTier.MEDIUM, RiskTier.HIGH, RiskTier.CRITICAL)

        estimated_changes = [
            f"Installs package '{tool.name}'"
            + (f" version {tool.version}" if tool.version else " (latest available)")
            + f" via {package_manager.value}.",
        ]
        if tool.required_permissions:
            estimated_changes.append(
                f"Tool declares required permissions: {list(tool.required_permissions)}."
            )

        return InstallationPlan(
            tool_id=tool.id,
            tool_name=tool.name,
            platform=target_platform,
            architecture=environment.architecture,
            source=tool.provenance,
            version=tool.version,
            package_manager=package_manager,
            dependencies=dependency_checks,
            prerequisites=[f"{package_manager.value} must be available on the target host."],
            required_permissions=list(tool.required_permissions),
            installation_steps=steps,
            verification_steps=verification_steps,
            risk_level=tool.risk_level,
            approval_required=approval_required,
            estimated_changes=estimated_changes,
        )

    @staticmethod
    def _choose_package_manager(
        target_platform: str, environment: EnvironmentCheck
    ) -> PackageManager:
        preference = _PLATFORM_PREFERENCE.get(target_platform, (PackageManager.PIP,))
        for manager in preference:
            if manager in environment.available_package_managers:
                return manager
        raise PackageManagerUnavailableError(
            f"No supported package manager is available for platform '{target_platform}' "
            f"(checked {[m.value for m in preference]})."
        )
