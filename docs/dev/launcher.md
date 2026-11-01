# kidux-launcher

The launcher is the child's screen once they are signed in: the first thing
their session runs and what starts everything else in it, the modules
included, and the bar along the bottom of the screen that takes the child
between them (session.md, section 3). It runs **as the child**, so nothing in
it is trusted: it shows what the daemon says, asks the
daemon for the two things a child may ask for — their own time and a lock —
and never sees the adult password (D6, D17).

This document fixes the behaviour. How it looks follows the sign-in screen
(greeter.md, section 8); what is specific to the launcher is in section 8
here.

## 1. Shape

Its own source package, `kidux-launcher`, which `kidux-session` depends on as
it depends on `kidux-greeter`. The same split as the greeter:

```
kidux_launcher/
  model.py      what the screen says: time left, warnings; no GTK
  daemon.py     Usage, Lock, Modules1.List and the signals, behind a protocol
  launch.py     the command a module is started with
  compositor.py the compositor, through the foreign-toplevel protocol
  desk.py       whose each window is, and what is on screen; no GTK
  view.py       GTK 4 + libadwaita: the launcher's page
  bar.py        GTK 4: the bar along the bottom
  words.py      the sentences only the launcher says
  main.py       wiring
```

The manifests are read by `kidux.modules`, the one reader the daemon and the
panel use too (D34).

`/usr/libexec/kidux-launcher`, started by `session-inner` inside `labwc` with
the child's environment: `LANG`, `LC_ALL`, `XKB_DEFAULT_LAYOUT`,
`KIDUX_DISPLAY_SCALE` and `KIDUX_AVATAR` (D24), all from the sign-in screen,
because a child cannot read the family's state. Their name is the one on
their own account, which the daemon sets from their display name; the user
it runs as is who they are.

## 2. The screen

