# The adult panel and the first-run wizard

The adult panel is where an adult changes what a child may do;
the first-run wizard is what turns a freshly installed machine into one with an
adult password and a first child, without a terminal. Both are trusted
screens (D6): they run as `_greetd`, inside `kidux-greeter`, and nowhere else.

This document fixes the behaviour and what the daemon offers for it. How
the screens look follows the sign-in screen (greeter.md, section 8); what is
specific to these screens is in section 8 here.

## 1. Shape

Both are more screens of `kidux-greeter`, not a program of their own:

- The adult's token is bound to the D-Bus connection that unlocked it (D26).
  The sign-in screen already holds that connection when the adult types the
  password, so the panel is simply what it draws next. A second program would
  need a second unlock.
- The lock screen reaches the panel the same way, and a child's frozen
  session stays frozen underneath it.
- Leaving the panel is the same code path everywhere: `Parental1.Lock(token)`,
  then back to the screen it was opened from (greeter.md, section 2).

```
kidux_greeter/
  panel.py      the state machines of the panel and the first-run wizard:
                pages, forms, what each save calls
  screen.py     what a state machine hands the view: a screen, its data, and
                which machine owns the next tap
  flow.py       hands over to them and takes the screen back
  view.py       draws all of it
```

`panel.py` follows `flow.py`: no GTK, a fake daemon in the
tests, and the same rule that every screen has a way forward.

## 2. The first-run wizard

`SignIn.start()` hands the screen to the wizard when there is no adult
password yet (`Parental1.IsPasswordSet()`), or when setup never finished and
there are no children. A machine with children goes to them, set up or not:
it was set up some other way, and is usable. From there:

```
language ──▶ keyboard ──▶ (the screen restarts in them) ──▶ adult password
   ──▶ usage statistics ──▶ the first child's form
   ──▶ done: the sign-in screen, with the child on it
```

1. **Language.** Kidux's logo, and one button per locale in
   `/usr/share/kidux/locales`, each written in its own language ("Español",
   "English"), so an adult who reads only one of them can find it. Tapping
   one redraws the wizard in it at once, with `kidux.i18n.translations()`.
2. **Keyboard.** The layouts that go with the chosen language (section 8).
   There is no line to try them on: the layout only changes
   when the screen restarts, so such a line would show the old one.
3. **Saved, then restarted.** `Daemon1.SetConfig` (section 5) writes the
   language and keyboard, and the greeter exits on purpose. greetd starts it
   again; `greeter-session` hands `cage` the new layout; the wizard resumes at
   the adult password. This is the only way the layout can change (D29), and
   it has to change *before* the adult password is typed: a password typed in
   the wrong layout is one the adult cannot type again. The wizard knows where
   to resume because `IsPasswordSet()` is still false and `setup_complete` is
   still false while `default_language` has been set by someone
   (`language_chosen`, section 5).
4. **Adult password,** twice. D5: no rule but not empty; a short one gets a
   sentence saying longer ones are harder to guess, and nothing more.
   `Parental1.SetPassword("", password)`, then `Parental1.Unlock(password)`
   for the token the next steps need.
5. **Usage statistics.** One switch, on, and what it does in a few sentences:
   every fetch of the archive carries an identifier made for this machine
   alone, so that the archive's logs count it as one machine (D109).
   *Continue* is `Daemon1.SetConfig(token, {apt_statistics})` with the
   switch's state; the Advanced page has the same switch later.
6. **The first child,** on the child's form of section 3, the same one the
   panel uses for every later child: name, picture, language, password
   twice, and how they may use the computer, which starts at an hour a day.
   The child's Unix name is made from their name, without accents, and
   never shown. *Add* is `Children1.Create`, then `Access1.SetPolicy`; a
   field that is missing or refused is marked on the form, and what was
   typed stays, except the passwords.
7. **Done.** `Daemon1.SetConfig(token, {setup_complete: true})`,
   `Parental1.Lock(token)`, and the sign-in screen, where the new child's
   picture is waiting.

*Back* from the keyboard to the languages, and *Turn off* always. Leaving the
wizard half-way leaves a machine that is still not set up, and the next
start of the greeter resumes it at the first step not done, worked out from
what the daemon says, never from a file of the greeter's own.

## 3. The panel

