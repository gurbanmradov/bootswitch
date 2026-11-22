from __future__ import annotations

import os
import platform
import shutil
import subprocess
from abc import ABC, abstractmethod
from pathlib import Path

from bootswitch.models import BootState
from bootswitch.parser import parse_bcdedit_firmware, parse_efibootmgr

_BOOTNEXT_EFIVAR = Path("/sys/firmware/efi/efivars/BootNext-8be4df61-93ca-11d2-aa0d-00e098032b8c")


class BootBackendError(RuntimeError):
    """Raised when an underlying UEFI or OS command fails."""


class BootBackend(ABC):
    """Abstract interface for OS-specific UEFI boot operations."""

    @abstractmethod
    def get_state(self) -> BootState:
        """Read current UEFI boot entries and order."""

    @abstractmethod
    def set_next_boot(self, boot_id: str, *, dry_run: bool = False, gui_auth: bool = False) -> list[str]:
        """Set one-time next boot target. Returns the executed command."""

    @abstractmethod
    def clear_next_boot(self, *, dry_run: bool = False, gui_auth: bool = False) -> list[str]:
        """Clear any pending one-time next boot target. Returns the executed command."""

    @abstractmethod
    def reboot(self, *, dry_run: bool = False) -> list[str]:
        """Reboot the machine immediately. Returns the executed command."""


def _run_command(cmd: list[str]) -> str:
    try:
        completed = subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        return completed.stdout
    except FileNotFoundError as exc:
        raise BootBackendError(f"Required system tool not found: {cmd[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or exc.stdout or "").strip()
        raise BootBackendError(f"Command failed ({' '.join(cmd)}): {stderr}") from exc


class LinuxBackend(BootBackend):
    """UEFI backend for Linux using `efibootmgr`, `efivarfs`, and `systemctl`."""

    def _elevate(self, cmd: list[str], *, gui_auth: bool = False) -> list[str]:
        if hasattr(os, "geteuid") and os.geteuid() == 0:
            return cmd
        if gui_auth and shutil.which("pkexec"):
            return ["pkexec", *cmd]
        if shutil.which("sudo"):
            return ["sudo", *cmd]
        return cmd

    def get_state(self) -> BootState:
        output = _run_command(["efibootmgr"])
        return parse_efibootmgr(output)

    def set_next_boot(self, boot_id: str, *, dry_run: bool = False, gui_auth: bool = False) -> list[str]:
        cmd = self._elevate(["efibootmgr", "--bootnext", boot_id], gui_auth=gui_auth)
        if not dry_run:
            _run_command(cmd)
        return cmd

    def clear_next_boot(self, *, dry_run: bool = False, gui_auth: bool = False) -> list[str]:
        cmd = self._elevate(["efibootmgr", "--delete-bootnext"], gui_auth=gui_auth)
        if dry_run:
            return cmd

        try:
            _run_command(cmd)
            return cmd
        except BootBackendError:
            # Fallback for efibootmgr versions affected by the Boot0001 upstream bug
            if not _BOOTNEXT_EFIVAR.exists():
                return cmd
            fallback_cmd = self._elevate(
                ["sh", "-c", 'chattr -i "$1" && rm -f "$1"', "_", str(_BOOTNEXT_EFIVAR)],
                gui_auth=gui_auth,
            )
            _run_command(fallback_cmd)
            return fallback_cmd

    def reboot(self, *, dry_run: bool = False) -> list[str]:
        cmd = ["systemctl", "reboot"]
        if not dry_run:
            _run_command(cmd)
        return cmd


class WindowsBackend(BootBackend):
    """UEFI backend for Windows using `bcdedit` and `shutdown`."""

    def get_state(self) -> BootState:
        output = _run_command(["bcdedit", "/enum", "firmware"])
        return parse_bcdedit_firmware(output)

    def set_next_boot(self, boot_id: str, *, dry_run: bool = False, gui_auth: bool = False) -> list[str]:
        cmd = ["bcdedit", "/set", "{fwbootmgr}", "bootsequence", boot_id]
        if not dry_run:
            _run_command(cmd)
        return cmd

    def clear_next_boot(self, *, dry_run: bool = False, gui_auth: bool = False) -> list[str]:
        cmd = ["bcdedit", "/deletevalue", "{fwbootmgr}", "bootsequence"]
        if not dry_run:
            _run_command(cmd)
        return cmd

    def reboot(self, *, dry_run: bool = False) -> list[str]:
        cmd = ["shutdown", "/r", "/t", "0"]
        if not dry_run:
            _run_command(cmd)
        return cmd


def get_backend() -> BootBackend:
    """Detect the current operating system and return the matching backend."""
    system = platform.system().lower()
    if system == "linux":
        return LinuxBackend()
    if system == "windows":
        return WindowsBackend()
    raise BootBackendError(f"Unsupported operating system: {platform.system()}")
