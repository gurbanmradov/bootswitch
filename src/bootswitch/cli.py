from __future__ import annotations

import argparse
import platform
import sys
from typing import Sequence

from bootswitch import __version__
from bootswitch.backends import BootBackend, BootBackendError, get_backend
from bootswitch.parser import find_other_os_entry, find_target_entry
from bootswitch.shortcuts import install_shortcut


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bootswitch",
        description="Switch between Linux and Windows dual-boot systems via UEFI BootNext.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("list", help="List detected UEFI boot entries.")

    to_parser = subparsers.add_parser("to", help="Set next boot target and optionally reboot.")
    to_parser.add_argument(
        "target",
        help="Target OS label or UEFI boot ID (e.g., windows, fedora, 0004).",
    )
    to_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview commands without modifying UEFI or rebooting.",
    )
    to_parser.add_argument(
        "--no-reboot",
        action="store_true",
        help="Configure BootNext without rebooting immediately.",
    )
    to_parser.add_argument(
        "-y",
        "--yes",
        action="store_true",
        help="Skip interactive confirmation prompt.",
    )
    to_parser.add_argument(
        "--gui-auth",
        action="store_true",
        help="Use pkexec for graphical authentication on Linux (ideal for desktop shortcuts).",
    )

    clear_parser = subparsers.add_parser("clear", help="Clear any pending one-time BootNext entry.")
    clear_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview command without modifying UEFI.",
    )
    clear_parser.add_argument(
        "--gui-auth",
        action="store_true",
        help="Use pkexec for graphical authentication on Linux.",
    )

    shortcut_parser = subparsers.add_parser(
        "shortcut",
        help="Create a one-click desktop launcher for a specific target OS.",
    )
    shortcut_parser.add_argument(
        "target",
        help="Target OS label or UEFI boot ID (e.g., windows, ubuntu, fedora).",
    )

    subparsers.add_parser(
        "setup",
        help="Auto-detect the other OS and create a one-click desktop shortcut.",
    )

    return parser


def cmd_list(backend: BootBackend) -> int:
    state = backend.get_state()
    if state.current:
        print(f"Current : {state.current}")
    if state.next_boot:
        print(f"BootNext: {state.next_boot}")
    if state.order:
        print(f"Order   : {', '.join(state.order)}")

    print("\nID     Status    Label")
    print("-" * 42)
    for entry in state.entries:
        status = "active" if entry.active else "inactive"
        marker = " (current)" if state.current and entry.boot_id == state.current else ""
        print(f"{entry.boot_id:<6} {status:<9} {entry.label}{marker}")
    return 0


def cmd_to(backend: BootBackend, args: argparse.Namespace) -> int:
    state = backend.get_state()
    entry = find_target_entry(state, args.target)

    print(f"Matched target: {entry.label} [ID: {entry.boot_id}]")

    if not args.dry_run and not args.yes:
        action = "set BootNext" if args.no_reboot else "set BootNext and reboot"
        reply = input(f"Proceed to {action} into '{entry.label}'? [y/N]: ").strip().lower()
        if reply not in {"y", "yes"}:
            print("Aborted.")
            return 0

    boot_cmd = backend.set_next_boot(
        entry.boot_id,
        dry_run=args.dry_run,
        gui_auth=args.gui_auth,
    )
    if args.dry_run:
        print(f"[dry-run] Would run: {' '.join(boot_cmd)}")
    else:
        print(f"BootNext configured to {entry.boot_id} ({entry.label}).")

    if not args.no_reboot:
        reboot_cmd = backend.reboot(dry_run=args.dry_run)
        if args.dry_run:
            print(f"[dry-run] Would run: {' '.join(reboot_cmd)}")
        else:
            print("Rebooting...")

    return 0


def cmd_clear(backend: BootBackend, args: argparse.Namespace) -> int:
    cmd = backend.clear_next_boot(dry_run=args.dry_run, gui_auth=args.gui_auth)
    if args.dry_run:
        print(f"[dry-run] Would run: {' '.join(cmd)}")
    else:
        print("Cleared pending BootNext entry.")
    return 0


def cmd_shortcut(backend: BootBackend, args: argparse.Namespace) -> int:
    state = backend.get_state()
    entry = find_target_entry(state, args.target)
    created_path = install_shortcut(entry, entry.boot_id)
    print(f"Created shortcut for '{entry.label}' at: {created_path}")
    return 0


def cmd_setup(backend: BootBackend) -> int:
    state = backend.get_state()
    entry = find_other_os_entry(state, platform.system())
    created_path = install_shortcut(entry, entry.boot_id)
    print(f"Auto-detected secondary OS: {entry.label} [ID: {entry.boot_id}]")
    print(f"Created one-click shortcut at: {created_path}")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        backend = get_backend()
        if args.command == "list":
            return cmd_list(backend)
        if args.command == "to":
            return cmd_to(backend, args)
        if args.command == "clear":
            return cmd_clear(backend, args)
        if args.command == "shortcut":
            return cmd_shortcut(backend, args)
        if args.command == "setup":
            return cmd_setup(backend)
    except (BootBackendError, LookupError, ValueError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