Reached with the adult password from the *Adult* button on the sign-in
screen and from the lock screen, with the corner of a laptop's battery,
brightness, keyboard light and sound over its top right as on every
screen of the greeter (greeter.md). Four pages, each one screen with
everything it is about (D37): a tab bar across the top, *Close* in the
corner where *Back* is on every other screen, and the logo small in the
bottom middle.

**Children.** Across the top, each child as a small picture and name, the
one shown marked, and *Add a child* at the end. Below, the chosen child's
time used today, *Give more time*: 15, 30 or 60 minutes, given at once
with `Access1.Grant` (section 5), and *Left today*: a number of minutes
from 0, which starts at what the child has left, and *Set*, which makes it
exactly what they have left with `Access1.SetTimeLeft` (D50), zero
included; for a child with no limit the row says *No time limit*, and
*Set* answers that there is nothing to set. Below that, the
child's form, all of it at once:

| Field | Control | Saves with |
|---|---|---|
| Name | a text field | `Children1.SetProfile` |
| Picture | a list of the avatars, as pictures | `Children1.SetProfile` |
| Language | a list of the shipped languages; the keyboard follows it | `Children1.SetProfile` |
| Password | two fields, empty; changed only when both are filled | `Children1.SetChildPassword` |
| How they may use the computer | a list of the three modes and, on the same row, the minutes a day, a number, which counts when the mode is the daily one | `Access1.SetPolicy` |
| Days | seven boxes, *Mon* to *Sun*, all ticked for a new child: the days of the week the child's time is for (D54), which a mode by an adult's say does not ask, so there they cannot be changed; on the panel only, the wizard's first child has every day | `Access1.SetPolicy`, with the mode |
| Windows | a switch, off for a new child, and on the same row what it does: modules in windows the child moves, resizes and puts full screen, several at once, from their next sign-in (D46); on the panel only, the wizard does not ask | `Children1.SetProfile` |

The mode, the minutes and the days are one field for the form,
`"<mode>:<minutes>:<days>"`, the days as seven digits, Monday first, 1 for
a day ticked: `daily:60:0000111` is an hour on Friday, Saturday and Sunday
(`parse_access` and `access_of` in `panel.py`, which also read the field
without its days, as every day).

*Save* sends every field that changed, one call each, and shows one notice;
a field the daemon refuses is marked where it is, with a sentence, and the
others are kept. *Remove* asks once, on the same page, with *Keep their
files* as the alternative (`Children1.Delete`); a child with a session open
cannot be removed (`SessionActive`), and the page says so. *Add a child* is
the same form, empty, with *Add* in place of *Save*.

The focus starts in the name, so that an Enter pressed out of habit gives
nobody time; Enter in the name saves, Enter in the first password field
moves to the second, and Enter there saves. For a new child, Enter in the
name moves to the password instead, since there is no child without one.