- **Top:** the child's picture and name on the left, the clock in the middle,
  the time left on the right when the child's mode has a limit — an
  hourglass and the time as a clock reads it, `00:51` (`Model.time_clock`,
  `timeleft.py`), with the sentence, "51 minutes left", on hover and in a
  popover on a tap (D64), and nothing at all for a child with no limit
  rather than a meaningless "∞".
  After it, the corner (D61, `kidux.corner` in kidux-common, which the
  greeter draws too): what the machine has and nothing it has not. The
  sound's volume, the keyboard's light and the screen's brightness, each
  a button with its icon and its percentage that opens a vertical slider,
  the sound's with a *Mute* toggle under it; and the battery, its icon
  and its charge, charging or not. Read from `/sys` and `wpctl` by
  `kidux.hardware` every five seconds, after a slider moves, and at once
  when a key has changed a level: `hardware.key` touches
  `$XDG_RUNTIME_DIR/kidux/levels`, which the corner watches
  (`Gio.FileMonitor`, read once the keys settle for 200 ms). A slider's
  label follows it as it moves, and a slider open under the child's hand
  is not read back while it is. On a screen narrower than 1200 logical
  pixels (`kidux.screen.compact_corner`) the corner is compact, its icons
  without their percentages, and the child's name is cut to 24 characters
  with an ellipsis, so that the clock between them keeps its room. Set
  through `brightnessctl`, which needs
  group `video` (session.md section 5), and `wpctl`; a failure of either
  is in the journal as `kidux.hardware`'s warning, with what the program
  said. On the test machine, a desktop with no sound device, the
  corner is empty, and the launcher's log says so: `hardware: battery=none
  backlight=none keyboard=none lid=no mac=no fn=no audio=no`.
- **Middle:** the tiles of the modules enabled for this child
  (section 5). With none, the middle says so kindly, next to the mascot:
  *There is nothing here yet. An adult can add things to do.*
- **Bottom:** *Lock* on the left (D13), *Log out* and *Turn off* on the
  right, and Kidux's logo small in the middle, as on the sign-in screen.

**Notices** (`bubbles.py`, `notices.py`, D98): a module tells the child
something through the desktop's notifications, freedesktop.org's *Desktop
Notifications*, as Thunderbird does when a server does not answer. The
launcher owns `org.freedesktop.Notifications` on the child's session bus
and draws each notice as a bubble rising from the bar, above its right
end, on gtk4-layer-shell's overlay layer (anchored to the bottom and the
right, its margin the bar's height, its exclusive zone -1 so that it
stands where it is told), over every module and taking no keyboard; the
newest is nearest the bar. A bubble says who it is from: the module's
name and tile when the sender runs in a module's scope (its cgroup's
`kidux-module-<id>.scope`), the program's own name otherwise. Then the
notice's summary and its text, plain; a close button; the program's
actions as buttons, with its own words; and a click on the bubble does
its default action, when it has one. A notice goes after eight seconds,
or stays until it is closed when its program marks it urgent or never
expiring. The server answers `GetCapabilities` with `body` and `actions`,
and nothing about sound: a notice is never heard. The journal says each
notice's number, who it is from and why it closed (`notice 1 from mail`,
`notice 1 closed (1)`), never its words, which may be a child's mail. The
launcher's own notices, the time warnings of section 3, go the same way
(`Bubbles.tell`): from Kidux, with the mascot, staying until closed. The
bar's bell, at its right end, keeps the last twenty notices that came,
gone or not (`notices.HISTORY`), the newest first with the time each came,
in a popover above the bell; a count beside the bell says how many came
since the child last opened it, and *Clear* empties it. The launcher logs
`notices: the bell opened, N kept`. The
sign-in and lock screens run no launcher, so a bubble is never on them,
and under the lock the launcher is frozen with the session. A program
reaches the desktop's notifications through libnotify, which some load
only when it is there, as Thunderbird does: the module that runs one
depends on `libnotify4`. A website never notifies: Chromium's policy
blocks it (D36).

**Lock** calls `Access1.Lock()`. The daemon puts the trusted lock screen up
and freezes the session; the launcher does nothing else and has nothing to
draw while it is frozen.

**Log out** asks once — *Have you saved your work?* with *Log out* and
*Cancel* — and then the launcher exits with status 0. `session-inner` treats
that as the end of the session (section 4), tells `labwc` to exit, and greetd
shows the sign-in screen; every module ends with the session. No password:
the child is ending their own session.

**Turn off** also calls `Access1.Lock()`: the lock screen, which is
trusted, has the real *Turn off* (D16), exactly as the physical power button
brings it up.

## 3. Time

`Access1.Usage(username)` gives the seconds left, or −1 for no limit. The
launcher asks when it starts, every 30 seconds, and after every signal, and
counts down by itself in between, so the number moves every minute without
asking the daemon every minute. The daemon, not the launcher, decides when
time is up; the launcher never locks on its own count.

**Warnings.** `TimeWarning(username, seconds_left)` at ten, five and one
minute (`WARNINGS` in the daemon's `access.py`) is a bubble of Kidux's
own, rising from the bar as a module's notices do (section 2, D98): *5
minutes left. Save your work.*, from Kidux with the mascot, which stays
until the child closes it, each warning in place of the one before, and
kept in the bar's bell. The bar shows the time left and nothing else of
it. A bubble never steals the keyboard from a module.

**Locked and unlocked.** `Locked` and `Unlocked` for this child only refresh
the time. The session is frozen between them; nothing the launcher does
could run anyway.

**The daemon restarting.** The calls go through `kidux.client.Client`, which
raises `DaemonUnavailableError` while the daemon is away. The launcher keeps
its last figures, stops counting down, shows nothing alarming, and asks again
every few seconds until the daemon answers. Signals are subscribed on the
bus name, not on a connection to the daemon, so they arrive again by
themselves once it is back.

## 4. Never an empty screen

Without the launcher there is no way to open anything, and no bar: if it
dies, the child is looking at a module with no way home, or at the cream
background `session-inner` puts behind every window. So `session-inner` runs it in a loop:

- exit status 0 is *Log out*: the loop ends, `labwc --exit` ends `labwc`, and
  the session ends with it;
- anything else is a crash: logged, and the launcher started again after a
  second, up to five times in a minute; after that, the session ends, which
  brings back the sign-in screen rather than an empty one.

The rule is the greeter's, turned round: the greeter must never crash-loop
because greetd would restart it forever; the launcher must never simply
vanish, because nothing would.

## 5. Modules

**The tiles.** `Modules1.List(username)` says which modules are enabled for
the child; `kidux.modules.read` reads each one's manifest, and a module
whose manifest no longer reads gets no tile. The tiles are a `Gtk.FlowBox`
in the scrolling middle, homogeneous, six to a row at 1280 pixels and more
rows scrolling, which the middle shows (`kidux.scroll`, D63): a scrollbar
drawn for as long as there is more, a shade along the edge that has more,
and `the child's screen does not fit: <n> pixels tall` in the log, judged
once labwc has maximised the window, since before that its room is its
own natural size. Each is one `Gtk.FlowBoxChild`: the module's `icon.svg`
drawn with librsvg at 128 pixels, as the mascot is, or the mascot when the
module has none, over its name in the child's language
(`kidux.modules.name_in` with `LANG`). Tab reaches the tiles as one stop,
the arrows move between them, and Enter, a tap or a click activates one; the
tile's handler, `_open`, is the one place a module is started from. The
launcher logs `tiles:` and the ids each time the tiles change, `none` when
they go.

