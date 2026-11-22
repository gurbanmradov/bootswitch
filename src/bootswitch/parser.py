from __future__ import annotations

import re

from bootswitch.models import BootEntry, BootState

_EFI_ENTRY_RE = re.compile(
    r"^Boot([0-9A-Fa-f]{4})(\*?)\s+([^\t\r\n]+)(?:\t(.*))?$"
)


def parse_efibootmgr(output: str) -> BootState:
    """Parse stdout from Linux `efibootmgr` into a structured BootState."""
    current: str | None = None
    next_boot: str | None = None
    order: list[str] = []
    entries: list[BootEntry] = []

    for raw_line in output.splitlines():
        line = raw_line.strip()
        if not line:
            continue

        if line.startswith("BootCurrent:"):
            current = line.split(":", 1)[1].strip()
        elif line.startswith("BootNext:"):
            next_boot = line.split(":", 1)[1].strip()
        elif line.startswith("BootOrder:"):
            raw_order = line.split(":", 1)[1].strip()
            order = [item.strip() for item in raw_order.split(",") if item.strip()]
        else:
            match = _EFI_ENTRY_RE.match(raw_line)
            if match:
                boot_id, star, label, details = match.groups()
                entries.append(
                    BootEntry(
                        boot_id=boot_id.upper(),
                        label=label.strip(),
                        active=star == "*",
                        details=(details or "").strip(),
                    )
                )

    return BootState(
        current=current,
        next_boot=next_boot,
        order=order,
        entries=entries,
    )


def parse_bcdedit_firmware(output: str) -> BootState:
    """Parse stdout from Windows `bcdedit /enum firmware` into a BootState."""
    entries: list[BootEntry] = []
    blocks = re.split(r"\r?\n\s*\r?\n", output)

    for block in blocks:
        id_match = re.search(r"^\s*identifier\s+(\{[^}]+\})", block, re.MULTILINE | re.IGNORECASE)
        desc_match = re.search(r"^\s*description\s+(.+)$", block, re.MULTILINE | re.IGNORECASE)
        if not id_match or not desc_match:
            continue

        boot_id = id_match.group(1).strip()
        label = desc_match.group(1).strip()
        if boot_id.lower() == "{fwbootmgr}":
            continue

        entries.append(BootEntry(boot_id=boot_id, label=label, active=True))

    return BootState(entries=entries)


def find_target_entry(state: BootState, query: str) -> BootEntry:
    """
    Find the best matching UEFI entry for a user query (e.g., 'windows', 'fedora', or '0004').

    Resolution priority:
    1. Exact boot_id match.
    2. Case-insensitive label match, prioritized by active status and BootOrder position.
    """
    normalized = query.strip().lower()
    if not normalized:
        raise ValueError("Target query cannot be empty.")

    for entry in state.entries:
        if entry.boot_id.lower() == normalized:
            return entry

    matches = [entry for entry in state.entries if normalized in entry.label.lower()]
    if not matches:
        available = ", ".join(f"{e.boot_id} ({e.label})" for e in state.entries)
        raise LookupError(f"No boot entry matched '{query}'. Available: {available}")

    order_rank = {boot_id.upper(): idx for idx, boot_id in enumerate(state.order)}

    def sort_key(entry: BootEntry) -> tuple[int, int, int]:
        exact_label = 0 if entry.label.lower() == normalized else 1
        inactive_penalty = 0 if entry.active else 1
        rank = order_rank.get(entry.boot_id.upper(), len(order_rank) + 1)
        return (inactive_penalty, exact_label, rank)

    matches.sort(key=sort_key)
    return matches[0]