**Modules.** Two parts of one form. First the installed modules, one grid:
the modules down, each with its name and description in the machine's
language (`kidux.modules.name_in` and `description_in`, through the
module's own gettext domain), the children across, each under their
picture and name, a `Gtk.Switch` where they meet, reading
`Modules1.List(child)`, and *Remove* at the end of each row. A module whose
manifest says `needs_windows` has *Needs windows* after its description,
and for a child without windows its switch is off and cannot be switched
on (D46). Beside the name, smaller, the module's ages (D55): *Ages 4 to
8*, *Ages 2 and up* or *Ages up to 10* as its manifest gives one bound or
both, nothing when it gives none. Under the name, as small, on a line of
its own only for a module that names any, *Recommended before:* and the
modules it names in `recommended_before`, by their names in the machine's
language where the machine has them, installed or on offer, by their ids
otherwise. The description wraps
at 56 characters: wide rather than tall, so that the page stays whole at
1280x800 with a module installed and three on offer, or three installed,
and a notice. Flipping a
switch calls `Modules1.SetEnabled` at once and draws the page again from
what the daemon then says, with *Saved.*, or with *This was not saved* and
the switch back where it was; the focus stays on the switch just flipped,
and starts on the first switch. *Remove* asks once, in the module's own
row, across the room its switches and buttons take and no wider, so
that nothing on the page moves: *Remove <name>? The children's own files
stay.*, with *Cancel*, a cross, which has the focus, and *Remove*, which
calls `Modules1.Remove`. The page is drawn again in place for the
question, and for its answer: it stays where the adult had scrolled it,
scrolled no more than shows the question when its row is below the fold;
*Cancel* puts the focus back on that row's *Remove*, in view.
(`view.keep_place` sets the room's place once GTK has laid the page out,
since a place set while it is laid out moves the scrollbar and not the
page; the view logs `modules room kept at <pixels> of <pixels>, the focus
in view` once it is painted, for the tests.) A module that is only a
folder, which no package installed, as the tests' stand-ins are, says
*A folder, not from a package* after its description, and its *Remove*
asks *Remove the folder of <name>? The children's own files stay.*: the
update job removes the folder (D101). The tab order of a row is its
switches, then *Settings*, for a module that declares settings (D90),
then *Remove*. With nothing installed, the part says so.

*Settings* opens a page of the module's own: its name, *Each child has
their own. A change is saved as soon as it is made.*, then a grid with
every child across and the module's settings down, each with its label
and, under it, its description, in the adult's language. Where they meet,
the control of the setting's kind: a switch, a number box within the
setting's limits, a text box, or a password box for a secret, which says
*Set. Type a new one to change it.* when one is set, with *Forget* beside
it, and never shows it. A switch or a number is saved as it changes, a
text or a secret when Enter is pressed or the focus leaves it, each by
`Modules1.SetSetting`, and the page is drawn again with *Saved.* or *This
was not saved*. The tab bar is above it, and *Modules* goes back.
Both parts are by age (D73, `panel.ordered`): the youngest first, a module
that says no age among them, by name at the same age, and a module whose
name begins with a bracket, `[Test]` or `[Prueba]` (D70), last whatever
its age; a sentence above them says so. A version is shown as
`panel.shown_version` gives it: without what follows a `+`, which is how
the program was built, and a `0+git<date>` as the snapshot's date. Above
both parts a `Gtk.SearchEntry`, *Find a module*, narrows them to the rows
whose name or description holds every word typed, hiding the other rows
in place, in the view, so that the typing keeps its focus.

Then *Add modules*: one row per module `Modules1.Available` offers that is
not installed, its name and description as the archive gives them, in
the machine's language (D47), under them who it is for, as above, from
the same answer, and *Install*, which calls
`Modules1.Install`; with nothing installed, the focus starts on the first
*Install*. *Look for modules* calls `System1.CheckUpdates`, allowed with
children signed in, since the list is read from apt's lists; the page
shows it looking and redraws the list when it is done. With every module
installed it says *Every module the archive offers is installed.*, and on
a machine with no Kidux archive among its sources, *This computer has no
source of modules.* Both lists grow with every module there is, so the
page's two parts, and *Look for modules* under them, are in a room of their
own between the tabs and the bottom row that scrolls, centred there while
they fit, and following the keyboard's focus (D63's scrollbar and
shades); the page itself fits 1280x800 however many modules there are.

While a module is installed, it is among the installed modules from the
moment *Install* is pressed, as the archive describes it until its
manifest is in place, with a bar of how far it has got across the room
its switches and buttons will take; while one is removed, its row stays,
as last drawn, with the bar across the same room, until the removal
ends. The page stays in the adult's hands meanwhile: it scrolls, the
switches and *Settings* of the other modules work, and *Install*,
*Remove* and *Look for modules* can be pressed again. What they ask for
waits its turn, in order, each row saying *Waiting…* where its bar will
be, a module to install among the installed ones from the moment
*Install* is pressed and one to remove where it is, and each starts the
moment the job before it ends; a job that cannot start, with a child
signed in or the daemon busy, drops what waited behind it, since nothing
would start it. The page asks `System1.UpdateState` once a second
(`poll_modules`), following the bar in place: the page is drawn again
only when something else changes, so that it never moves under the adult
(`screen.only_progress_differs`), and a poll is no question of the
adult's: the screen is not made insensitive for it, a tap that comes
while one is out is asked once it is answered, and a poll that comes
while a question is out is left to that question's answer, which asks
again (`view.run(poll=True)`). How the job went, *Installed.*,
*Removed.* or *That did not work.*, is a toast over the bottom of the
page for five seconds, which moves nothing; apt's own line of a failure
stays on the page. With a child signed in, *Install* and *Remove* answer
*Children are signed in. Modules can be installed and removed once they
have logged out.*

**System.** One form:

