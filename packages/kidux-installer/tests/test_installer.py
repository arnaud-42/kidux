"""Kidux's installer: Calamares's settings, the look, and the live system's scripts.

Calamares reads YAML it does not check much: a key it does not know is
ignored, a module it cannot find stops the installer. These tests hold the
settings to what Calamares 3.3, trixie's, has, and run the scripts that
start it with stand-ins for what the live system gives them.
"""

import subprocess
import tomllib
from pathlib import Path

import pytest
import yaml

PACKAGE = Path(__file__).resolve().parents[1]
CALAMARES = PACKAGE / "calamares"
#: The modules Calamares 3.3.14, trixie's, ships in /usr/lib/calamares/modules.
MODULES = {
    "bootloader", "contextualprocess", "displaymanager", "dracut", "dracutlukscfg",
    "dummycpp", "dummyprocess", "dummypython", "finished", "finishedq", "fsresizer", "fstab",
    "grubcfg", "hostinfo", "hwclock", "initcpio", "initcpiocfg", "initramfs", "initramfscfg",
    "interactiveterminal", "keyboard", "keyboardq", "license", "locale", "localecfg",
    "localeq", "luksbootkeyfile", "luksopenswaphookcfg", "machineid", "mkinitfs", "mount",
    "netinstall", "networkcfg", "notesqml", "oemid", "openrcdmcryptcfg", "packagechooser",
    "packagechooserq", "packages", "partition", "plymouthcfg", "preservefiles", "rawfs",
    "removeuser", "services-openrc", "services-systemd", "shellprocess", "summary",
    "summaryq", "tracking", "umount", "unpackfs", "unpackfsc", "users", "usersq", "welcome",
    "welcomeq", "zfs", "zfshostid",
}


def load(path: Path):
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def settings() -> dict:
    return load(CALAMARES / "settings.conf")


def sequence() -> list[str]:
    return [step for part in settings()["sequence"] for steps in part.values() for step in steps]


def test_every_settings_file_is_yaml_calamares_can_read():
    for path in [CALAMARES / "settings.conf", *sorted((CALAMARES / "modules").glob("*.conf")),
                 CALAMARES / "branding" / "kidux" / "branding.desc"]:
        assert isinstance(load(path), dict), path


def test_every_step_is_a_module_calamares_has_or_one_of_kidux_s_instances():
    instances = {f"{i['module']}@{i['id']}": i for i in settings()["instances"]}
    for step in sequence():
        if "@" in step:
            assert step in instances, step
            assert instances[step]["module"] in MODULES
            assert (CALAMARES / "modules" / instances[step]["config"]).is_file()
        else:
            assert step in MODULES, step


def test_the_steps_run_in_the_order_the_install_needs():
    steps = [s for s in settings()["sequence"][1]["exec"]]
    # The initramfs before GRUB, whose menu names it: the image carries none.
    order = ["partition", "mount", "unpackfs", "machineid", "fstab", "users", "packages",
             "initramfs", "shellprocess@kidux-grub", "bootloader", "shellprocess@kidux-efi",
             "umount"]
    assert [s for s in steps if s in order] == order


def test_the_disk_gets_the_system_and_home_on_partitions_of_their_own():
    partition = load(CALAMARES / "modules" / "partition.conf")
    layout = {p["mountPoint"]: p for p in partition["partitionLayout"]}

    assert set(layout) == {"/", "/home"}
    assert partition["initialPartitioningChoice"] == "erase"
    assert partition["allowManualPartitioning"] is False
    assert all(p["filesystem"] == "ext4" for p in layout.values())


def test_the_computer_needs_what_the_user_guide_says():
    requirements = load(CALAMARES / "modules" / "welcome.conf")["requirements"]

    assert requirements["requiredStorage"] == 32
    assert {"storage", "ram", "root"} <= set(requirements["required"])


