# Installing Debian on the development server — MacBook Pro Retina 15" (mid-2015)

The development and test server is a MacBook Pro Retina 15" mid-2015 (A1398) with the
AMD Radeon R9 M370X, which makes it a **MacBookPro11,5** (the 11,4 is the Intel-only
variant). Core i7 quad-core 2.8 GHz, 16 GB RAM, 512 GB PCIe flash, Intel Iris Pro 5200
plus AMD Radeon R9 M370X, Broadcom BCM43602 Wi-Fi, Force Touch trackpad, Spanish
backlit keyboard.

Good news about this generation: 64-bit EFI (the 32-bit EFI problem only affects
2006–2008 Macs) and no T2 chip (2018+), so nothing has to be changed in macOS Recovery
to boot from USB. Checked against the Arch wiki "Laptop/Apple" page on 2026-09-22.

This machine has **two roles at once**: it is the development server (reached over
SSH, parent account, builds and tests) and it is the family's real children's
computer, running the kiosk daily once phase 1 is usable. Both coexist because Linux
is multi-user: a child's graphical session and the parent's SSH session run side by
side. It is installed from the official Debian installer, **not** from our ISO,
because our ISO does not exist yet. Once it does, it is reinstalled from it with
"Reinstall, keep my data", like any user would.

Rules that follow from the double role:

- Never hand-edit the running system to make something work. Build the `.deb`,
  install it from the `testing` suite, exactly as a user's machine would get it. This
  is what keeps the kiosk on this machine identical to what we ship.
- Heavy builds (ISO, Chromium-based web apps) run in GitHub Actions or at night, not
  while a child is using the machine.
- The kiosk hardening (no extra VTs, GRUB password, no `sudo` for children) applies
  here too. SSH is the maintenance path; keep the parent user's key working.

## 1. Download the installer (on the Mac)

1. Get the current Debian 13 netinst image from https://www.debian.org/download
   (`debian-13.x.0-amd64-netinst.iso`, 13.7 as of September 2026). Since Debian 12
   the official image includes the non-free firmware, so the old "unofficial
   non-free" images are not needed.
2. Verify the checksum against `SHA256SUMS` from the same directory:

   ```bash
   shasum -a 256 debian-13.*-amd64-netinst.iso
   ```

## 2. Write the USB stick (on the Mac)

```bash
diskutil list                      # find the stick, e.g. /dev/disk4
diskutil unmountDisk /dev/disk4
sudo dd if=debian-13.*-amd64-netinst.iso of=/dev/rdisk4 bs=4m status=progress
diskutil eject /dev/disk4
```

balenaEtcher works too.

## 3. Boot the installer

1. Plug in a USB Ethernet adapter if you have one. Wi-Fi works with the included
   firmware, but a cable removes one variable from the first install.
2. Shut the MacBook down completely, power on holding `Option (Alt)`.
3. Choose the **"EFI Boot"** volume (the USB stick).
4. Pick **"Graphical install"**. If the screen goes black after choosing it, reboot,
   highlight the entry, press `e`, add `nomodeset` to the line starting with
   `linux`, and boot with `F10`; fix graphics after installation (section 6).

## 4. Installer choices

| Screen | Choice | Why |
|---|---|---|
| Language | English | System locale `en_US.UTF-8`; a dev server in English keeps logs and docs consistent. |
| Location / locale | Spain, `en_US.UTF-8` | Time zone Europe/Madrid. |
| Keyboard | Spanish | Physical keyboard is ES. |
| Network | Ethernet if present; otherwise Wi-Fi (`brcmfmac`, firmware included) | If Wi-Fi does not work in the installer, continue without network and fix it in section 5. |
| Hostname | `kidux` | The one actually used. mDNS is case-insensitive, so it is reached as `kidux.local`. |
| Domain | leave empty | |
| Root password | leave **empty** | Then the first user gets `sudo`. |
| User | your name, login `<user>` | |
| Partitioning | **Manual**: keep the existing 209 MB EFI partition (use as EFI System Partition), delete the macOS partitions, then 80 GB ext4 on `/` and the rest ext4 on `/home`, no swap partition | Wipes macOS. Mirrors the layout our own installer will use (see architecture, section 4); 80 GB instead of 24 because this machine also builds packages. Swap file later. |
| Software selection | untick everything except **SSH server** and **standard system utilities** | No desktop: the kiosk session will be installed later from our packages. |
| GRUB | install to the primary drive; answer **Yes** to "Force GRUB installation to the EFI removable media path" | Apple firmware sometimes ignores NVRAM boot entries; the removable path (`EFI/BOOT/BOOTX64.EFI`) always boots. |

