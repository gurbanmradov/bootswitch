from __future__ import annotations

import platform
import re
import shutil
import sys
from pathlib import Path

from bootswitch.models import BootEntry


def _slugify(text: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or "os"


def create_linux_desktop_entry(
    entry: BootEntry,
    target_query: str,
    *,
    applications_dir: Path | None = None,
) -> Path:
    """Create a clickable .desktop launcher for Linux desktop environments."""
    app_dir = applications_dir or (Path.home() / ".local" / "share" / "applications")
    app_dir.mkdir(parents=True, exist_ok=True)

    exe = shutil.which("bootswitch") or f"{sys.executable} -m bootswitch"
    slug = _slugify(entry.label)
    desktop_file = app_dir / f"bootswitch-{slug}.desktop"

    content = (
        "[Desktop Entry]\n"
        f"Name=Switch to {entry.label}\n"
        f"Comment=Reboot directly into {entry.label} via UEFI BootNext\n"
        f"Exec={exe} to {target_query} --yes --gui-auth\n"
        "Icon=system-reboot\n"
        "Terminal=false\n"
        "Type=Application\n"
        "Categories=System;Utility;\n"
    )
    desktop_file.write_text(content, encoding="utf-8")
    return desktop_file


def create_windows_bat_shortcut(
    entry: BootEntry,
    *,
    desktop_dir: Path | None = None,
) -> Path:
    """Create a clickable .bat launcher on the Windows Desktop with UAC elevation."""
    target_dir = desktop_dir or (Path.home() / "Desktop")
    target_dir.mkdir(parents=True, exist_ok=True)

    safe_name = re.sub(r'[<>:"/\\|?*]', "", entry.label).strip() or "OS"
    bat_file = target_dir / f"Switch to {safe_name}.bat"

    content = (
        "@echo off\n"
        f'powershell -NoProfile -Command "Start-Process cmd -Verb RunAs '
        f"-ArgumentList '/c bcdedit /set {{fwbootmgr}} bootsequence {entry.boot_id} && shutdown /r /t 0'\"\n"
    )
    bat_file.write_text(content, encoding="utf-8")
    return bat_file


def install_shortcut(entry: BootEntry, target_query: str) -> Path:
    """Create a desktop shortcut appropriate for the current operating system."""
    system = platform.system().lower()
    if system == "linux":
        return create_linux_desktop_entry(entry, target_query)
    if system == "windows":
        return create_windows_bat_shortcut(entry)
    raise RuntimeError(f"Shortcuts are not supported on {platform.system()}")
