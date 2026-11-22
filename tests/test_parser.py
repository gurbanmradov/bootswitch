import unittest

from bootswitch.parser import (
    find_target_entry,
    parse_bcdedit_firmware,
    parse_efibootmgr,
)

SAMPLE_EFIBOOTMGR = """\
BootCurrent: 0000
Timeout: 0 seconds
BootOrder: 0004,0000,0002,2001
Boot0000* Fedora\tHD(1,GPT,03cd5579)/\\EFI\\fedora\\shim.efi
Boot0002* Fedora\tHD(1,GPT,03cd5579)/\\EFI\\fedora\\shimx64.efi
Boot0004* Windows Boot Manager\tHD(1,GPT,03cd5579)/\\EFI\\Microsoft\\Boot\\bootmgfw.efi
Boot0005  Ubuntu\tHD(1,GPT,03cd5579)/\\EFI\\ubuntu\\shimx64.efi
Boot2001* EFI USB Device\tRC
"""

SAMPLE_BCDEDIT = """\
Firmware Boot Manager
---------------------
identifier              {fwbootmgr}
displayorder            {bootmgr}
                        {12345678-1234-1234-1234-123456789abc}

Windows Boot Manager
--------------------
identifier              {bootmgr}
device                  partition=\\Device\\HarddiskVolume1
description             Windows Boot Manager

Firmware Application (101fffff)
-------------------------------
identifier              {12345678-1234-1234-1234-123456789abc}
device                  partition=\\Device\\HarddiskVolume1
path                    \\EFI\\fedora\\shimx64.efi
description             Fedora
"""


class TestParsers(unittest.TestCase):
    def test_parse_efibootmgr_metadata_and_entries(self):
        state = parse_efibootmgr(SAMPLE_EFIBOOTMGR)
        self.assertEqual(state.current, "0000")
        self.assertEqual(state.order, ["0004", "0000", "0002", "2001"])
        self.assertEqual(len(state.entries), 5)
        self.assertTrue(state.entries[0].active)
        self.assertFalse(state.entries[3].active)

    def test_find_target_prefers_boot_order_on_duplicates(self):
        state = parse_efibootmgr(SAMPLE_EFIBOOTMGR)
        entry = find_target_entry(state, "fedora")
        self.assertEqual(entry.boot_id, "0000")

    def test_find_target_matches_substring_case_insensitive(self):
        state = parse_efibootmgr(SAMPLE_EFIBOOTMGR)
        entry = find_target_entry(state, "WINDOWS")
        self.assertEqual(entry.boot_id, "0004")

    def test_find_target_matches_exact_boot_id(self):
        state = parse_efibootmgr(SAMPLE_EFIBOOTMGR)
        entry = find_target_entry(state, "0002")
        self.assertEqual(entry.label, "Fedora")
        self.assertEqual(entry.boot_id, "0002")

    def test_find_target_raises_on_missing_entry(self):
        state = parse_efibootmgr(SAMPLE_EFIBOOTMGR)
        with self.assertRaises(LookupError):
            find_target_entry(state, "archlinux")

    def test_parse_bcdedit_firmware_skips_fwbootmgr(self):
        state = parse_bcdedit_firmware(SAMPLE_BCDEDIT)
        self.assertEqual(len(state.entries), 2)
        fedora = find_target_entry(state, "fedora")
        self.assertEqual(fedora.boot_id, "{12345678-1234-1234-1234-123456789abc}")


if __name__ == "__main__":
    unittest.main()


class TestAutoDetect(unittest.TestCase):
    def test_auto_detect_from_linux_finds_windows(self):
        from bootswitch.parser import find_other_os_entry

        state = parse_efibootmgr(SAMPLE_EFIBOOTMGR)
        target = find_other_os_entry(state, "Linux")
        self.assertEqual(target.boot_id, "0004")

    def test_auto_detect_from_windows_finds_linux(self):
        from bootswitch.parser import find_other_os_entry

        state = parse_bcdedit_firmware(SAMPLE_BCDEDIT)
        target = find_other_os_entry(state, "Windows")
        self.assertEqual(target.label, "Fedora")
