# kidux-session

How the machine boots into the sign-in screen, how a child's session is
started, how the lock screen gets a screen of its own, and every door that is
closed so that the child's Unix user is the only thing a child can be. It is
one package, and it can be removed as one package: that is what makes it safe
to try, and what turns a kiosk back into a computer.

This is the design; the decisions it rests on are D4, D7, D10, D12, D16, D17
and D24, D25, D28 in `architecture.md`. The daemon it works with is in
`daemon.md`.

## 1. What is in it

```
/usr/share/kidux/greetd.toml                     section 2
/usr/lib/systemd/system/greetd.service.d/kidux.conf
/usr/libexec/kidux-session                       section 3
/usr/share/kidux/labwc/kiosk/                    rc.xml, menu.xml, themerc-override
/usr/share/kidux/labwc/desk/                     the same, for a child with windows
/usr/lib/kidux/session-inner
/usr/lib/kidux/greeter-session                   sections 2 and 4
/usr/lib/kidux/labwc-rc                          labwc's rc.xml with the pointer's part, section 3
/usr/lib/kidux/kidux-lid-watch                   the lid on the trusted screens, section 5
/usr/lib/kidux/kidux-idle                        a screen left alone, section 5
/usr/lib/systemd/system/kidux-locker@.service
/etc/pam.d/kidux-locker
/usr/share/glib-2.0/schemas/90_kidux.gschema.override   GTK's inspector, section 6
/usr/lib/systemd/logind.conf.d/kidux.conf        section 6
/usr/lib/sysctl.d/60-kidux.conf
/etc/ssh/sshd_config.d/kidux.conf
/usr/lib/systemd/system/getty@.service.d/kidux.conf
/etc/systemd/system/ctrl-alt-del.target          symlink to /dev/null
/usr/share/polkit-1/rules.d/40-kidux-children.rules
/usr/lib/udev/rules.d/70-kidux-switches.rules     the lid, section 5
/usr/lib/udev/rules.d/91-kidux-keyboard-light.rules   the keyboard's light, section 5
/etc/default/grub.d/90-kidux.cfg                 section 7
/etc/grub.d/09_kidux
/usr/share/plymouth/themes/kidux/                the boot splash, section 7
```

Nothing a person types is among them, which is why the programs are in
`/usr/libexec` and `/usr/lib/kidux` rather than on the `PATH`; and nothing a
person types comes with them: the package conflicts with `foot`, the
terminal `labwc` suggests, `wmenu`, a launcher's menu, and
`x-terminal-emulator`, every terminal emulator there is (Chromium's
recommendations bring one), so
that installing Kidux, or a module, with recommends leaves them out and a
machine that has them removes them.

Depends on `adduser`, `greetd`, `cage`, `labwc` (0.8 in trixie), `xwayland`, `swaybg`,
`swayidle`, `wlopm`, `wlr-randr`, `xdg-user-dirs`, `brightnessctl`, `plymouth`,
`plymouth-label`, `polkitd`,
`pipewire-audio`, `python3-gi`, `kidux-daemon`, `kidux-greeter`,
`kidux-launcher`.

## 2. greetd

greetd's own `/etc/greetd/config.toml` belongs to the greetd package, so
`greetd.service.d/kidux.conf` points it at `/usr/share/kidux/greetd.toml`
with `greetd --config` instead of fighting over the file:

```toml
[terminal]
vt = 7

[default_session]
command = "/usr/lib/kidux/greeter-session"
user = "_greetd"
```

`/usr/lib/kidux/greeter-session` asks the daemon (`GetConfig`) for the
machine's language, keyboard layout and display scale, exports them, and
`exec`s `cage -- /usr/lib/kidux/session-inner /usr/libexec/kidux-greeter`,
through `/usr/lib/kidux/compositor` (below):
the inner step of section 3 sets the scale and the idle dimming for the
sign-in screen exactly as for a child's session. If the daemon cannot be
asked, the screen comes up in the defaults anyway.

Both compositors, `cage` for the trusted screens and `labwc` for a child's
session, start through `/usr/lib/kidux/compositor`. wlroots draws with the
card's OpenGL ES, and in software (pixman) by itself only on a card with
no render node; a card with a render node and no working OpenGL, as a
virtual machine's VMSVGA without 3D in VirtualBox or VMware, leaves it no
way to draw, and the compositor stops at once. `compositor` starts it
once more with `WLR_RENDERER=pixman` when it stops of its own accord
within five seconds with no renderer named, and says so in the journal;
on any other card the first start stays. `compositor` is the session's
first process while the compositor runs as its child, and ends as the
compositor would have: greetd ends a session, and systemd the lock screen
(`KillMode=mixed`), with a signal to the first process alone and kills
the rest once it is gone, so `compositor` passes SIGTERM, SIGHUP and
SIGINT on to the compositor and waits for it to end, and a compositor so
ended is not started again.

Before it starts `cage`, the sign-in screen waits, up to ten seconds, until
no other session of its seat is still `closing` in logind. greetd starts it
the moment the session before it ends, a child's logged out or the sign-in
screen's own when greetd restarts, and that session's compositor, or its
lock screen's, may take a second or two more to exit. One that lets go of
the display after `cage` has set it up leaves the screen showing what the
graphics card last had in memory, stripes of noise, while the sign-in screen
draws where nobody sees it. The journal says how long it waited, and for
which sessions.

