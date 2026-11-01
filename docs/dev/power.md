# Suspend and hibernate

What a Kidux computer does when its lid closes, and when it is left alone
after its screen has turned off (D119). The panel says *suspend*
("Suspender") and *hibernate* ("Hibernar"), logind's words, which the
adult reading the page understands; *suspend, then hibernate after a
minute* is systemd's suspend-then-hibernate. In the code, "sleep" is
suspend.

## 1. The settings

Three settings in `config.toml` (`kiduxd/config.py`), on the panel's
*Suspend and hibernate* page (panel.md), and one that no page offers:

| Key | Values | Default |
|---|---|---|
| `lid_action` | `sleep_then_hibernate`, `sleep`, `nothing` | `sleep_then_hibernate` |
| `idle_action` | `sleep_then_hibernate`, `sleep`, `screen_off_only` | `sleep_then_hibernate` |
| `idle_sleep_minutes` | 1 to 240 | 20 |
| `hibernate_delay_seconds` | not settable | 60 |

`screen_off_minutes`, the screen off of a computer left alone (D67,
session.md section 5), is the first stage and stays as it is; the idle
action is the second. A machine whose `config.toml` predates the keys
takes their defaults: `Config.load` fills a missing key from `DEFAULTS`,
which is the migration, and nothing else in the file changes.

`Daemon1.GetConfig` returns the three with what the computer can do,
`can_sleep`, `can_hibernate` and `hibernate_reason`; `Daemon1.SetConfig`
takes the three (daemon.md section 15).

## 2. What the computer can do

`kiduxd/power.py`, pure but for reading two files, asks logind, as root,
`CanSuspend`, `CanHibernate` and `CanSuspendThenHibernate`: anything but
`yes` is a no, and the computer can hibernate only when both of the
last two are `yes`. When it cannot, the reason is, in this order:

- `secure_boot`: `/sys/kernel/security/lockdown` has anything but `[none]`
  chosen, which Secure Boot does, and a locked-down kernel refuses to
  hibernate;
- `no_swap`: `/proc/swaps` lists no swap space but zram, which cannot hold
  the memory while the computer is off;
- `no_resume`: the start after hibernating would not look for the memory
  saved: neither `resume=` on the kernel's command line nor a resume
  device in `/sys/power/resume`, which Debian's initramfs sets when
  `/etc/initramfs-tools/conf.d/resume` names one (`power.resumes`).
  logind answers yes without it on a UEFI computer, where systemd writes
  the `HibernateLocation` EFI variable, but only a systemd initrd reads
  that variable; initramfs-tools starts afresh and the session is lost.
  Debian's installer writes `RESUME=none` for a swap file. It is checked
  even when logind says yes;
- `unsupported`: anything else logind knows, such as a swap space smaller
  than the memory in use.