Reboot, remove the USB stick. The machine should boot straight into Debian.

## 5. First boot: network, SSH, mDNS

Log in on the console as your user.

```bash
sudo apt update
sudo apt install openssh-server avahi-daemon network-manager firmware-brcm80211 \
                 firmware-linux git curl
sudo systemctl enable --now ssh avahi-daemon NetworkManager
```

Wi-Fi from the console, if not done during the install:

```bash
nmcli device wifi list
nmcli device wifi connect "<SSID>" --ask
```

A Wi-Fi set up in the Debian installer is `ifupdown`'s, in
`/etc/network/interfaces`, and NetworkManager leaves it alone: `nmcli device
status` says `unmanaged`. The panel's Network page (D62) then shows it and
cannot change it. To hand it to NetworkManager, at the machine's own
keyboard, since the Wi-Fi goes down: take the interface down first, while
its stanza is still in the file, because `ifdown` is what ends the
`wpa_supplicant` that `ifupdown` started, and a restart of `networking`
cannot end one whose stanza is gone, which leaves it holding the card;
then delete the Wi-Fi's `allow-hotplug`, `iface` and `wpa-` lines, restart
NetworkManager, and join the network again:

```bash
sudo ifdown wlp3s0
sudo nano /etc/network/interfaces
sudo systemctl restart NetworkManager
sudo nmcli device wifi connect "<SSID>" --ask
```

A restart of the machine after the edit does the same, which is what the
user guide, section 8, tells a family, who then join the network from the
Network page.

If `brcmfmac` refuses to start the BCM43602 (`brcmf_pcie_probe: failed 14e4:43ba`
in `journalctl -k`), add the kernel parameter `brcmfmac.feature_disable=0x82000`
(the workaround documented on the Arch wiki) to `GRUB_CMDLINE_LINUX_DEFAULT` in
`/etc/default/grub`, run `sudo update-grub`, reboot. The proprietary
`broadcom-sta-dkms` driver is a last resort; it is unstable on recent kernels.

Check that Wi-Fi is up before moving on:

```bash
nmcli device status          # the wlp... device should say "connected"
ping -c 3 debian.org
```

Only if the device is missing or `unavailable`, look at `journalctl -k | grep brcmfmac`
for the `brcmf_pcie_probe: failed` message and apply the kernel parameter above.

**On the main Mac** (not on the laptop), copy your SSH key so that logins and VS Code
Remote-SSH need no password. Create the key first if `~/.ssh/id_ed25519.pub` does not
exist (`ssh-keygen -t ed25519`, accept the defaults):

```bash
ssh-copy-id -i ~/.ssh/id_ed25519.pub <user>@kidux.local
ssh <user>@kidux.local
```

The first connection asks to trust the server fingerprint; answer `yes`. If
`kidux.local` does not resolve, `avahi-daemon` is not running on the laptop; use the
IP shown by `ip -4 a` on the laptop meanwhile.

## 5b. Retina console: readable font and brightness

The text console runs at the panel's native 2880x1800, so the font is tiny and the
backlight starts low. Until SSH is working, fix both from the console:

```bash
setfont /usr/share/consolefonts/Lat15-TerminusBold32x16.psf.gz
cat /sys/class/backlight/gmux_backlight/max_brightness
echo <that number> | sudo tee /sys/class/backlight/gmux_backlight/brightness
```

`gmux_backlight` is Apple's backlight controller on this model. To keep the large
font on every boot: `sudo dpkg-reconfigure console-setup`, font Terminus, size
16x32. Once the network is up, `sudo apt install brightnessctl` gives
`brightnessctl set 100%`.

## 6. Graphics on the 11,5

When Linux is booted through EFI, Apple's firmware hands the display to the
**discrete AMD GPU** and leaves the Intel Iris Pro invisible to the OS. Using the Intel
part instead would need the `apple_set_os.efi` trick, and it is not needed: the AMD GPU
runs the children's kiosk perfectly well.

- The R9 M370X ("Cape Verde", GCN 1.0) is driven by the in-kernel `radeon` driver
  with firmware from `firmware-amd-graphics`. It provides KMS and OpenGL, which is
  all `cage` (wlroots) and Chromium need for Scratch, MakeCode and GCompris. Nothing
  to configure.
- Cost of the AMD GPU: more heat and power than the Intel one would use. Keep the
  machine on mains power; it is a desktop replacement, not a travel laptop.
- If the console freezes or goes black after boot, add `radeon.dpm=0` to
  `GRUB_CMDLINE_LINUX_DEFAULT` and `sudo update-grub`.