`ModulesChanged` for this child, `Unlocked`, and the question every 30
seconds all ask `List` again, so a module an adult switches on or off shows
or goes while the launcher is open, and a change made while the session was
locked is there when it continues.

**Opening one.** `launch.command(module, home)` makes the argv, a pure
function whose test is the specification (D32, D42):

```
systemd-run --user --scope --quiet --collect --unit=kidux-module-<id>
    --property=MemoryMax=<memory_max>
    --setenv=XDG_DATA_HOME=<home>/.local/share/kidux/<id>
    --setenv=XDG_CONFIG_HOME=<home>/.config/kidux/<id>
    --setenv=XDG_CACHE_HOME=<home>/.cache/kidux/<id> --
systemd-cat --identifier=kidux-module-<id>
<exec, split as a shell would, never run through one>
```

The scope, under the child's user manager, is what ends a module, caps its
memory, is frozen with the session under the lock screen (D40) and keeps
the module running if the launcher crashes; with `--scope`, `systemd-run`
runs the program itself, so the launcher's `Gio.Subprocess` is the module
and its end is the module's; `systemd-cat` gives the module the journal as
its standard output and error and runs it in its own place, so that what
it writes is in the journal as `kidux-module-<id>` (`journalctl -t
kidux-module-codecombat`), where the session's own, the console of the
terminal labwc draws on, would show it to nobody; the layer-shell library the launcher itself
runs with (below) is taken out of the module's environment. There is no sandbox: a module sees what any
program of the child's user sees, the child's home above all, where the
files a child makes in one module are there for every other (D42). What is
the module's own is its settings, its data and its cache, in three
directories under the child's home that the launcher makes, mode 0700,
before the first start and hands it as the XDG variables, so that they are
its alone; removing the module leaves them in the child's home (D89). A
web application (`launch = {
webapp = "<id>" }`) or a website (`launch = { web = "https://…" }`) is
started the same way, in its scope: the program is `/usr/libexec/kidux-webapp
<module id>`, from `kidux-webapps`, which reads the module's manifest and
opens a Chromium application window (`--app`), with no tabs and no address
bar, on the application `kidux-webapps` serves on `127.0.0.1:8123` or on
the website, walled in to the module's own hosts and held by Chromium's
managed policy (D36, D44, D85); a web application's name is checked before
it goes into the command.