A setting the computer cannot do is done as the nearest one it can, and
the setting itself is kept: `sleep_then_hibernate` as `sleep`, and `sleep`,
on a computer that cannot sleep, as `nothing` for the lid and
`screen_off_only` for idleness (`power.lid_action`, `power.idle_action`).
The panel offers every choice, shows the setting as stored, and warns in
one line when the computer cannot hibernate, or cannot suspend: why, and
that choosing to hibernate suspends instead; for no swap, or a swap too
small, with the address of the guide's section on making a swap space
(`words.SWAP_GUIDE_URL`, in the screen's language).

## 3. The lid

logind handles the lid, from a drop-in the daemon writes, root's and 0644,
`/etc/systemd/logind.conf.d/50-kidux-power.conf` (`paths.LOGIND_POWER`):

```ini
[Login]
HandleLidSwitch=suspend-then-hibernate
HandleLidSwitchExternalPower=suspend-then-hibernate
HandleLidSwitchDocked=ignore
```

`suspend-then-hibernate`, `suspend` or `ignore`, for the lid action the
computer can do, the same on battery and on mains power; nothing while the
laptop is docked or another screen is connected, logind's own test of
docked. The daemon writes it at every start, so that an upgraded machine
gets it and a computer that has gained or lost the means to hibernate
does what it now can, and when `lid_action` is set; when the text changed,
it has logind read its configuration again with SIGHUP to its main process
(`org.freedesktop.systemd1.Manager.KillUnit`, as `systemctl kill -s HUP
systemd-logind`), never a restart, which would end every session.
`kidux-session`'s own `logind.conf.d/kidux.conf` sets nothing about the
lid: it is in `/usr/lib`, named after `50-…`, and would win.

The delay is systemd-sleep's, from
`/etc/systemd/sleep.conf.d/50-kidux-power.conf` (`paths.SLEEP_POWER`),
which the daemon writes at every start and systemd-sleep reads at every
sleep: `HibernateDelaySec=60s` from `hibernate_delay_seconds`, and
`HibernateOnACPower=yes`, so that a laptop plugged in hibernates too. Each
key is written only for a systemd that knows it, from its manager's
`Version`: 239 and 254 (trixie has 257).

Nothing else on a Kidux screen handles the lid. labwc has no lid handling
of its own; the launcher (launcher.md section 5) and `kidux-lid-watch`
(session.md section 5) read the switch, lock the session and power the
laptop's own panel off, and take no `handle-lid-switch` inhibitor, so
logind acts on the lid as it is set. With the lid set to `nothing`, or
docked, what they do is all that happens. `LidSwitchIgnoreInhibited`
stays logind's default, yes: a video playing does not keep a closed laptop
awake.

## 4. A computer left alone

`kidux-idle` (session.md section 5) arms a third `swayidle` timeout beside
the lock and the screen off, `KIDUX_IDLE_SLEEP_SECONDS`: `idle_sleep_minutes`
in seconds, or 0, nothing armed, when the idle action is
`screen_off_only` or the computer cannot sleep (`kidux.idle.sleep_seconds`).
The greeter gives it to a child's session (`flow.py`), `greeter-session`
to the sign-in and lock screens. When it fires, `kidux-idle sleep` calls
`System1.SleepWhenIdle`, whose action is `self` (the children and the
trusted screens): a child may not suspend through polkit, and the setting,
the capability and the inhibitors are the daemon's to weigh. The daemon
does nothing when the idle action comes to `screen_off_only`, or when
logind's `BlockInhibited` holds `idle` or `sleep` (`systemd-inhibit
--what=idle`, a call); otherwise it calls `Suspend(false)` or
`SuspendThenHibernate(false)`, audited as `sleep when idle`, and answers
what it did. A video holds the compositor's idle inhibitor (the Wayland
idle-inhibit protocol, which labwc and cage honour), so `swayidle` fires
neither the screen off nor the sleep while it plays. logind's own
`IdleAction=` is not used: it needs every session's `IdleHint`, which
neither the sign-in screen nor a frozen child's session sets.

Each screen counts its own minutes, from when it comes to the front: a
child's session left alone locks after `idle_lock_minutes`, and the lock
screen, which then has the front, counts its screen off and its sleep from
there.

## 5. Locking before any sleep

Closing the lid must never be a way out of a time limit (D67). The daemon
holds a delay inhibitor on sleep (`kiduxd.logind.SleepGuard`); when logind
signals `PrepareForSleep(true)`, for the lid, idleness, a key or anything
else, it locks every unlocked child's session with reason `sleep`, the
lock of daemon.md section 10, and lets the inhibitor go, and takes a new
one at `PrepareForSleep(false)`. `kidux-session`'s logind drop-in sets
`InhibitDelayMaxSec=15`, as long as a lock can take: the lock screen's
start and the switch to it. A locked session is not counted, so nothing is
spent while the computer sleeps; the launcher's own lock for the lid
(`LockFor("lid")`), which usually arrives first, finds it locked, or is
found locked.

## 6. Making the computer able to hibernate

`kidux-hibernate-setup`, `/usr/lib/kidux/kidux-hibernate-setup` of `kidux-session`, gives the
computer what hibernating needs: a swap space as large as the memory, and
the start after hibernating told where it is. `kidux-session`'s postinst
runs it at every install and upgrade, and the installer runs it with
`--install` in the new system, before it makes the initramfs and GRUB's
configuration (`shellprocess@kidux-hibernate`).

- A swap partition at least as large as the memory is used as it is.
- Otherwise the swap file, `/swapfile`, is made, or made again, as large
  as `MemTotal` rounded up to a whole GiB, where it fits with 4 GiB left
  free: on `/`, counting the room an old swap file there gives back, or
  else on `/home`, when it is a filesystem of its own, as
  `/home/.kidux-swapfile`; `/etc/fstab` gets it as its one swap file of
  the two. A swap file in use is taken out of use first, and when swapoff
  refuses nothing more is done.
- The device's UUID and the file's first block, in pages (`filefrag -v`),
  go to Debian's initramfs, `/etc/initramfs-tools/conf.d/resume`
  (`RESUME=UUID=…`, `RESUME_OFFSET=…`, over the `RESUME=none` Debian's
  installer writes for a swap file), and to the kernel's command line,
  `/etc/default/grub.d/91-kidux-resume.cfg` (`resume=UUID=… resume_offset=…`),
  which `09_kidux` takes with `GRUB_CMDLINE_LINUX_DEFAULT`.
- On a running computer, the kernel is told too, `/sys/power/resume_offset`
  and then `/sys/power/resume`, as the initramfs tells it at a start, so
  that the computer hibernates before any restart; and the initramfs and
  GRUB's configuration are made again.

It does nothing in a chroot or an image being built, under Secure Boot's
lockdown, when the memory's size cannot be read, without room, or when
the resume device is set and the swap is large enough already; it prints
and logs (`kidux-hibernate-setup` in the journal) what it did or why not,
and never fails the package's installation. Purging `kidux-session`
removes `91-kidux-resume.cfg`; the swap file and the initramfs's resume
setting stay, the machine's own.

## 7. Trying it by hand

On a Kidux laptop that can hibernate (Secure Boot off, a swap space as
large as the memory in use), as its administrator over SSH:

1. `systemctl hibernate`: the computer turns off, and turning it on comes
   back to the screen it was on.
2. A child signed in, the lid closed for less than a minute and opened:
   the lock screen at once, the session locked, its time stopped.
3. The lid closed for more than a minute: the computer is off; turned on,
   the lock screen; `journalctl -b -1 | grep -i hibernat` shows the
   hibernation.
4. Left alone `idle_sleep_minutes` (set it to 1 on the panel to try it):
   the screen off, then sleep, then off a minute later. With a video
   playing in a module, nothing happens; with `systemd-inhibit
   --what=idle sleep 600` running, nothing happens.
5. The same on mains power.
6. With another screen connected, the lid only turns the laptop's panel
   off, and the computer stays awake.
7. On a computer that cannot hibernate (Secure Boot on, or no swap): the
   *Suspend and hibernate* page warns why, with the guide's address for
   no swap, and the lid suspends (`HandleLidSwitch=suspend` in the
   drop-in).
8. `systemd-analyze cat-config systemd/logind.conf` shows the drop-in last
   for the lid; `systemd-inhibit --list` shows Kidux's delay lock.