- The Kidux version, `kidux-base`'s, and on the same row the updates;
  under them, in the small letters of the ages, each part's own version:
  *service*, *session*, *child's screen*, *sign-in screen*, *common
  parts* and *web modules* (`System1.Versions`, daemon.md section 13; the
  daemon's own `Daemon1.Version` when dpkg says nothing). What the
  updates' row says takes two lines at most, the rest behind an ellipsis
  and whole in its tooltip, so that a long list of packages or apt's
  line keeps the page within 1280x800. The updates: *Look for
  updates*, then *Install* with a bar and the package it is on, and
  *Restart now* when an update needs it (`System1.CheckUpdates`,
  `ApplyUpdates` and `UpdateState`, daemon.md section 13). *Install* is
  refused with a sentence while a child has a session open.
- The recovery password, hidden until *Show* is tapped, with a sentence
  saying what it is for: starting the machine another way, from the boot
  menu. `Parental1.GetRecoveryPassword` (section 5).
- The adult password: the current one, the new one twice, and *Save*.
- The machine's language and keyboard, two lists on one row, saved as
  soon as either changes. Both apply the next time the screen starts: restarting it from
  the panel would end the lock screen's cover over a child's session when
  the panel was opened from there.
- Display scale: *Automatic (175 %\*)*, which is what a machine has until
  an adult chooses (D53), the percentage being what automatic comes to on
  this screen (D56: from `KIDUX_SCREEN_MODE`, the mode `session-inner`
  exports, or the display's size times its scale where nothing did), then
  100, 125\*, 150\*, 175\*, 200, 250\* and 300 %, a list, the sizes that are
  not whole multiples of 100 % marked (`panel.size_label`,
  `words.NOT_PREFERRED_MARK`), automatic too when it comes to one; under
  it a note, *Sizes with \* can make a module that uses XWayland look
  blurred; if one does, choose a size without \*.* (D59), the form's rows 6
  pixels apart so that the page fits 1280x800; saved as soon as it
  changes. The screens take it when they start (D49): on the sign-in
  screen, closing the panel after a new size, language or keyboard starts
  the screen again, so that the adult sees it applied (*Saved. It applies
  when you close the panel.*); on the lock screen, which must not start
  again over a child's session, it waits for the next start (*Saved. It
  applies the next time the screen starts.*), and a child's session takes
  it at the next sign-in.
- *Left alone* (D67): one row, *Lock after* [minutes] *min* · *screen off
  after* [minutes] *min*, and *Set*, which Enter in either box does too:
  the minutes before a child's session locks itself (1 to 120, five until
  an adult chooses), which are also the panel's own, and before any screen
  turns off (1 to 240, ten). `set_idle` sends both to `SetConfig` and says
  *Saved. This panel closes after that long from now on, and a child's
  screen locks after it from the child's next sign-in.*: the panel takes
  them at once, a screen when it starts.
- *Advanced*: *Pointer, touchpad and Chromium*, a button to a page of its
  own (the System page has no room left at 1280x800), `panel_advanced`,
  under the same tabs, for the settings that depend on the machine's
  hardware (D52): a line saying they are *How this computer's pointer
  moves, and what to try if something does not work on it*; *Share usage
  statistics*, the wizard's switch again, sent as `apt_statistics` (D109);
  *Pointer speed* and *Scrolling with two fingers*, a list of five steps each,
  *Much slower* to *Much faster*, the middle *Normal*, each sent to
  `Daemon1.SetConfig` as `pointer_speed` or `scroll_speed`, -2 to 2, as
  soon as it is chosen, which says *Saved. It applies the next time a
  child signs in.* (`set_pointer`), with a sentence under the second on
  what *Normal* is; and *Chromium's options*, a text of several lines,
  one flag a line, with a sentence on what it is for; *Save*, which sends the lines
  to `Daemon1.SetConfig` as `chromium_flags` and says *Saved.*, or, when
  the daemon refuses one, says what an option must be and keeps what was
  typed (daemon.md section 15); and under Save the options worth trying
  as a list, in the order of rollout.md section 5, each in monospace,
  selectable with the pointer to copy, with what it does beside it
  (`words.CHROMIUM_OPTION_LIST`), out of the keyboard's way: Tab goes
  from the box to Save.

  Beside it, after it in the keys' order, *Suspending the computer*, a
  button to a page of its own, `panel_power`, under the same tabs (D119,
  power.md), its title and no line under it: *When the lid closes*, a
  list of *Suspend* and *Nothing*, sent to `Daemon1.SetConfig` as
  `lid_action` as soon as it is chosen, which says *Saved.* (`set_lid`),
  with *With another screen connected, closing the lid only turns this
  screen off.* under it; *Action when idle*, a list of *Suspend* and *Only
  turn the screen off*, *after* [minutes] *min* (1 to 240, twenty) and
  *Set*, which Enter in the box does too, sent as `idle_action` and
  `idle_sleep_minutes`, which says *Saved. It applies the next time the
  screen starts.* (`set_idle_sleep`), with *The screen can turn off
  earlier: that is set on the System page.* under it; a line on what
  suspending is; and, on a computer that cannot suspend (`GetConfig`'s
  `can_sleep`), a warning that closing the lid or leaving it idle only
  locks it and turns the screen off. A value the page does not offer
  shows as *Suspend*.

