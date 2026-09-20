"""Tool Installation Service configuration — same plain-dataclass pattern
as services/terminal/config.py and services/tools/discovery.py."""

from dataclasses import dataclass


@dataclass(frozen=True)
class InstallationServiceConfig:
    max_install_attempts: int = 2
    install_timeout_seconds: int = 300
    verify_timeout_seconds: int = 30