The launcher reads the manifest again when a tile is activated, so a module
apt replaced since the tiles were drawn starts as its new manifest says,
and logs the command. A module that ends with a status other than 0 within
two seconds did not open: the launcher comes back to the screen with *That
did not open. An adult can look at it.* above the tiles, and the log says
the command and the status. Otherwise the launcher logs `module <id> ended`.

**Several at once: the desk.** The child's session runs `labwc` (D58),
which draws and places the windows as Kidux's configuration says
(session.md section 3); the launcher knows them, and drives them, through
`wlr-foreign-toplevel-management-unstable-v1`, the protocol taskbars use
(`compositor.py`, on `python3-pywayland` 0.4.18, whose Python for the
protocol is made from its XML when the package is built,
`protocol/generate.py`). It gives every window's `app_id`, title, states
(maximised, minimised, active, fullscreen) and, for a dialog, its parent,
and takes `activate`, `set_minimized`, `set_maximized`, `unset_fullscreen`
and `close`. Its events are read in GLib's main loop when the compositor's
socket has something (`GLib.unix_fd_add_full`): no thread, so the requests
the desk makes and the events it reads never meet halfway. `desk.py` is
the policy, with no GTK in it, so its test is the specification:

- The launcher's own window, `org.kidux.Launcher`, maximised under every
  other, is home.
- A window is of the module whose manifest claims its `app_id`
  (`kidux.modules.claims`: `app_ids` in the manifest, globs, and for a web
  application Chromium's name for its window, `chrome-127.0.0.1__<id>_-*`,
  added by the reader, modules.md section 1); a dialog is of its parent's
  module; a window no manifest claims is of the module started from a
  tile whose first window has not come yet, the oldest when there are
  several; any other is a stranger, logged once and left alone. The
  protocol says nothing of a window's process, which is why the manifest
  names its windows.
- The module on screen is the one whose window is active; home when the
  launcher's is. A tile of a module that is open brings its window forward
  (the one last active, or its first) and starts nothing; a tile of one
  that is not starts it, and its first window is brought forward when it
  comes. The tiles stay usable while modules are open.
- A module whose last window closes leaves the bar (`module <id> closed`
  in the log when it had been asked to), and when it was on screen, the
  launcher's window is brought forward rather than whichever window the
  compositor would put there.
- **The kiosk**, for a child without windows: labwc's rule makes every main
  window fill the room above the bar, without a frame, and leaves a dialog
  floating over its window. The desk also takes fullscreen back, so that
  the bar stays reachable, and maximises again a main window that is not,
  as one that came up fullscreen is at its own size once out of it (with a
  title bar, which labwc 0.8 gives it back: labwc-notes.md).