**Network** (D62). The machine's network, for the adult who wants to see
it and fix it, `panel_network`, through `Network1` (daemon.md section 16):

- *Connection*: each interface on a line, what it is (*Wi-Fi*, *Cable*,
  *Other*), the network's name and the signal for a Wi-Fi, and its
  address, or *Not connected*.
- *Router*: whether the default route's gateway answers one ping, *It
  answers.* or *It does not answer.*, *Asking it…* while it is asked, and
  a sentence when there is no default route at all; *Look again*, which
  rescans the Wi-Fi and asks the router again. The page looks again by
  itself when it opens, and asks the daemon once a second while a job
  runs (`poll_network`).
- When NetworkManager manages a Wi-Fi, *Wi-Fi networks*: every network
  in reach, the one in use first, then by signal, the page scrolling when
  they are many (D63), each with its name, its signal, a padlock
  when it has a password, and what can be done: *Connected*; *Connect*,
  which for a secured network never joined asks its password in place,
  a field and *Connect* on the network's own row, the length checked
  before the daemon is asked (8 to 63 bytes, as the daemon counts it, or
  64 hex digits); *Forget* for one this computer knows, which
  asks once under the list, *Cancel* first; or, for an enterprise or WEP
  network, a sentence saying Kidux cannot join it from here. A note says
  that changing the network can leave the children's modules without a
  connection for a moment: the page is not refused while a child is
  signed in, since the connection is the machine's and a laptop changes
  network under whoever is using it. How a job ended is the page's
  notice, read through `poll_network` from the moment the job starts, so
  that one over before the page is read again is not missed: *Connected.*, *That is not the network's password.* (with the
  field again, for another try), *It did not connect.* with NetworkManager's own
  sentence, or *Forgotten.*
- A Wi-Fi NetworkManager does not manage, one the Debian installer set
  up with `ifupdown`, is shown and not changed: a sentence says so, and
  the user guide says how to hand it to NetworkManager.

**Leaving.** *Close*, Escape anywhere in the panel, or as many minutes
without a touch as a child's session may be left alone (`idle_lock_minutes`,
five until an adult chooses; every panel page carries it as `idle_seconds`,
which the view's idle timer reads) locks the token and goes back to the
screen the panel was opened from; the daemon kills the token after the same
minutes anyway (D26, D67). From
the lock screen the panel is one of the adult's choices, after the adult
password, next to giving time, unlocking to save and logging out. The panel never
outlives the token: a call answered `NotUnlocked` closes it with a sentence
asking for the password again.

## 4. Languages

The panel and the wizard are in the machine's language, whatever child is
on the sign-in screen, except while the wizard's first step is choosing it.
Every word goes through the shared catalogue; the words the panel shares
with the launcher (the access modes, *Time left*) are already in
`kidux.vocabulary`, and the panel's own sentences go in a module of their
own, as the sign-in screen's do in `words.py`.

## 5. What the daemon offers them

Besides the calls the sign-in and lock screens use, the panel and the wizard
use three made for them, all in class `manage` for polkit, all needing a
token, all audited (daemon.md sections 7 and 15):

