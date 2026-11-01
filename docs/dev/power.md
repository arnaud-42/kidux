# Suspending

What a Kidux computer does when its lid closes, and when it is left alone
after its screen has turned off (D119): it suspends, and it never
hibernates. In the code, "sleep" is suspend.

## 1. The settings

Three settings in `config.toml` (`kiduxd/config.py`), on the panel's
*Suspending the computer* page (panel.md):

| Key | Values | Default |
|---|---|---|
| `lid_action` | `sleep`, `nothing` | `sleep` |
| `idle_action` | `sleep`, `screen_off_only` | `sleep` |
| `idle_sleep_minutes` | 1 to 240 | 20 |

`screen_off_minutes`, the screen off of a computer left alone (D67,
session.md section 5), is the first stage and stays as it is; the idle
action is the second. A machine whose `config.toml` predates the keys
takes their defaults: `Config.load` fills a missing key from `DEFAULTS`,
which is the migration, and nothing else in the file changes. A value
`SetConfig` would not take, such as `sleep_then_hibernate`, is done as the
default.

`Daemon1.GetConfig` returns the three with `can_sleep`, whether the
computer can suspend; `Daemon1.SetConfig` takes the three (daemon.md
section 15).

## 2. What the computer can do

`kiduxd/power.py`, pure, asks logind, as root, `CanSuspend`: anything but
`yes` is a no. On a computer that cannot suspend, the lid's `sleep` is
done as `nothing` and idleness's as `screen_off_only`, the setting itself
kept (`power.lid_action`, `power.idle_action`), and the panel says so in a
warning.

Kidux never hibernates. `kidux-session` ships
`/usr/lib/systemd/sleep.conf.d/kidux.conf`, with `AllowHibernation=no`,
`AllowSuspendThenHibernate=no` and `AllowHybridSleep=no`, so that no key,
program or setting can hibernate the computer, and logind answers no to
`CanHibernate`: a computer whose start cannot restore what hibernating
saved hangs at every start until someone types `noresume` at GRUB's
prompt (D119). Kidux never changes swap, the kernel's command line or the
initramfs.

## 3. The lid

logind handles the lid, from a drop-in the daemon writes, root's and 0644,
`/etc/systemd/logind.conf.d/50-kidux-power.conf` (`paths.LOGIND_POWER`):

```ini
[Login]
HandleLidSwitch=suspend
HandleLidSwitchExternalPower=suspend
HandleLidSwitchDocked=ignore
```

`suspend` or `ignore`, for the lid action the computer can do, the same on
battery and on mains power; nothing while the laptop is docked or another
screen is connected, logind's own test of docked. The daemon writes it at
every start, so that an upgraded machine gets it and a computer that has
gained or lost the means to suspend does what it now can, and when
`lid_action` is set; when the text changed, it has logind read its
configuration again with SIGHUP to its main process
(`org.freedesktop.systemd1.Manager.KillUnit`, as `systemctl kill -s HUP
systemd-logind`), never a restart, which would end every session.
`kidux-session`'s own `logind.conf.d/kidux.conf` sets nothing about the
lid: it is in `/usr/lib`, named after `50-…`, and would win.

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
x A video holds the compositor's idle inhibitor (the Wayland
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

## 6. Trying it by hand

On a Kidux laptop, as its administrator over SSH:

1. A child signed in, the lid closed for a few seconds and opened: the
   computer suspends within a second or two, and on opening shows the
   lock screen, the session locked and its time stopped.
2. The lid closed for several minutes: the same, never off.
3. Left alone `idle_sleep_minutes` (set it to 1 on the panel to try it,
   and sign in again): the session locks, the screen turns off, the
   computer suspends. With a video playing in a module, nothing happens;
   with `systemd-inhibit --what=idle sleep 600` running, nothing happens.
4. The same on mains power.
5. With another screen connected, the lid only turns the laptop's panel
   off, and the computer stays awake.
6. `busctl call org.freedesktop.login1 /org/freedesktop/login1
   org.freedesktop.login1.Manager CanHibernate` as root answers `no`, and
   `sudo systemctl hibernate` is refused.
7. `systemd-analyze cat-config systemd/logind.conf` shows the drop-in last
   for the lid; `systemd-inhibit --list` shows Kidux's delay lock.