The keyboard layout of both trusted screens is always the machine's, never a
child's (D29). A password has to be typed the way it was set, and passwords
are set in the adult panel, which is a trusted screen too.

`vt = 7` is greetd's own default, and its unit already conflicts with
`getty@tty7`. No auto-login (D10). The greeter runs under
`/etc/pam.d/greetd-greeter`, which includes `login`, so it has a logind session
of class `greeter` and `cage` can take the display through logind like any
compositor.

greetd starts sessions with `source_profile = false`: without it, the child's
`~/.profile` would run before their session, and a child's home is theirs to
write (D17).

`greetd.service.d/kidux.conf` sets `StartLimitIntervalSec=0`. greetd's unit
gives up after five failures in thirty seconds, which on a kiosk is a black
screen with no way out; a greeter that crashes on start is better restarted
forever than not at all, and the greeter also guards its own start-up.

`kidux-session.postinst` enables greetd as the display manager and starts
nothing: greetd starting now would end whatever is on terminal 7.

The display scale is set by `session-inner` from inside the compositor
(D49), with `wlr-randr`. `cage` refuses a configuration that comes while it
is still bringing its output up (`wlr-randr` says *failed to apply
configuration*), and it can list an output before it has a mode, so
`session-inner` asks again every quarter of a second for up to five, both
for a listing with a `current` mode and for the scale itself; a scale that
took more than one try is logged with how many, and one never taken with
`wlr-randr`'s words (`journalctl -t kidux-session`). `20-scale.py` starts
the sign-in screen five times at a scale of 2 and finds it 640x400 each
time.

Then, before the screen's program starts, `session-inner` turns the output
off and on once with `kidux-idle screen off` and `screen on`, as opening the
lid does: `wlr-randr` under `cage`, `wlopm` under labwc. On the development
MacBook's Radeon, setting the scale, or a compositor before this one letting
go of the display late, can leave the screen showing what the graphics card
last had in memory, stripes of noise or the boot's text, while the
compositor draws where nobody sees it; a fresh start of the output puts
the compositor's picture back on it.

## 3. The child's session

The greeter, once greetd has accepted the child's password and the daemon's
`CheckAccess` has said `allowed`, sends greetd:

```json
{"type": "start_session",
 "cmd": ["/usr/libexec/kidux-session"],
 "env": ["KIDUX_LANGUAGE=es_ES.UTF-8", "XKB_DEFAULT_LAYOUT=es",
         "KIDUX_DISPLAY_SCALE=2", "KIDUX_AVATAR=fox", "KIDUX_WINDOWS=1"]}
```