- **Windows** (D46), for a child with them (`KIDUX_WINDOWS=1`, which the
  sign-in screen sets from the child's profile, and which also gives the
  session labwc's desk configuration): every window in labwc's frame, to
  move it by its title, resize it by its edges, iconify, maximise and close
  it by its buttons, placed in cascade; several modules' windows in view
  at once over the launcher's window, which labwc keeps under every other
  (D57). Home, on the bar or Super, shows the desk: every module's main
  window minimised and the launcher's in use. Leaving it by a tile or a
  window's button on the bar brings back every window home put away, the
  one asked for in front; one the child minimised stays so. labwc places a
  new window as if the minimised ones were not there, so without that a
  module opened from home would come up exactly over the one before. One
  that comes up fullscreen is
  taken out of it once; fullscreen asked for afterwards
  is the child's, the bar under it, and Super and Alt+Tab still bring the
  launcher and the other windows back. A module whose manifest says
  `needs_windows` gets no tile for a child without windows (modules.md
  section 2).
- **Closing** (D45). *Close*, on the bar or Alt+F4 (labwc's
  `Execute pkill -USR2 -f "^/usr/bin/python3 /usr/libexec/kidux-launcher"`,
  which the launcher hears through `GLib.unix_signal_add`), asks the module on screen to close: each of its
  windows is sent the protocol's `close`, the `xdg_toplevel` close request
  a window's close button sends, so the program decides, and one with
  unsaved work can ask its own question. A module whose windows are all
  gone is closed. One still open `CLOSE_SECONDS` (10) later is overdue: the
  bar asks *<name> has not closed. It may have something to save.* with
  *Cancel*, which leaves it and forgets the request, and *Close it anyway*,
  which stops its scope (`launch.stop`, `systemctl --user stop
  kidux-module-<id>.scope`) and every process in it: SIGTERM, and SIGKILL
  five seconds later, the scope's `TimeoutStopSec`, since a program made
  with SDL 1.2, Tux Typing for one, turns SIGTERM into a quit it does not
  heed on every screen (D112). Close pressed again
  while the bar asks is the same as *Close it anyway*; pressed before the
  wait is over, it asks again. Nothing is ended without that question.
- `settle` reads every window each time and puts the desk in order, which
  is what makes a launcher started again after a crash find the modules
  still open. The launcher logs `toplevels:` with every window,
  `app_id=module:flags` (`a` active, `m` maximised, `i` minimised, `f`
  fullscreen, `d` a dialog), and `on screen:` with the module on screen,
  each time they change.

**The bar** (`bar.py`) is a second window of the launcher, a layer-shell
surface (`gtk4-layer-shell` 1.0) on the bottom edge, on the layer above
windows, with an exclusive zone of its own height, 56 logical pixels, which
`labwc` keeps free of maximised windows; it never takes the keyboard. In it: *Home*
(the mascot, small, and the word), then one button per open module, its
icon at 32 pixels and its name, in the order they were opened; the one on
screen is marked, *Home* when it is the launcher; and, at the far right
whatever is on screen, the bell of the notices (section 2), from which
the bubbles rise. While a module is on
screen it also shows, on the right, the time left as on the child's
screen, the hourglass and `00:51`, *Close* for the module on screen (a cross
and the word; a screen reader hears *Close <name>*), and *Lock*, since
that is what the child is looking at; on the launcher those are on its own
page already. While the bar asks about a module that has not closed, the
question and its two buttons take the place of the time and *Close*, and
of the other modules' buttons with their arrows, which step
aside until it is answered, on that module's screen: so *Lock* stays whole
on a 1280-pixel screen, which `16-module-open.py` checks. A module's
button brings its window forward, *Home* the launcher's. For a child with
windows (D57) the bar is the taskbar: one button per main window instead
of one per module, the module's icon and the window's title (the module's
name when it has none, cut to 24 characters, `desk.title_of`), the window in
use marked and a minimised one faded; a button brings its window forward,
back from minimised (`desk.raise_window`). The buttons, in the kiosk and
on the desk alike, take all the room between *Home* and the time left
(D64), and scroll past it rather than push *Close* and *Lock* off the
screen, and
show it (D63): while they do not all fit, an arrow either side, the one at
an end faded, each moving them along by most of what is shown, and a shade
along the edge that has more; the button of what is in use is brought into
view. The arrows and the button are set once GTK has laid the bar out (100
ms after it changes), since neither can be while it does, and the
launcher logs `strip: more than fit` or `strip: all fit` when that
changes. The
desk tells the bar of every change of a window's title or state. The launcher logs
`bar:` and the open modules' ids each time they change.

The layer-shell library has to be in the process before GTK connects to the
compositor, and loading it through GObject introspection comes too late: so
`main.py`, when `LD_PRELOAD` does not name `libgtk4-layer-shell.so.0`,
executes itself once more with it there, the same process and the same
command line. Without layer-shell, or without the compositor's
foreign-toplevel protocol, the launcher runs without its bar and says so
in the log.

The keyboard's way round: Super, pressed and let go alone, is home (on the
desk, a signal to the launcher, which shows the desk as the bar's Home
does); Alt+F4 is *Close* (session.md section 3); and Alt+Tab goes round
the bar (D64, D66). labwc sends the launcher a signal for Alt+Tab
(`SIGRTMIN+1`) and one for Alt+Shift+Tab (`SIGRTMIN+2`); each is a step
round the bar's buttons in the bar's order, frozen when the round begins
(`desk.switch`): for a child without windows each open module, its main
window last in use, for a child with windows each main window. Home is
not in the round, since Super goes home: from Home the first step is the
first button (Alt+Shift+Tab, the last), from a module the next to its
right, the last wrapping to the first; with one module open and on
screen there is nowhere to go, and the launcher logs `switch: nowhere`.
The bar lights the button of the one pointed at (`kidux-next`) and follows
the keyboard's state, which labwc sends every program whether it has the
keyboard or not, as it changes and every 150 ms, until Alt is let go,
which goes there (`desk.switch_done`); Alt never seen down is a quick
Alt+Tab, let go before the first look. So a quick Alt+Tab is the next
module in the bar, and held, each Tab a step further. The bar never takes the
keyboard: while a layer-shell window holds it, labwc brings no window
forward (labwc-notes.md). Tab held down repeats, a step every 120 ms at
most. The launcher logs `switch: <whose>` for each step and
`switched: <whose>` at the end, a module's id. The bar says the keys on
hover (D64): Home's tooltip the key that goes home and nothing else, `⌘`
on a Mac and `Win` elsewhere, Close's `Alt+F4`, written `Alt+(fn)F4` on
a Mac whose function keys are media keys first, and the button of the
module, or on the desk the window, that Alt+Tab would go to first
(`desk.next_in_bar`) says `Alt+Tab`; the launcher logs `alt-tab:`, that
module's id or `none`, when it changes. The words come
from `kidux.hardware`
(`super_key`, `function_key`), never from a literal, and keys.md says
how they are chosen. The laptop's own keys for the screen, the keyboard's
light and the sound are labwc's too, and run `kidux-keys` (keys.md).

