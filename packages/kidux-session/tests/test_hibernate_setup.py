"""kidux-hibernate-setup: what it decides and writes (D119, power.md)."""

import importlib.machinery
import importlib.util
from pathlib import Path

import pytest

PROGRAM = Path(__file__).resolve().parents[1] / "bin" / "kidux-hibernate-setup"
loader = importlib.machinery.SourceFileLoader("hibernate_setup", str(PROGRAM))
spec = importlib.util.spec_from_loader("hibernate_setup", loader)
setup = importlib.util.module_from_spec(spec)
loader.exec_module(setup)

GIB = setup.GIB
SWAPS = ("Filename\tType\tSize\tUsed\tPriority\n"
         "/swapfile                               file\t\t4194300\t\t0\t\t-2\n"
         "/dev/zram0                              partition\t8000000\t0\t100\n")


def test_the_memory_from_meminfo():
    assert setup.memory_bytes("MemTotal:       16314564 kB\nMemFree: 1 kB\n") == 16314564 * 1024
    assert setup.memory_bytes("") == 0


@pytest.mark.parametrize("memory, size", [
    (16314564 * 1024, 16 * GIB), (8 * GIB, 8 * GIB), (8 * GIB + 1, 9 * GIB), (1, GIB),
])
def test_the_swap_file_is_the_memory_in_whole_gib(memory, size):
    assert setup.swap_size(memory) == size


def test_swaps_leave_zram_out():
    assert setup.swaps(SWAPS) == [("/swapfile", "file", 4194300 * 1024)]


@pytest.mark.parametrize("conf, configured", [
    ("RESUME=none\n", False), ("RESUME=UUID=abc\nRESUME_OFFSET=34816\n", True), ("", False),
    ("# nothing\n", False),
])
def test_debian_s_resume_none_is_not_a_resume_device(conf, configured):
    assert setup.resume_set(conf) is configured


def test_the_swap_file_goes_on_root_when_it_fits_counting_the_old_one():
    free = {"/swapfile": 13 * GIB, "/home/.kidux-swapfile": 300 * GIB}

    assert setup.choose_place(8 * GIB, free, {}) == "/swapfile"
    # 2 GiB free and an old 4 GiB file make room for 2 + 4 - 4 spare = 2 GiB.
    assert setup.choose_place(8 * GIB, {"/swapfile": 2 * GIB}, {"/swapfile": 4 * GIB}) is None


def test_otherwise_on_home_and_otherwise_nowhere():
    free = {"/swapfile": 5 * GIB, "/home/.kidux-swapfile": 300 * GIB}

    assert setup.choose_place(16 * GIB, free, {}) == "/home/.kidux-swapfile"
    assert setup.choose_place(16 * GIB, {"/swapfile": 5 * GIB}, {}) is None


def test_the_first_extent_from_filefrag():
    output = ("Filesystem type is: ef53\n"
              "File size of /swapfile is 4294967296 (1048576 blocks of 4096 bytes)\n"
              " ext:     logical_offset:        physical_offset: length:   expected: flags:\n"
              "   0:        0..   32767:    1081344..   1114111:  32768:            \n"
              "   1:    32768..   65535:    1114112..   1146879:  32768:            unwritten\n")

    assert setup.first_extent(output) == 1081344
    assert setup.first_extent("nothing") is None


def test_the_initramfs_and_grub_are_told_the_device_and_the_offset():
    assert setup.resume_conf("abc", 1081344).endswith(
        "RESUME=UUID=abc\nRESUME_OFFSET=1081344\n")
    assert setup.resume_conf("abc", None).endswith("RESUME=UUID=abc\n")
    assert setup.grub_conf("abc", 1081344).endswith(
        'GRUB_CMDLINE_LINUX_DEFAULT="$GRUB_CMDLINE_LINUX_DEFAULT '
        'resume=UUID=abc resume_offset=1081344"\n')


def test_fstab_holds_one_swap_file():
    fstab = ("UUID=1 / ext4 errors=remount-ro 0 1\n"
             "/swapfile none swap sw 0 0\n"
             "UUID=2 /home ext4 defaults 0 2\n")

    assert setup.fstab_with(fstab, "/home/.kidux-swapfile") == (
        "UUID=1 / ext4 errors=remount-ro 0 1\n"
        "UUID=2 /home ext4 defaults 0 2\n"
        "/home/.kidux-swapfile none swap defaults 0 0\n")
    assert setup.fstab_with(fstab, "/swapfile").count("/swapfile") == 1


def test_secure_boot_s_lockdown():
    assert setup.locked_down("none [integrity] confidentiality")
    assert not setup.locked_down("[none] integrity confidentiality")