- If the kiosk ever feels slow in graphics-heavy modules, try `amdgpu` with
  `radeon.si_support=0 amdgpu.si_support=1`. Not needed until measured.

## 7. Laptop settings

Until the kiosk exists, the lid must not suspend the machine (it would drop SSH).
Once children use it, Kidux's own power policy takes over: the screen off when
left alone, suspend on the lid's close and when left alone longer, as the adult
sets on the panel (power.md), shutdown from the launcher.

```bash
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nHandleLidSwitch=ignore\nHandleLidSwitchExternalPower=ignore\n' \
  | sudo tee /etc/systemd/logind.conf.d/server.conf
sudo systemctl restart systemd-logind
sudo systemctl mask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

Because logind now ignores the lid, closing it leaves the panel lit and burning
power. Until Kidux is installed, a small watcher handles it: backlight to zero
and framebuffer powered down when the lid closes, both restored when it opens.
Kidux's own screens power the panel off through the compositor and leave the
brightness alone (D61), so this watcher is retired before `kidux-base` goes on
(rollout.md, section 2): the two would fight over the lid. The lid is polled
once a second — procfs cannot be watched with
inotify, and `/proc/acpi/button/lid/LID0/state` is the interface this model reports
reliably. On this machine the panel is `gmux_backlight` (range 0–1023) and the DRM
`dpms` attribute is read-only, so brightness plus `/sys/class/graphics/fb0/blank` are
the only levers.

```bash
sudo tee /usr/local/sbin/kidux-lid-watch >/dev/null <<'EOF'
#!/bin/bash
set -u
BACKLIGHT=/sys/class/backlight/gmux_backlight
LID=/proc/acpi/button/lid/LID0/state
BLANK=/sys/class/graphics/fb0/blank
SAVED=/var/lib/kidux-lid-brightness

last=""
while :; do
    state=$(awk '{print $2}' "$LID" 2>/dev/null || true)
    if [ -n "$state" ] && [ "$state" != "$last" ]; then
        case "$state" in
        closed)
            current=$(cat "$BACKLIGHT/brightness" 2>/dev/null || echo 0)
            [ "$current" -gt 0 ] && printf '%s\n' "$current" > "$SAVED"
            echo 0 > "$BACKLIGHT/brightness" 2>/dev/null || true
            [ -w "$BLANK" ] && echo 4 > "$BLANK" 2>/dev/null || true
            ;;
        open)
            [ -w "$BLANK" ] && echo 0 > "$BLANK" 2>/dev/null || true
            restore=$(cat "$SAVED" 2>/dev/null || true)
            if [ -z "$restore" ]; then
                restore=$(( $(cat "$BACKLIGHT/max_brightness") / 2 ))
            fi
            echo "$restore" > "$BACKLIGHT/brightness" 2>/dev/null || true
            ;;
        esac
        last="$state"
    fi
    sleep 1
done
EOF
sudo chmod 755 /usr/local/sbin/kidux-lid-watch

sudo tee /etc/systemd/system/kidux-lid-watch.service >/dev/null <<'EOF'
[Unit]
Description=Blank the panel while the lid is closed (development machine)
ConditionPathExists=/proc/acpi/button/lid/LID0/state

[Service]
Type=simple
ExecStart=/usr/local/sbin/kidux-lid-watch
Restart=always
RestartSec=2
Nice=10

[Install]
WantedBy=multi-user.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now kidux-lid-watch
```

Check it with `systemctl status kidux-lid-watch` and
`cat /sys/class/backlight/gmux_backlight/brightness` with the lid open and shut. If
the brightness restored on opening is not the one you like, set the one you want with
`brightnessctl` while the lid is open, close and open it again: the watcher saves
whatever was in use.

Keyboard backlight (`applesmc`) and the Force Touch trackpad work out of the box on
the 6.12 kernel; irrelevant for SSH use anyway.

## 8. Development tools on the server

```bash
# Claude Code CLI (native installer, uses the claude.ai subscription; no API key)
curl -fsSL https://claude.ai/install.sh | bash
claude   # first run opens the browser login flow

# Repository
git clone git@github.com:<owner>/kidux.git ~/kidux
```

Then connect VS Code as described in [dev-environment.md](dev-environment.md).

## 9. Checklist

- [ ] Boots without USB, lands on a login prompt.
- [ ] `ssh kidux.local` works with the key, no password.
- [ ] Wi-Fi survives a reboot (`nmcli device status`).
- [ ] Lid closed does not suspend.
- [ ] `claude` authenticates and answers.
- [ ] Repo cloned and `git pull` works.