(`KIDUX_WINDOWS=1` only for a child with windows, D46: the launcher reads
it and floats that child's modules in windows.)

greetd starts `kidux-session` as the child with that environment added to
PAM's. The values come from `Children1.List` and `Daemon1.GetConfig`, which the
greeter may call and the child may not (D24). **A child's session never reads
`/home/.kidux`**: it cannot, the directory is closed to it, and it does not
need to.

`/usr/libexec/kidux-session`, a shell script:

1. `XDG_SESSION_TYPE=wayland`, `XDG_CURRENT_DESKTOP=kidux`, and `MOZ_ENABLE_WAYLAND`
   and friends for the programs modules will bring. `LANG` and `LC_ALL` are set
   from `KIDUX_LANGUAGE`, and `LANGUAGE` is unset. The language travels under
   its own name because greetd opens the session through Debian's `login` PAM
   stack, whose `pam_env` sets `LANG` from `/etc/default/locale` after the
   greeter's variables are in: a `LANG` from the greeter would come out as the
   machine's. Without `KIDUX_LANGUAGE`, the session keeps the machine's `LANG`.
   `/usr/share/kidux/session/xdg` goes first in `XDG_CONFIG_DIRS` and
   `/usr/share/kidux/session/share` first in `XDG_DATA_DIRS`, for links out
   of a module (below).
2. `exec /usr/lib/kidux/compositor labwc -C /usr/share/kidux/labwc/kiosk
   -c <rc.xml> -s "/usr/lib/kidux/session-inner --keep-running
   /usr/libexec/kidux-launcher"`: `labwc` (D58), through `compositor`
   (section 2), with Kidux's configuration and no other: `-C` is the only
   directory it reads, so a child's `~/.config/labwc` is never read; `desk`
   in place of `kiosk` for a child whose modules open in windows
   (`KIDUX_WINDOWS=1`, D46). `-c` is that directory's `rc.xml` with the
   pointer's speed and the touchpad's scroll an adult set on the panel's
   Advanced page, `/etc/kidux/input.xml`, put in as its `<libinput>` part,
   or the middle steps' without the file (`kidux.pointer`, daemon.md
   section 15): `/usr/lib/kidux/labwc-rc` writes it at every start into a
   directory the session makes for itself under `$XDG_RUNTIME_DIR`,
   `kidux-labwc.XXXXXX`, new each time, which goes with the session; when
   that fails, labwc gets Kidux's `rc.xml` as it is. The trusted screens
   run under `cage`, which takes no such settings: they keep libinput's
   own. What `-s`
   names, run as the child, is the inner step, which sets the scale with
   `wlr-randr --output <name> --scale <scale>` on every output — the
   configuration does not know the scale, and `labwc` implements
   `wlr-output-management`, so it is set from inside, as for the trusted
   screens under `cage`, which implements it too. The scale is
   `$KIDUX_DISPLAY_SCALE`, or, when that is 0, automatic (D53, D56): the
   largest quarter that leaves the output's current mode roomy, 1600x960 or
   more, never less than 1, which `python3 -m kidux.screen <mode>` answers
   (1.75 for the MacBook's 2880x1800). The first output's mode is exported
   as `KIDUX_SCREEN_MODE`, for the panel to say what automatic comes to. A
   scale that cannot be set is logged, with what `wlr-randr` said. It then
   starts `swaybg -c '#fff6e9'`, Kidux's cream behind every window for the
   moment a restarted launcher, whose maximised window is the floor, is not
   there, and `kidux-idle` (section 5); runs `xdg-user-dirs-update` so
   that the child's home has its usual folders in the child's language,
   where modules save the child's work (D42); and runs the launcher in the
   loop of launcher.md section 4: restarted after a crash, the session
   ended after a log-out or after five crashes in a minute, by `labwc
   --exit`.

The two configurations are the whole of what a child's desktop can do,
root's and read-only to the child, each `rc.xml`, an empty `menu.xml`, and
a `themerc-override` with Kidux's colours on labwc's frame (ink on cream,
cream on ink for the window in use; an override in the configuration's own
directory, so that no theme of the child's changes it). What was found
trying each piece is labwc-notes.md.

- **Keys.** `<keyboard>` has four keybinds and no `<default />`, so none of
  labwc's own exist: `Super_L`, pressed and let go alone, is home: in the
  kiosk a `ForEach` over the window whose identifier is
  `org.kidux.Launcher` that focuses and raises it, on the desk the signal
  `-USR1` to the launcher, found as for Alt+F4, which shows the desk;
  `A-Tab` and `A-S-Tab` signal the launcher the same way, `-RTMIN+1` and
  `-RTMIN+2`, and its bar goes round the windows, lighting the one it
  points at until Alt is let go (D64, launcher.md section 5); `A-F4` is `Execute pkill -USR2 -f
  "^/usr/bin/python3 /usr/libexec/kidux-launcher"`, a signal the launcher
  hears (its process is `python3`, so it is found by its command line),
  and it closes the module on
  screen as the bar's *Close* does (launcher.md section 5, D45): the key
  never reaches the module, so Alt+F4 means the same in every one. A
  laptop's own keys for its screen, its keyboard's light and its sound,
  `XF86MonBrightnessUp` and `Down`, `XF86KbdBrightnessUp` and `Down`,
  `XF86AudioRaiseVolume`, `LowerVolume` and `Mute`, the keysyms a MacBook
  and a PC send alike, are `Execute` keybinds that run `kidux-keys` as the
  child (D61, keys.md), in both configurations.
- **Mouse.** `<mouse>` has no `<default />` either, and no binding shows a
  menu, so the empty `menu.xml` is never reached. In the kiosk, a press in
  a window focuses and raises it, and the close button of a title bar, which
  only a window taken out of fullscreen has, closes it. On the desk, every frame's: a press focuses and
  raises, the title bar moves the window and a double click maximises it,
  the edges and corners resize it, and the iconify, maximise and close
  buttons do what they say.
- **The kiosk.** `<windowRule identifier="*" type="normal">` with
  `Maximize`: every main window of every module, and the launcher's, fills
  the room above the bar, while a dialog, `type` `dialog` since it has a
  parent, floats over its window. A second rule, `serverDecoration="no"`
  with `SetDecorations` `none`, takes the frame off every window, a dialog
  and an X11 one included, which takes no notice of
  `serverDecoration` alone. A main window the rule misses, an X11 one that
  says no type, is maximised by the launcher (launcher.md section 5). One
  limit is labwc 0.8's: a window that comes up fullscreen gets a title bar
  back when the launcher takes it out of fullscreen, whatever a rule says
  (labwc-notes.md, D60). Kidux's modules do not ask for fullscreen, GCompris
  included (`--window`); a program that does keeps a thin title bar with
  its close button (`<layout>icon:close</layout>`).
- **The desk** (D57). `<decoration>server</decoration>`, every window in
  labwc's frame with `<layout>icon:iconify,max,close</layout>`, placed in
  `cascade`; only the launcher's window has a rule, maximised, without a
  frame and `ToggleAlwaysOnBottom`: the desk's floor, under every window.
  Super there reaches the launcher, which minimises every window to show
  the desk and brings them back when the child leaves it (launcher.md
  section 5). Nothing is `skipTaskbar`, which would take a window off the list the launcher reads.
- **XWayland** is on: labwc starts it, as the child, when an X11 program
  first connects, and ends it ten seconds after the last one
  (`<xwaylandPersistence>no`). `DISPLAY` is set for every program the
  session starts.

The keyboard layout comes from `XKB_DEFAULT_LAYOUT` in the environment,
which `labwc` reads when its configuration names none. What the
configuration cannot close is the compositor's own Ctrl+Alt+F*n*, which
asks logind to switch terminals and is refused
(section 6). The trusted screens keep `cage`, run without `-s`, so no
key there ever asks. The daemon switches VTs through logind and nothing
else does; and when it gives a session the screen back after the lock
screen, it wakes the input devices, since a compositor on wlroots 0.18
otherwise sets them up only on the child's first key, which is lost
(daemon.md section 10).

**Sound** is PipeWire (D35), 1.4 in trixie, from `pipewire-audio`, which
`kidux-session` depends on. Its user units are enabled for every user and
start with the child's user manager, which logind starts for every session of
class `user`; nothing in the session script starts it, and there is no
system-wide sound server. A module plays sound through the socket in the
child's `$XDG_RUNTIME_DIR`, like any desktop program.

**Links out of a module** (D107). A program that asks the desktop to open
a web page or a link, as Step's *Open in browser* does with a local HTML
file or a program's help with its web site, gets Kidux's answer, not a
browser: `kidux-session` installs a `mimeapps.list` in
`/usr/share/kidux/session/xdg` whose default for `text/html`,
`application/xhtml+xml`, `x-scheme-handler/http` and
`x-scheme-handler/https` is `kidux-closed.desktop`, which is in
`/usr/share/kidux/session/share/applications`, kept out of every menu.
Its program, `/usr/libexec/kidux-closed` (`kidux.closed`), sends the
desktop's notification *That opens the internet, which is closed here.*,
which the launcher shows as a bubble from the module whose scope sent it
(launcher.md section 2, D98), and exits 0, having opened nothing.
`xdg-open`, GLib and KDE's KIO all choose by those files, read from the
directories the session puts first; a KDE module's starter puts its own
restrictions' directory before them and keeps the rest (modules.md
section 2). A module that is a web page starts its browser itself,
`kidux-webapp`, and is not touched.

## 4. The lock screen's own screen

`kidux-locker@.service`, started by the daemon (`daemon.md` section 10):

```ini
[Unit]
Description=Kidux lock screen for %i
After=systemd-user-sessions.service
Conflicts=getty@tty8.service

[Service]
User=_greetd
PAMName=kidux-locker
TTYPath=/dev/tty8
TTYReset=yes
TTYVHangup=yes
StandardInput=tty
UtmpIdentifier=tty8
UtmpMode=user
Environment=XDG_SESSION_TYPE=wayland XDG_SESSION_CLASS=greeter XDG_SEAT=seat0 XDG_VTNR=8
ExecStart=/usr/lib/kidux/greeter-session --lock %i
KillMode=mixed
TimeoutStopSec=5
```

Terminal 8 holds one lock screen at a time, and a lock screen told to stop
while it is still starting can let the signal pass, as when greetd restarts
the instant the power button is pressed. systemd then kills it after five
seconds, rather than the default ninety, during which the next child's lock
screen would be refused and that child left with a frozen session and no
screen to continue from.

`PAMName=` makes systemd open a PAM session, and `pam_systemd` in it registers
a logind session for `_greetd` on VT 8 — the same mechanism `cage`'s own
documentation gives for running it as a service, and the same one greetd uses
for the greeter. `/etc/pam.d/kidux-locker` is:

```
account  required  pam_permit.so
session  required  pam_systemd.so
```

systemd never runs the `auth` part of a `PAMName=` stack, so this is complete.
It is not `login`: the `login` stack carries `pam_nologin`, `pam_securetty` and
`pam_faildelay`, none of which mean anything for a fixed system user starting
a screen.

`/usr/lib/kidux/greeter-session --lock <username>` is the wrapper of section
2 with one difference: the language is the child's (`Children1.List`),
because it is the child who is sitting in front of the lock screen. The
keyboard stays the machine's (D29) and the scale is the machine's.

## 5. Idle

A screen left alone (D67). `session-inner` starts `/usr/lib/kidux/kidux-idle
watch` beside every screen it runs: the sign-in and lock screens under
`cage`, and a child's session under `labwc`. `kidux-idle` runs `swayidle`
(`cage` and `labwc` implement `idle-notify`) with the minutes the screen was
given: a child's session gets `KIDUX_IDLE_LOCK_SECONDS` and
`KIDUX_SCREEN_OFF_SECONDS` from the greeter (`flow.py`), from the machine's
`idle_lock_minutes` (five until an adult chooses) and `screen_off_minutes`
(ten), which the panel's System page sets; a trusted screen gets the
screen's minutes from `greeter-session` and no lock, having no session to
lock; and, for every screen, `KIDUX_IDLE_SLEEP_SECONDS`, the machine's
`idle_sleep_minutes` (twenty), or 0 when the adult chose the screen off
only (D119, power.md section 4). After the first, `kidux-idle lock` asks the daemon to lock the child's
session, `Access1.LockFor("idle")`, as the child: the same lock as the Lock
button, so the counter stops (D13). After the second, `kidux-idle screen
off` turns every output off through the compositor, `wlopm` under `labwc`,
which has output power management, and `wlr-randr --off` under `cage`,
which has not, and the keyboard's light after them; the first touch runs
`kidux-idle screen on`, which gives the light back first, as it was. The
screen's brightness is left alone, so a desktop's screen turns off as a
laptop's does. After the third, `kidux-idle sleep` asks the daemon,
`System1.SleepWhenIdle`, to put the computer to sleep, or to sleep and then
turn off saving, as the adult chose and the computer can, unless an idle
inhibitor is held (power.md section 4).

`kidux-idle` counts only while its screen's terminal is the one in front:
it reads its own from `XDG_VTNR`, which greetd and the lock screen's unit
give their sessions, and the one in front from
`/sys/class/tty/tty0/active`, every two seconds (`kidux.idle.step`). While
another terminal is in front it stops `swayidle`; when its own comes back,
or when two looks are more than ten seconds apart, which is a process that
was frozen under the lock screen, it turns the screen on and starts
`swayidle` afresh. So a child's session counts nothing under the lock
screen, and a timer that ran out while it was frozen never fires as it
thaws; the daemon refuses a lock for idleness in the ten seconds after a
session is given the screen back, in case one does. Its log is the
journal's `kidux-idle`: `swayidle started (tty7, lock 300 s, screen off
600 s, sleep 1200 s)`, `swayidle stopped: tty8 is in front`, `screen off (tty8)`,
`screen on (tty8)`, `lock: asked (tty7)`.

The screen's brightness and the keyboard's light are the laptop keys' and
the corner's (keys.md): `brightnessctl` in trixie writes `/sys` itself,
without logind, and its own udev rule gives a backlight to group `video`
and a light to group `input`; `video` is what `kidux-daemon` gives every
child and `kidux-session`'s `postinst` gives `_greetd`, and
`91-kidux-keyboard-light.rules` gives a keyboard's light to `video` as
well, since `input` reads every keyboard and no child is in it. The
`postinst` triggers the lights as it triggers the switches, so an upgrade
takes effect without a restart; `postrm` takes `_greetd` out of `video`
again.

The keyboard's light goes off with the screen, for the lid or for being
left alone, and comes back as it was (D97): `kidux.hardware`'s
`keyboard_light_off` remembers its level, in the light's own steps, and
sets it to 0, and `keyboard_light_back` sets the level remembered and
forgets it. A level already remembered is kept, since the screen may go
off for both reasons at once, and a light already off stays off. It is
remembered in `/run/kidux-light/keyboard`, a directory
`kidux-session`'s `tmpfiles.d` makes, root's, group `video`, mode 2770,
so that a child's session and the trusted screens share it: a lid closed
in a child's session is opened on the lock screen, which finds the level
there and gives it back. Where it cannot be remembered, the light is left
on rather than turned off for good.

The lid (D61, D67): in a child's session, closing it locks the session,
`Access1.LockFor("lid")`, and powers the laptop's own panel off; opening it
powers it on, and shows the lock screen. `wlopm` asks labwc's output power
management; the launcher does it (launcher.md section 5),
reading the lid switch that `70-kidux-switches.rules` makes readable to
anyone (`ID_INPUT_SWITCH` devices, mode 0644: a switch's state gives away
nothing). The rule applies to a device as udev sees it, so
`kidux-session`'s `postinst` reloads udev's rules and triggers the input
devices: an upgrade takes effect without a restart. The keyboard's light
goes off after the panel and comes back before it, as above; the screen's
brightness is untouched; with the lid closed, `kidux-idle screen on`
leaves the laptop's own panel and the light off. Whether the computer
then sleeps is logind's, as the adult set it (power.md section 3); before
it sleeps the daemon locks the session, if the launcher has not already.

On the trusted screens, under `cage`, no launcher watches the lid:
`session-inner` starts `/usr/lib/kidux/kidux-lid-watch` beside the sign-in
or lock screen, which reads the same switch through `kidux.hardware` and
turns the laptop's own panel off with `wlr-randr --output <panel> --off`
while the lid is closed, and `--on` when it opens (`cage` implements
output management, not output power management), with the keyboard's
light as in a child's session. It ends with the screen
it was started for, when its parent, the screen's process, is gone, and on
a machine without a lid it says so in the journal (`kidux-lid-watch`) and
ends at once; a switch that can no longer be read is logged and left, and
the others go on being watched. The lock screen is where it matters most:
a laptop shut for the night with a child locked out.

## 6. The doors, one by one

Every item is a packaged file, so that `apt purge kidux-session` removes it
and the machine is a Debian machine again. Nothing here is done by a
`postinst` writing into a file it does not own.

| Door | Closed by | What it would have let a child do |
|---|---|---|
| Extra virtual terminals | `logind.conf.d`: `NAutoVTs=0`, `ReserveVT=0`; `getty@.service.d/kidux.conf` makes every text login on a virtual terminal conditional on `kidux.console` being on the kernel command line | Ctrl+Alt+F2 to a login prompt. There is no shell to log into, but a login prompt on a kiosk is a door with the lock removed. `kidux.console`, added from the GRUB menu with the recovery password, is the documented way back; the serial console is a different unit and is unaffected. |
| Ctrl+Alt+Delete | `ctrl-alt-del.target` masked with a `/dev/null` symlink in `/etc/systemd/system/` | Reboot from the keyboard, ending the session and everything unsaved in it — and, on a machine without a firmware password, a way to reach GRUB. |
| SysRq | `sysctl.d`: `kernel.sysrq = 0` | Alt+SysRq+B reboots without asking anything; Alt+SysRq+K kills the session. |
| Outliving the session | `logind.conf.d`: `KillUserProcesses=yes` (trixie default `no`) | A script started before logging out keeps running, and keeps counting for nothing — or keeps a listening socket open for the next session. |
| Watching other processes | `sysctl.d`: `kernel.yama.ptrace_scope = 2` (trixie default `0`) | One of the child's processes attaches to another — the launcher, a module — and reads or drives it. Phase 6 gives children arbitrary code on purpose. |
| Power key | `logind.conf.d`: `HandlePowerKey=ignore`, `HandlePowerKeyLongPress=ignore` | logind powers off before the daemon can put the trusted screen up (`daemon.md` section 11). |
| Sleeping out of a time limit | `logind.conf.d`: `InhibitDelayMaxSec=15`, for the daemon's delay lock on sleep, which locks a child's session before the computer sleeps for any reason; the lid itself is the daemon's drop-in in `/etc`, as the adult sets it (power.md) | A child closes the lid, or presses a sleep key, and the session sleeps unlocked, counting nothing and open again at once on waking. |
| Switching back from the lock screen | `40-kidux-children.rules`: `org.freedesktop.login1.chvt` → `NO` for `kidux-children` | trixie's default lets an inactive session switch VTs; a child's frozen session, once thawed for a moment, could switch itself back. `/dev/tty*` is already root-only, so this is the only path, and it is closed. |
| Ctrl+Alt+F*n* inside a child's session | The same `chvt` rule: `labwc` has these keys built in, and asks logind, which refuses the child | Leaving the session for a text login, or for terminal 8 while the lock screen is down. |
| A terminal, a menu, a key that runs a program | labwc's configuration binds Super, Alt+Tab and Alt+F4 (Alt+Tab, Alt+F4, and Super on the desk, signal the launcher) and the laptop's keys for its screen, keyboard light and sound, which run `kidux-keys` as the child, a program that only sets those three levels (D61), and nothing else, loads none of labwc's own keys or mouse bindings, shows no menu, and is root's, read from a directory the child cannot write (`-C`); its `rc.xml` with the pointer's part (section 3) is written afresh at every start in a new directory of the session's, so nothing the child leaves there is ever read at a start, and labwc reads it again only on a signal, which takes a program of the child's that can already run whatever a key could; `kidux-session` conflicts with `foot`, `wmenu` and every `x-terminal-emulator` | The shell a desktop hands anyone who presses the right keys. |
| X11, where a program reads every key and sees every window of the others | XWayland is on (D58): it runs as the child, one per session, started by labwc without a cookie, so it takes any local connection; the only other users on the machine are root and the sign-in screen's, and one child's session runs at a time, so its clients are the child's own X11 programs. They see one another's keys and windows, as on every Linux desktop, and nothing of the Wayland programs, the launcher, the lock screen, another child or the adult. That is within D42: no sandbox between one child's modules. The adult password is never typed in a child's session (D6) | One X11 module of the child's reading what the child types into another X11 module of theirs. |
| The foreign-toplevel protocol, which lists and drives every window | Nothing: any program of the child's may use it, as the launcher does (launcher.md section 5), and what it can do, activate, minimise, maximise, close a window, the child can do with the frame and the keys (D17) | A program of the child's moving or closing the child's other windows. |
| GTK's inspector | `90_kidux.gschema.override` in `/usr/share/glib-2.0/schemas`, which GLib's trigger compiles in: `enable-inspector-keybinding` false for GTK 4, whose default is true, and for GTK 3 | Ctrl+Shift+I or Ctrl+Shift+D on the lock screen, the panel or the launcher opens a window that reads and changes every widget of the program, and swallows the keys typed after it. |
| A theme of the child's changing the frame | The colours are a `themerc-override` in the configuration's own directory, root's | Nothing that matters: the look of a title bar. |
| Everything else through polkit | The same rules file: for `kidux-children`, `YES` for `login1.power-off`, `login1.reboot`, `udisks2.filesystem-mount` on removable media; `NO` for any other action | Mounting fixed disks, changing the clock (`timedate1.set-time`), inhibiting shutdown, managing units. The micro:bit is a removable drive, hence the exception. |
| Group `video` | Nothing: every child is in it (`accounts.CHILD_GROUPS`), and `_greetd` too, since `brightnessctl` writes the backlight's and the keyboard light's `brightness` files itself and Debian's rules give them to `video` (section 5, D61) | Reading and writing the console's framebuffer, `/dev/fb0`, which shows nothing while a compositor draws; opening the DRM card nodes, `/dev/dri/card*`, as a client that is not the compositor, which is no more than the `render` node every program draws with; and, on a machine with a webcam, `/dev/video*`, the camera. A module that must not see the camera does not exist yet; when one matters, the two `brightness` files go to a group of Kidux's own and the children leave `video`. |
| SSH | `sshd_config.d`: `DenyGroups kidux-children` | A child with Python and a network. |
| Sudo | Nothing to close: the daemon never adds a child to `sudo`. | |
| Shell | Nothing to close: children are created with `/usr/sbin/nologin`, and `login` has no `pam_shells`, so the graphical session still starts. | |
| GRUB | Section 7 | Editing the boot line to `init=/bin/bash` is root without a password. |

Two things this package **never** touches:

- **SSH for anyone not in `kidux-children`.** It is the recovery path on
  every machine and the maintenance path on the development one.
- **greetd's process.** No `postinst` here restarts greetd, because that kills
  whatever session it is running. Configuration changes take effect at the
  next boot, and the install guide says so.

## 7. GRUB

The trap: setting `superusers` protects *every* entry, including the one the
machine boots by itself, and trixie's `/etc/grub.d/10_linux` never marks an
entry `--unrestricted`. A machine hardened that way asks for a password to
boot at all.

So `kidux-session` ships its own entry (D25):

- `/etc/default/grub.d/90-kidux.cfg`: `GRUB_DEFAULT=kidux`,
  `GRUB_TIMEOUT=1`, `GRUB_TIMEOUT_STYLE=hidden`, `GRUB_DISABLE_OS_PROBER=true`,
  and `quiet splash plymouth.ignore-serial-consoles loglevel=3 systemd.show_status=false
  vt.global_cursor_default=0`
  *appended* to `GRUB_CMDLINE_LINUX_DEFAULT`, so a machine's own settings — a
  serial console, say — survive. One invisible second, not zero: with no
  window at all, Esc could never reach the menu and the recovery password
  would be unusable.
- `/etc/grub.d/09_kidux` emits, before Debian's entries:
  - `set superusers="kidux"` and `password_pbkdf2 kidux <hash>`, **only if**
    `/home/.kidux/adults.toml` holds `grub_password_hash`. Before first boot
    there is no password and nothing is protected, which is right: nothing is
    running yet either.
  - One `menuentry 'Kidux' --unrestricted --id kidux { ... }` booting the
    newest kernel in `/boot`, found the way `10_linux` finds it, with
    `kidux.boot` on its command line so a running machine can tell which
    entry started it. Kernel packages run `update-grub`, so the entry follows
    every kernel update. The root device, its UUID and the commands to reach
    it come from `grub-mkconfig_lib`, the helpers `10_linux` uses; the
    `/vmlinuz` symlinks are not relied on, because cloud and minimal installs
    do not always have them. Debian's `-cloud-` kernels are passed over
    whenever another kernel is installed: they have no display drivers, so
    they cannot show a sign-in screen, and beside a generic kernel of the same
    version they would otherwise win on version order.

Debian's own entries, generated by `10_linux` after ours, stay in the hidden
menu and stay **restricted**: choosing one, pressing `e` on ours, or Esc for
GRUB's shell, asks for the recovery password. That is precisely the split wanted: the kiosk boots by
itself; anything else needs the adult.

`kidux-firstboot` runs `update-grub` after writing the hash (`daemon.md`
section 12), and `kidux-session.postinst` runs it too, so whichever is
installed second completes the picture. The assumption written into this: no
separate `/boot` partition, which is what the architecture's disk layout says.

The recovery password is what an adult reads off the panel when the machine
will not come up: Escape during the first second for the menu, the user name
`kidux` and the password, then one of Debian's entries, or `e` on the Kidux
entry and `kidux.console`, `init=/bin/bash` or `systemd.unit=rescue.target`.
The user guide, section 11, has the words; this document has the
mechanism.

### The boot splash

While the machine starts, Plymouth shows Kidux's logo centred on cream,
the colour of every Kidux screen, and nothing else. The theme is
`/usr/share/plymouth/themes/kidux/`: `kidux.plymouth`, a script that sizes
the logo to a quarter of the screen's height, and `logo.png`, the logo
rendered 512 pixels tall so that it is only ever scaled down.
`kidux-session.postinst` makes it the default theme and rebuilds the
initramfs, where Plymouth runs from; removing the package resets Debian's
default theme the same way. The package depends on `plymouth-label`, the
plugin that draws text (`label-pango.so`): the theme draws none, but
initramfs-tools' Plymouth hook copies that plugin for every theme but
Debian's own three, and warns at every kernel update when it is missing;
with it there, the initramfs holds it and the hook is quiet. `splash` on
the kernel command line turns the splash on.
Plymouth draws only text while any serial console is on the command line,
so the Kidux entry also carries `plymouth.ignore-serial-consoles`: the logo
belongs on the screen, and a serial console keeps the kernel's own messages.

## 8. Testing

Everything in a VM with a real screen, before and instead of the development
machine (D4): `tests/run session`, driven from outside the machine, because
what it tests only exists after a reboot and can only be tried with keys
pressed on the machine's own keyboard. The scenarios are the files in
`tests/session/`, one per scenario, run in order on one machine;
`tests/lib/sessionlib.py` is how they drive it (`tests/README.md`).

The machine gets a disk of its own for the length of the run (an overlay on
the base image, deleted afterwards), an SSH key for the administrator, and a
QEMU monitor through which the script types (`sendkey`, one key at a time),
presses the power button (`system_powerdown`, which is what the ACPI button
sends) and takes pictures of the screen. `sendkey` presses its keys
together and lets them all go at the next command, so a key held down
while others are pressed, Alt through Alt+Tab's round, is typed on a
keyboard of the machine's own instead: `tests/lib/keyboard.py`, run as
root through uinput, which the compositor takes for a real one
(`sessionlib.keyboard`). The pictures are left in
`build/vm/session-NN-<screen>.png`, numbered in the order they are taken, to
be looked at.

The run sets the machine up in Spanish. `tests/run session-en`
(`KIDUX_VM_LANGUAGE=en`) sets it up in English instead, with a disk, ports
and pictures of its own (`build/vm/session-en-NN-<screen>.png`), so the
battery runs both at once: every screen is tested, and photographed for the
user guide and the README, in both languages. What a test expects that
depends on the language, the locale, the keyboard, a module's words, is in
`sessionlib.LANGUAGES`.

Every screen is the real one, used the way a child or an adult uses it:
Enter on what has the focus, the arrows between pictures, Escape for Back,
passwords typed key by key.

The run: install `kidux-base`, which brings `kidux-session`, `kidux-greeter`
and `kidux-launcher`, reboot, and then —

1. the Kidux entry booted, with the quiet command line, into the sign-in
   screen on terminal 7;
2. the first-run wizard, by keyboard, in Spanish: language, keyboard (the
   screen restarts in it), the adult password, the first child with their
   picture, password and access; the machine is set up, and that child signs
   in with the password the wizard gave them;
3. two more children are added from the command line; the power button,
   with nobody signed in, asks before turning anything off;
4. Ctrl+Alt+F2 leaves terminal 7 where it is, and Alt+SysRq+B leaves the
   machine running; sysctl, logind's settings, the absent getty and the
   masked Ctrl+Alt+Delete are what section 6 says; a child is denied by
   `sshd -T`, the administrator is still logged in;
5. polkit, asked about one of the child's own processes: power off and
   reboot allowed, `chvt`, setting the clock and managing units refused;
6. a child added while the sign-in screen is up appears on it at once;
7. with the child's day spent, the sign-in screen says so and starts nothing;
   an adult types the adult password there, picks fifteen minutes, and the
   session starts with fifteen minutes;
8. a wrong password signs nobody in; the right one starts the child's
   session on terminal 7 under `labwc` with the environment the greeter
   sent, the launcher's bar along the bottom and the child's usual folders
   in their home; the daemon counts it; the power button locks it onto terminal 8 and freezes it; the
   child types their password on the lock screen and the same session
   carries on; the launcher is on screen although the child's `~/.profile`
   says otherwise; its Lock button locks and the child continues into the
   same launcher; it survives the daemon restarting under it, and is started
   again, in the same session, when it is killed; Ctrl+Alt+Escape locks too; the adult opens the panel from
   the lock screen, closes it, and gives time, and the session carries on;
   greetd restarting under a locked session takes the lock screen down with
   it, and the sign-in screen that comes back has the keyboard; logging out
   from the launcher asks once and leaves nothing of theirs running;
9. a child with one minute a day signs in, and the lock screen comes up by
   itself when the minute is spent; the adult's time unlocks it; *Unlock to
   save work* gives the screen back without charging for it and locks again
   when the minutes are over;
10. with the daemon masked and stopped, signing in shows the waiting screen,
    and the pictures come back by themselves when the daemon returns; a
    minute without a touch on a child's screen returns to everyone's
    pictures;
11. updates from the panel, by keyboard, with nobody signed in: *Look for
    updates* finds the one a local repository in the machine offers, and
    *Install* puts it in place (daemon.md section 13);
12. every screen shown so far, which is every screen of the greeter, fits
    the machine's 1280x800 whole: the greeter logged none that had to scroll;
13. GRUB: the configuration has the password stanza and a single unrestricted
    entry; at the boot menu both Esc (GRUB's shell) and `e` stop at "Enter
    username:"; a reset with nobody at the keyboard boots straight through,
    showing Kidux's logo while it starts;
14. learning modules (modules.md, launcher.md, panel.md): the tests'
    stand-in module switched on for a child from the panel and off again
    over the lock screen, its tile coming and going on the child's launcher,
    and sound through PipeWire in the child's session; two stand-in modules
    open at once, each filling the room above the launcher's bar and
    getting the click made over it, the launcher saying what the machine
    has (nothing of a laptop's, no Mac) and how it writes the keys (Win,
    Alt+F4, Alt+Tab), Super home and Alt+Tab round the modules in the bar's order, never
    home, nowhere with one module on screen, Alt held down going round with
    the bar lit at each step and let go going there, Alt+Shift+Tab back, the lock leaving
    them where they were and a launcher crash bringing home back with both
    in its bar, Alt+F4 closing the one that goes when asked and, for
    the one that refuses, the bar asking and Alt+F4 again ending it,
    logging out ending them; `kidux-module-hello` installed
    from the panel's Modules page by keyboard, opened by the child in
    Spanish and closed with *Done*, its tile gone when it is purged, and
    removed from the panel, which offers it again; GCompris installed,
    opened by the child on its menu, in Spanish and with sound, above the
    bar, the lock and continuing, and logging out ending it; the
    reference web application, in Chromium above the bar, its link
    to the internet refused by the policy, the lock and continuing,
    *Done*, Alt+F4 closing it after the link, and logging out ending it;
15. the display scale (D49, D53): set to 2 through the daemon, the sign-in
    screen under `cage` and a child's launcher under `labwc` both have
    640x400 logical pixels; 1.25 gives 1024x640; automatic, on the test
    machine's 1280x800, 1280x800;
16. windows (D46, D57): a child with windows gets labwc's desk
    configuration, modules in labwc's frame, the one that comes up
    fullscreen opened as a window; Super shows the desk, and a tile brings
    the windows back with the new one over them, both in view; minimised,
    brought back, maximised and getting the click made over it; fullscreen asked for afterwards kept, Super
    and Alt+F4 as ever; without windows, a module that needs them has
    no tile and the canary fills the room above the bar;
17. a module made for X11 (D58): the tests' Tk stand-in opens through
    XWayland, which runs as the child, fills the room above the bar, gets
    the click made over it, comes back after the lock, closes on Alt+F4,
    XWayland ending by itself after it, and nothing of either is left after
    logging out;
18. the adult panel's Network page (D62), on a simulated Wi-Fi with a
    password: a wrong password said and not kept, the right one joining
    the network in a connection file of root's, and Forget; then the same
    radio run as the Debian installer leaves a Wi-Fi, which the page
    names within five seconds;
19. `apt purge kidux-session`, reboot, and Ctrl+Alt+F2 reaches a login
    prompt: the machine is Debian again.

Each step is a `PASS`/`FAIL` line and the whole thing is one command.

On the development machine, which is also where its owner works over SSH,
`KillUserProcesses=yes` would end a `tmux` session at logout. logind can
exclude users by name only, so the machine gets a local drop-in in
`/etc/systemd/logind.conf.d/` naming its administrator in `KillExcludeUsers=`
when Kidux is rolled out on it (plan step 9.11). A family machine needs no such
thing.