**The lid** (`lid.py`): on a laptop, the launcher reads the lid switch,
readable by anyone since `kidux-session`'s udev rule, in GLib's loop, and
asks labwc through `wlopm` to power the machine's own panel (`eDP-*`,
`LVDS-*`, `DSI-*`, or the only output there is) off while the lid is
closed and on when it opens; at start, the lid's state as it is. Closing
it also locks the session first, `Access1.LockFor("lid")` (D67), so that
a laptop shut and carried off opens on the lock screen; the lid's state
when the launcher starts is not a closing. The keyboard's light goes off
after the panel, its level remembered where the lock screen, on which the
lid is opened, finds it to give it back, and comes back before the panel
when the launcher sees the lid open (`kidux.hardware.keyboard_light_off`
and `keyboard_light_back`, session.md section 5, D97). Nothing else
changes: the screen's brightness stays, windows stay, an external screen
stays on, and whether the computer then suspends is the daemon's, which
sees the lid close too, as the adult set it (power.md section 3); it locks
the session before any sleep, so closing the lid is never a way out of a
time limit. A session left alone locks itself too, through
`kidux-idle` (session.md section 5). Under the lock screen the session is
frozen and the launcher with it; the trusted screens have a watcher of
their own (session.md section 5).

**The lock** freezes every module with the session: the daemon freezes the
child's user manager as well as the session's scope (daemon.md section 10),
so a module is stopped under the lock screen and continues where it was,
the same one on screen.

**A launcher that crashes** leaves the modules running and open; the
launcher `session-inner` starts again a second later finds them as above,
lists them on its bar in the order the compositor does, and, its new
window being brought forward as every new window is, shows home. A module whose scope is still running with no window yet is
not started twice (`launch.running`, the active `kidux-module-*.scope`
units). Logging out, from the launcher or from the lock screen, ends the
session, `labwc`, XWayland, and every module with it.

