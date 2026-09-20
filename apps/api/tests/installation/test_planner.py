import pytest
from services.installation.errors import (
    PackageManagerUnavailableError,
    UnsupportedPlatformForToolError,
)
from services.installation.models import EnvironmentCheck, PackageManager
from services.installation.planner import InstallationPlanner

from tests.installation.helpers import approved_tool


def _env(**overrides) -> EnvironmentCheck:
    defaults = dict(
        platform="LINUX",
        architecture="x86_64",
        shell="/bin/bash",
        available_package_managers=(PackageManager.APT,),
    )
    defaults.update(overrides)
    return EnvironmentCheck(**defaults)


def test_build_plan_chooses_available_package_manager():
    planner = InstallationPlanner()
    plan = planner.build_plan(approved_tool(), _env(), target_platform="LINUX")
    assert plan.package_manager == PackageManager.APT
    assert plan.installation_steps[0].package_name == "dig"


def test_build_plan_prefers_native_manager_over_pip():
    planner = InstallationPlanner()
    env = _env(available_package_managers=(PackageManager.APT, PackageManager.PIP))
    plan = planner.build_plan(approved_tool(), env, target_platform="LINUX")
    assert plan.package_manager == PackageManager.APT


def test_build_plan_raises_for_unsupported_platform():
    planner = InstallationPlanner()
    tool = approved_tool(supported_platforms=("WINDOWS",))
    with pytest.raises(UnsupportedPlatformForToolError):
        planner.build_plan(tool, _env(), target_platform="LINUX")


def test_build_plan_raises_when_no_package_manager_available():
    planner = InstallationPlanner()
    with pytest.raises(PackageManagerUnavailableError):
        empty_env = _env(available_package_managers=())
        planner.build_plan(approved_tool(), empty_env, target_platform="LINUX")


def test_build_plan_marks_dependencies_unknown_not_fabricated():
    planner = InstallationPlanner()
    tool = approved_tool(dependencies=("libpcap",))
    plan = planner.build_plan(tool, _env(), target_platform="LINUX")
    assert plan.dependencies[0].name == "libpcap"
    assert plan.dependencies[0].status.value == "unknown"


def test_build_plan_requires_approval_for_medium_risk():
    from services.policy.engine import RiskTier

    planner = InstallationPlanner()
    tool = approved_tool(risk_level=RiskTier.MEDIUM)
    plan = planner.build_plan(tool, _env(), target_platform="LINUX")
    assert plan.approval_required is True


def test_build_plan_does_not_require_approval_for_low_risk():
    from services.policy.engine import RiskTier

    planner = InstallationPlanner()
    tool = approved_tool(risk_level=RiskTier.LOW)
    plan = planner.build_plan(tool, _env(), target_platform="LINUX")
    assert plan.approval_required is False


def test_build_plan_includes_estimated_changes():
    planner = InstallationPlanner()
    plan = planner.build_plan(approved_tool(), _env(), target_platform="LINUX")
    assert plan.estimated_changes
    assert "dig" in plan.estimated_changes[0]