def test_the_administrator_has_sudo_and_there_is_no_root_password():
    users = load(CALAMARES / "modules" / "users.conf")

    assert users["setRootPassword"] is False
    assert users["sudoersGroup"] == "sudo"
    assert "sudo" in [g["name"] for g in users["defaultGroups"]]


def test_the_installer_and_the_live_boot_leave_the_installed_system():
    removed = load(CALAMARES / "modules" / "packages.conf")["operations"][0]["remove"]

    assert {"kidux-installer", "calamares", "live-boot"} <= set(removed)
    # Nothing the installed Kidux needs: the sign-in screen runs in cage.
    assert "cage" not in removed and "greetd" not in removed


def test_unpackfs_copies_the_squashfs_the_image_carries():
    unpack = load(CALAMARES / "modules" / "unpackfs.conf")["unpack"][0]

    assert unpack["source"] == "/run/live/medium/live/filesystem.squashfs"
    assert unpack["sourcefs"] == "squashfs"


def test_the_branding_names_pictures_that_are_there():
    branding = load(CALAMARES / "branding" / "kidux" / "branding.desc")

    assert branding["componentName"] == settings()["branding"] == "kidux"
    for picture in branding["images"].values():
        assert (CALAMARES / "branding" / "kidux" / picture).is_file(), picture
    assert (CALAMARES / "branding" / "kidux" / branding["slideshow"]).is_file()


def test_greetd_runs_the_installer_as_root_on_kidux_s_terminal():
    installer = tomllib.loads((PACKAGE / "greetd" / "installer.toml").read_text())

    assert installer["default_session"] == {"command": "/usr/libexec/kidux-installer-session",
                                            "user": "root"}
    assert installer["terminal"]["vt"] == 7


def run(script: str, cmdline: str, tmp_path, **environment) -> str:
    (tmp_path / "cmdline").write_text(cmdline + "\n")
    stand_ins = tmp_path / "bin"
    stand_ins.mkdir(exist_ok=True)
    (stand_ins / "greetd").write_text('#!/bin/sh\necho greetd "$@"\n')
    (stand_ins / "greetd").chmod(0o755)
    return subprocess.run(["sh", str(PACKAGE / "bin" / script)], capture_output=True, text=True,
                          check=True,
                          env={"PATH": f"{stand_ins}:/usr/bin:/bin",
                               "KIDUX_CMDLINE": str(tmp_path / "cmdline"),
                               **environment}).stdout.strip()


def test_the_live_system_s_greetd_starts_the_installer(tmp_path):
    assert run("kidux-installer-greetd", "boot=live quiet kidux.live kidux.lang=en_US.UTF-8",
               tmp_path) == "greetd --config /usr/share/kidux-installer/greetd.toml"


def test_without_kidux_live_greetd_starts_kidux_s_sign_in_screen(tmp_path):
    assert run("kidux-installer-greetd", "root=/dev/sda1 quiet", tmp_path) \
        == "greetd --config /usr/share/kidux/greetd.toml"


@pytest.mark.parametrize("cmdline, said", [
    ("boot=live kidux.live", "es_ES.UTF-8 es_ES es"),
    ("boot=live kidux.live kidux.lang=en_US.UTF-8 kidux.keyboard=us", "en_US.UTF-8 en_US us"),
])
def test_the_installer_speaks_the_boot_menu_s_language_and_types_with_its_keyboard(
        tmp_path, cmdline, said):
    assert run("kidux-installer-session", cmdline, tmp_path, KIDUX_INSTALLER_PRINT="1") == said


def test_the_drop_ins_apply_to_the_live_system_alone():
    greetd = (PACKAGE / "systemd" / "greetd.service.d" / "zz-kidux-installer.conf").read_text()
    firstboot = (PACKAGE / "systemd" / "kidux-firstboot.service.d" / "kidux-installer.conf").read_text()

    # After kidux-session's own drop-in, kidux.conf, which sets greetd's.
    assert "ExecStart=/usr/libexec/kidux-installer-greetd" in greetd.splitlines()
    assert "ConditionKernelCommandLine=!kidux.live" in firstboot.splitlines()