**A module's guide** (D106). A module whose manifest says `guide = true`
(modules.md, sections 1 and 3) has its lessons shown beside it, in a third
window of the launcher, `guide.py`: a layer-shell surface on the right
edge, from the top down to the bar, layer `TOP`, with an exclusive zone of
its width, a quarter of the screen's logical width and never under 280
pixels, so that every maximised window and the launcher's own fill the
room to its left (labwc-notes.md). It comes up without the keyboard, which
stays with the module, since labwc gives the keys to a surface that asks
for them as it comes up; a press in it asks, and gives it the keys, and a
click in the program gives them back. At its top, the
module's name and *Fold*, which says its word beside its arrow; for a
child with windows, a pin stands before *Fold*, and, when several open
modules have a guide, the name is a list of them on a row of its own
under the two, so that the pane keeps its width. Under that, the guide's
introduction, when it has one, above the list of lessons, each a button,
or one lesson,
its blocks as `kidux.lessons` reads them: headings, paragraphs with bold
and italic, numbered steps and bullets, each with the button it names
drawn small before its words when the lesson gives its picture, pictures
drawn at the pane's width,
the mascot beside what it says, *Try this* in a box of its own, and the
lesson's mission, a box saying where its copy is and how to open it from
the module's own File, Open; at the bottom, *Lessons*, *Back* and *Next*.
Escape goes from a lesson to the list. *Fold* leaves a rail of 28 pixels
along the edge, an arrow pointing out of it, the book and the module's
name written upwards, its exclusive zone the rail's; a click on the rail, or the bar's *Guide*, a
button between the time and *Close* there while the pane is and lit while
it is unfolded, opens it again. While the bar asks whether to close a
module, *Guide* steps aside with the time and *Close*.

Which guide is shown is `guides.py`'s, with no GTK in it, at every change
the desk reports (`desk_changed`). Without windows the pane shows the guide
of the module on screen, and goes away for a module without one or home.
With windows it stays while any open module has a guide: the guide of the
module in use, the last one shown while a module without one or home is in
use, and none once the last module with a guide closes. A guide picked
from the list is pinned; the pin keeps the guide shown whatever window is
in use, until it is let go, when the pane follows the window in use
again, or its module closes, and is the session's alone. What the child left in each guide, folded or not and the lesson
they were in, is kept in `~/.local/share/kidux/launcher.json`, a file of
the launcher's own written whole and renamed into place, and read at
start; one that does not read is logged and set aside. The first time a
guide is shown, its missions are copied into the child's Documents, in a
folder named in their language, *Missions of <name>*, never over a file
already there, since it may be the child's work. The launcher logs
`guide: <id> lessons|lesson <n> folded|unfolded [pinned]` and `guide:
none` as the pane changes, and `guide: <id> missions copied: <n>`.

## 6. Accessibility and style

- The sizes of greeter.md section 8 (D30): every screen fits 1280x800 whole,
  and the launcher's bars are smaller than the greeter's, so that the room
  between them is the modules'; the bar along the bottom is smaller still,
  and never takes the keyboard. Full keyboard navigation with a visible focus
  ring, and nothing that is only a colour.
- Sizes in logical pixels, so the display scale makes them larger on a dense
  screen: the MacBook's panel at scale 2 and an old 1366x768 laptop at scale
  1 both get a full grid, and more modules than fit scroll.
- No text baked into pictures: every word is a label, so it is translated.

## 7. Testing

- `model.py`, unit tests: the text for every combination of mode and time
  left, in both languages; the countdown between two answers; the warnings
  at the three thresholds and never twice; the daemon disappearing and
  coming back.
- `launch.py`: the whole argv, a web application's, a manifest with
  nothing to start refused, a module still running from before found
  by its scope, and a module ended by stopping its scope.
