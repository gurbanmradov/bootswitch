from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class BootEntry:
    """Represents a single UEFI boot entry."""

    boot_id: str
    label: str
    active: bool = True
    details: str = ""


@dataclass(frozen=True)
class BootState:
    """Represents the parsed UEFI boot configuration of the host machine."""

    current: str | None = None
    next_boot: str | None = None
    order: list[str] = field(default_factory=list)
    entries: list[BootEntry] = field(default_factory=list)