- **`Daemon1.SetConfig(token, changes a{sv})`**: `default_language` (one of
  the shipped locales), `default_keyboard` (the pattern of daemon.md
  section 6), `display_scale` (1.0 to 3.0), `setup_complete` (bool),
  `chromium_flags`, `pointer_speed` and `scroll_speed` (-2 to 2),
  `idle_lock_minutes` (1 to 120), `screen_off_minutes` (1 to 240) and
  `save_minutes` (1 to 15), which no page offers. Unknown
  keys are `InvalidArgument`. On a machine with no adult password yet the
  token is ignored for `default_language` and `default_keyboard` only, as
  `SetPassword` ignores it, so the wizard can set them first; polkit has
  already limited who may call it. The call records `language_chosen = true`
  in `config.toml` when it sets a language, which is how the wizard knows to
  resume at the password (section 2, step 3), and `GetConfig` reports it.
- **`Parental1.GetRecoveryPassword(token) → s`**: `grub_password` from
  `adults.toml` (daemon.md section 5), for the System page.
- **`Access1.Grant(token, username, minutes)`**: the same bank deposit as
  `GrantExtraTime`, for an adult who is already in the panel and should not
  type the password again. 1 to 1440 minutes. Does not unlock anything: a
  locked session is continued from the lock screen.
- **`Access1.SetTimeLeft(token, username, minutes)`**: what the child has
  left today, 0 to 1440 minutes (daemon.md section 7). A session up locks
  at once at zero.

The update calls, `System1.CheckUpdates`, `ApplyUpdates` and `UpdateState`,
are designed in daemon.md section 13, the module calls,
`Modules1.Available`, `Install` and `Remove`, in section 9, and the network
calls, `Network1.GetNetwork`, `Check`, `ConnectWifi` and `ForgetWifi`, in
section 16.
`kidux.client.Client` has a method for every call.

## 6. What stays out

- Photographs as avatars (avatars.py says why), a PIN, password rules
  beyond "not empty" (D5).
- Network settings beyond joining and forgetting a Wi-Fi: addresses,
  proxies, VPNs, an office's Wi-Fi with a user of its own. An adult who
  needs them sets them up from Debian, with NetworkManager's own tools.
- More than one adult password. One password for every adult in the family.

## 7. Testing

- `panel.py`, unit tests against a fake daemon, like
  `flow.py`: every page, every save calling what the table says, a wrong
  token closing the panel, the wizard resuming at the right step after each
  possible interruption, and no screen without a way forward.
- The Modules page, against a directory of manifests: a switch per module
  and child, the names in the machine's language, a switch saved at once, a
  refused one put back, a lost token closing the panel; what the archive
  offers and what it does not, no archive at all, installing and removing
  and the page that follows them, a failure with apt's line, the refusal
  while children are signed in, one job at a time, and *Look for
  modules*.
- The Network page, against a fake daemon: looking again when it opens
  and asking until the job ends, a secured network's password asked in
  place and joined, one too short marked without asking the daemon, a
  wrong one asked again, another failure with NetworkManager's sentence,
  Forget asking once, a busy network, a lost token closing the panel.
- The daemon's four new calls, in its own tests: the token, polkit's
  `manage` class, the validation, the audit line, and `SetConfig`'s
  no-password exception covering exactly two keys.
- **The machine:** `tests/run session` gains a run on a machine with no
  adult password — no `kidux-as setup` — that goes through the wizard by
  keyboard in Spanish, then signs the new child in: from a fresh install to
  a working child account without a terminal. Pictures of every step, as for
  the sign-in screen.
- **The network** (`23-network.py`): a simulated Wi-Fi with a password
  (`mac80211_hwsim`, `hostapd`, `dnsmasq`), joined from the Network page by
  keyboard, a wrong password first, and forgotten.

## 8. The panel's own look

As built, and used by the owner:

- **The panel's look** is dense, for adults (D37): the sign-in screen's
  colours and typeface (greeter.md section 8), text at 16 px, buttons and
  fields 40 px tall, and one screen per page, which fits 1280x800 whole.
- **The keyboards offered** are, for Spanish, *Spanish (Spain)* `es` and
  *Latin American* `latam`; for English, *US* `us` and *UK* `gb`. The daemon
  accepts any layout name, so a machine with another keyboard is set through
  `Daemon1.SetConfig` from an administrator's SSH session until the panel
  offers the full list from `xkb-data`.
- **The first child's password** is asked by the wizard, since a child
  without one cannot sign in (D9); the user guide says a young child's can be
  very simple.
- **Removing a child** deletes their files by default; *Keep their files* is
  the alternative.