- `compositor.py`: the windows the protocol's events build, from a
  scripted sequence of them: a window listed from its first `done`,
  changes holding at `done` and only changes counting, a dialog's parent,
  a closed window gone, numbers that never repeat, the states' array read.
  `desk.py`, against a compositor that only remembers: a module's first
  window brought forward and the module on screen, a window no manifest
  claims being the waiting module's, a dialog its window's module's, a
  stranger left alone, home the launcher's window, a tile of an open
  module showing it and starting nothing, a module not started twice and
  one that could not start tried again, the window last active shown
  again, a closed module leaving the bar and home coming back, a launcher
  started again finding the modules, and the bar hearing of a change and
  only of one; in the kiosk, fullscreen taken back and a main window
  maximised, a dialog left; with windows, placing left to the compositor,
  fullscreen taken back once and kept afterwards, two modules open at
  once, home minimising every main window and no dialog (and in the kiosk
  nothing), the bar's windows and a button bringing one back, the bar
  told of a window minimised; `desk.title_of`; and closing: every
  window of the module on screen and no other asked, nothing on home, a
  module that goes when asked never asked about, one still open after the
  wait asked about and not ended, *Cancel* keeping it and asking nothing
  more, *Close it anyway* and a second Close while asked ending its scope,
  a second Close before the wait asking again, and the question gone when
  the module closes after all.
- `kidux.modules`, in `kidux-common`'s tests, against a directory of
  sample manifests, including broken ones: a bad manifest is skipped and
  logged, never a crash. `daemon.py`: only the enabled modules get a tile.
- **The machine:** `tests/run session` checks, with pictures: the launcher
  is on screen with the child's name and time; *Lock* by keyboard puts the lock screen up; the
  session continues and the launcher is still there; `systemctl restart
  kidux-daemon` under it leaves it standing and still counting; *Log out*
  by keyboard brings back the sign-in screen; killing the launcher starts
  it again; the bar is along the bottom. With the tests' two stand-in
  modules (`16-module-open.py`): Ctrl+Alt+F2 in the child's session leaves
  the screen where it is; a module opened by keyboard fills the room
  above the bar with no frame, gets the click made over it, in its scope with
  its own three directories, writes in the child's home what every module
  can see, and reaches the network; Super brings the launcher back with
  the module in the bar; a second module opens over it and finds the first
  one's file, and has the room above the bar rather than the whole screen
  it asked for; Alt+Tab goes round the modules in the bar's order, never
  home, with one module on screen nowhere; the lock
  freezes both and continuing brings the same one back; a launcher that
  crashes comes back home with both in its bar; an open module's tile
  brings it forward; a module that ends leaves the bar and the launcher
  comes back; Alt+F4
  closes the module that goes when asked, and on the one that refuses
  (the robin, which keeps its window as a program with unsaved work
  would) the bar asks ten seconds later, the module still open above it
  (picture `launcher-close-question`), and Alt+F4 again ends it; logging
  out from the lock screen ends everything. `19-module-hello-web.py`:
  after its link, when *Done* can no longer close Chromium, Alt+F4
  does.

## 8. The launcher's own look

As built, and used by the owner:

- **The time left** is an hourglass and `00:51`, and the words, "51
  minutes left", on hover and on a tap.
- **The warnings** are a bubble from Kidux that stays until closed, and
  nothing else: the bar keeps only the time.
- **The clock** is digital, like the sign-in screen's.
- **Log out** always asks *Have you saved your work?*, even while there is
  nothing to save: the habit is the point.
- **Turn off** only locks: a child looking for how to turn the computer off
  finds the button, and the lock screen, which is trusted, has the real one.
- **The bar** is the launcher's cream a shade darker, so that it reads as a
  bar under any module, with the button on screen in the launcher's dark
  brown.

Open, for a later phase, once children use the machine daily: a bar that
empties beside the words, for children who cannot yet read; a soft sound at
the one-minute warning; a clock face with hands as an option on the child's
page in the panel.
