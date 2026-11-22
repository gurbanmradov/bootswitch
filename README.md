# bootswitch

[![CI](https://github.com/gurbanmradov/bootswitch/actions/workflows/ci.yml/badge.svg)](https://github.com/gurbanmradov/bootswitch/actions/workflows/ci.yml)

A zero-dependency, cross-platform Python CLI tool to switch between **Linux** and **Windows** dual-boot systems in a single command or keyboard shortcut using UEFI `BootNext`.

## Why?

Switching between Fedora and Windows on a dual-boot machine normally requires rebooting, waiting for the firmware/GRUB menu, and manually selecting the target OS. `bootswitch` automates this safely by dynamically inspecting UEFI boot entries, resolving duplicate labels using `BootOrder` priority, and configuring a one-time `BootNext` target so your default boot order stays untouched.

## Features

- **Zero external dependencies:** Built purely on the Python standard library.
- **Dynamic UEFI parsing:** Automatically detects OS entries via `efibootmgr` (Linux) and `bcdedit /enum firmware` (Windows) — no hardcoded boot IDs.
- **Smart conflict resolution:** Handles duplicate firmware entries (e.g., multiple `Fedora` entries) by prioritizing active entries and `BootOrder` rank.
- **Safety first:** Supports `--dry-run` preview mode, interactive confirmation, and `clear` to cancel a pending `BootNext`.
- **Desktop shortcut ready:** Supports `--gui-auth` (`pkexec`) on Linux for seamless GNOME/KDE keyboard shortcuts.

## Installation

```bash
git clone [https://github.com/gurbanmradov/bootswitch.git](https://github.com/gurbanmradov/bootswitch.git)
cd bootswitch
pip install .
```

Or run directly without installing:

```bash
PYTHONPATH=src python3 -m bootswitch list
```

## Usage

### List UEFI boot entries
```bash
bootswitch list
```

```text
Current : 0000
Order   : 0004, 0000, 0002, 2001, 2002, 2003

ID     Status    Label
------------------------------------------
0000   active    Fedora (current)
0002   active    Fedora
0004   active    Windows Boot Manager
```

### Preview a switch safely (`--dry-run`)
```bash
bootswitch to windows --dry-run
```

```text
Matched target: Windows Boot Manager [ID: 0004]
[dry-run] Would run: sudo efibootmgr --bootnext 0004
[dry-run] Would run: systemctl reboot
```

### Switch OS and reboot
```bash
bootswitch to windows
bootswitch to fedora --no-reboot   # Set BootNext without rebooting yet
bootswitch clear                   # Cancel a pending BootNext
```

## Keyboard Shortcut Setup (GNOME / Fedora)

1. Open **Settings -> Keyboard -> View and Customize Shortcuts -> Custom Shortcuts**.
2. Click **+** and configure:
   - **Name:** `Switch to Windows`
   - **Command:** `bootswitch to windows --yes --gui-auth`
   - **Shortcut:** `Super + Shift + W` (or any combination you prefer)

When triggered, PolicyKit (`pkexec`) prompts for authentication (preventing accidental reboots), sets `BootNext`, and reboots straight into Windows.

## Running Tests

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
```

## License

MIT
