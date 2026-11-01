# kidux-daemon

The one privileged process in Kidux. It owns the family's state, decides who may
start a session and for how long, puts the lock screen up and takes it down, and
is the only thing that ever writes under `/home/.kidux`. Everything else — the
sign-in screen, the lock screen, the launcher, the adult panel — asks it over
D-Bus and is told yes or no.

This is the design. The wire protocol it implements is in the phase 1 plan,
section 7; the decisions it rests on are D6, D9–D18 and D24–D28 in
`architecture.md`. Where this document and the plan disagree, this document is
right and the plan is out of date.

## 1. Shape

One Python process, running as root, on the GLib main loop. `Type=dbus` on the
system bus as `org.kidux.Daemon1`, object `/org/kidux/Daemon1`, activated on
demand and started at boot after `kidux-firstboot.service`.

Source package `kidux-daemon`, binary package `kidux-daemon`, Python package
`kiduxd` (never imported by anything else; `kidux` from `kidux-common` is the
shared library, `kiduxd` is the daemon).

```
kiduxd/
  main.py        wiring the real machine to the service; the main loop
  bus.py         D-Bus in and out, against org.kidux.Daemon1.xml beside it
  service.py     every exported method, independent of D-Bus
  gate.py        polkit checks and the daemon's own checks (section 2)
  errors.py      the D-Bus error names (section 3)
  tokens.py      adult-panel tokens (section 4)
  adults.py      the adult password, argon2id (section 5)
  accounts.py    adduser, chpasswd, chfn, deluser, behind a protocol (section 6)
  children.py    the children and their profile files (section 6)
  access.py      policy and time, pure functions over an injected clock (section 7)
  sessions.py    what logind says is running (section 8)
  locker.py      the lock state machine (section 10)
  attention.py   the power button and Ctrl+Alt+Escape (section 11)
  firstboot.py   the first-boot unit (section 12)
  updates.py     the update job and its status file (section 13)
  logind.py      logind: sessions, power off, reboot (sections 8, 12)
  machine.py     systemd and logind as the lock needs them (section 10)
  pamcheck.py    a child's own password, through PAM (section 2)
  config.py      config.toml
```

`machine.py` is the real systemd and logind behind the lock, and `pamcheck.py`
checks a child's own password through PAM.

`access.py` has no D-Bus, no filesystem and no clock of its own. Everything with
a way to be quietly wrong lives there so it can be tested against a fake clock
in milliseconds. Every other module is a thin adapter around it.

Two seams exist for the tests: the state root comes from `KIDUX_STATE_ROOT`
(`kidux.paths`), and the pieces that touch the machine — accounts, logind,
systemd, polkit, input devices — are objects handed to `main.py`, so a test can
replace `SystemAccounts` with `FakeAccounts` and run the whole daemon on a
private bus against `python3-dbusmock`'s `logind`, `polkitd` and `systemd`
templates.

## 2. The three gates

Every call passes three gates, in this order, and each one answers a different
question.

**Gate 1 — PAM, through greetd: who may start a session.** The daemon never
does this. A child's password is their Unix password and greetd runs the PAM
conversation (D10). The only PAM the daemon does itself is verifying a child's
password on the lock screen (`ContinueSession`, `EndSession`), through
`python3-pam` against `/etc/pam.d/kidux`, which includes `common-auth` and
`common-account` and nothing else. trixie's `python3-pam` is PyPAM: the module
is `PAM`, a C binding with a conversation callback, not the pure-Python `pam`.

**Gate 2 — polkit: which Unix users may call what.** Three actions, defined in
`/usr/share/polkit-1/actions/org.kidux.daemon.policy`, all with defaults of
`no` so that only the rules grant anything:

| Action | Grants |
|---|---|
| `org.kidux.daemon.manage` | Changing configuration: `Parental1.*`, `Daemon1.SetConfig`, `Children1.Create/Delete/SetProfile/SetChildPassword`, `Access1.SetPolicy/Grant/SetTimeLeft`, `Modules1.SetEnabled/Settings/SetSetting`, `System1.CheckUpdates/ApplyUpdates`. |
| `org.kidux.daemon.screens` | What the trusted screens need: `Children1.List`, `Access1.GetPolicy/CheckAccess/AuthoriseSession/GrantExtraTime/UnlockForSaving/ContinueSession/EndSession`, `Daemon1.GetConfig`. |
| `org.kidux.daemon.self` | What a child needs: `Access1.Usage`, `Access1.Lock`, `Access1.LockFor`, `Modules1.List`, `Modules1.MySettings`, `System1.SleepWhenIdle`. |

The rules, in `/usr/share/polkit-1/rules.d/50-kidux.rules`:

```javascript
polkit.addRule(function(action, subject) {
    if (action.id.indexOf("org.kidux.daemon.") !== 0) {
        return polkit.Result.NOT_HANDLED;
    }
    if (subject.isInGroup("kidux-admin")) {
        return polkit.Result.YES;
    }
    if (subject.user === "_greetd") {
        return polkit.Result.YES;
    }
    if (subject.isInGroup("kidux-children") &&
        action.id === "org.kidux.daemon.self") {
        return polkit.Result.YES;
    }
    return polkit.Result.NOT_HANDLED;
});
```

`Ping`, `Version`, `Shutdown` and `Reboot` are not behind polkit at all: anyone
on the bus may call them. A child may always turn the computer off. Root is
not asked about either: it owns the machine already. The rules end in
`NOT_HANDLED` rather than `NO`, so anyone they do not name falls through to
the actions' defaults, which are `no`.

The daemon asks polkit with `CheckAuthorization` on
`org.freedesktop.PolicyKit1.Authority`, subject `system-bus-name` with the
caller's unique name, flags `0` (never interactive: there is no agent to
answer). A `no` becomes `org.freedesktop.DBus.Error.AccessDenied`.

**Gate 3 — the adult password: changing what a child may do.** Every method
under `manage` takes a token as its first argument (section 4). Every method
that grants time or unlocks takes the adult password itself, because those are
called from screens that have no token and are never open long enough to want
one.

### What polkit cannot see

polkit sees the action and the caller, never the arguments. So the daemon also
checks, itself, before doing anything:

- **Scope.** For `Usage(username)`, `Modules1.List(username)`, `Lock()` and
  `LockFor(reason)` called by a member of `kidux-children`, `username` must name the caller: the
  uid on the bus connection equals `getpwnam(username).pw_uid`, or the call is
  refused. A child asks about themselves and nobody else.
- **Who may be managed.** `Delete`, `SetProfile`, `SetChildPassword`,
  `SetPolicy` and `SetEnabled` act only on users who are members of
  `kidux-children`. Never the administrator, never `_greetd`, never a system
  account, whatever the token says. This is what stops an unlocked panel — or a
  bug in one — from deleting the account that owns the machine.
- **Names.** `Create` accepts `^[a-z][a-z0-9-]{0,31}$`, refuses an existing
  user, and refuses the names in `kidux.paths` (`_greetd`, the groups).
- **Tokens** are bound as section 4 says.

Refusals from these checks are `org.kidux.Daemon1.Error.NotAuthorized`.
`kidux.client` maps both that and `AccessDenied` to `PermissionDeniedError`,
which is a bug rather than something to show a child: the screens only ever
offer buttons for things their user may do.

## 3. Errors

D-Bus error names under `org.kidux.Daemon1.Error`:

| Name | When |
|---|---|
| `NotAuthorized` | The daemon's own checks refused (section 2). |
| `NotUnlocked` | The token is missing, unknown, expired or belongs to another connection. |
| `WrongPassword` | An adult or child password did not verify. Audited before it is raised. |
| `NoSuchChild` | The username is not a member of `kidux-children`. |
| `SessionActive` | The child has a session; log them out first. |
| `NoTimeLeft` | `ContinueSession` for a child whose time is spent. |
| `NoSession` | `Lock`, `UnlockForSaving` or `ContinueSession` with nothing to act on. |
| `InvalidArgument` | A name, language, avatar or number that does not validate. |
| `Busy` | An update job is already running (section 13). |
| `Failed` | Something on the machine failed — `adduser`, `chpasswd`, logind. The audit entry says what. |

A password is never in an error message.

## 4. Tokens

`Unlock(password)` verifies the adult password, audits the attempt with its
outcome and, on success, returns a token: `secrets.token_urlsafe(32)`. The
daemon records it with the caller's **unique bus name** and **uid**, the time
it was issued and the time it was last used.

A token is dead when any of these happens:

- `Lock(token)` — the panel closed.
- The unique name it was issued to leaves the bus (`NameOwnerChanged` with an
  empty new owner) — the panel crashed or was killed.
- It has not been used for `idle_lock_minutes` (config, default 5), the
  minutes a child's session may be left alone too — the panel was left open
  (D26, D67). A change to the setting applies from the next check. Checked
  on each use and by a timer; audited.
- A new `Unlock` from the same unique name — one token per connection.

A privileged call presents the token; the daemon compares it, the caller's
unique name and the caller's uid. Any mismatch is `NotUnlocked`. The token is
never the only thing checked: gate 2 has already said this caller may call
`manage` at all.

No lock-out and no delay on a wrong password (D15). The audit trail is the
defence: `unlock denied` with the caller and the time, every time.

## 5. The adult password

`/home/.kidux/adults.toml`:

```toml
schema_version = 1
password_hash = "$argon2id$v=19$m=65536,t=3,p=4$..."   # absent until set
grub_password = "..."                                  # section 12
grub_password_hash = "grub.pbkdf2.sha512.10000...."
```

argon2id through `python3-argon2` (21.1.0 in trixie), with the library's own
defaults — 100 MiB and 2 passes, the RFC 9106 low-memory profile — which is
the right cost for something typed a few times a day. `verify` is
constant-time; `check_needs_rehash` is honoured after a successful verify, so
parameters can be raised later without anyone noticing.

`IsPasswordSet()` is false when `password_hash` is absent. That is what sends
the first-run wizard to the front instead of the sign-in screen.

`SetPassword(token, new_password)`: non-empty, no other rule (D5). Audited.
On a machine with no adult password yet the token is ignored: there is
nothing to unlock with, and the first-run wizard has to be able to set the
first one. polkit has already limited who may call it at all. Once a password
exists, changing it needs a token like everything else.

Because a token is bound to the connection that unlocked, `busctl` cannot
drive the daemon: every `busctl` is a connection of its own. An administrator
scripting it uses one connection for the whole conversation, as the panel
does; `tests/lib/seed/user-data` has an example, `kidux-as`.

`grub_password` is stored in clear, on purpose: it is the recovery password an
adult reads off the panel when they need to boot the machine by hand, and a
hash cannot be read off a panel. The file is `root:kidux-admin 0640`, which is
exactly the set of people who may see it: `kidux.state.write` gives every file
it writes as root to `kidux-admin`, and every directory on the way, because a
file root makes would otherwise belong to group root and be closed to the
administrators.

## 6. Children

Creating a child touches the machine in a fixed order, and a failure at any
step undoes the steps before it:

1. Validate: username (section 2), `language` is one of the locales in
   `/usr/share/kidux/locales`, `avatar` passes `kidux.avatars.exists`,
   `keyboard` matches `^[a-z][a-z0-9_+:-]{0,31}$`, `display_name` is non-empty
   and at most 64 characters.
2. `adduser --disabled-password --comment <display_name> --shell /usr/sbin/nologin <username>`
   (adduser 3.152; `--gecos` is the old spelling).
3. `adduser <username> kidux-children`, then `adduser <username> video`. The
   second is for `brightnessctl`, which the idle handler in the child's session
   uses to darken the screen (`session.md`).
4. `chpasswd`, fed `<username>:<password>\n` on standard input. The password
   is never an argument and never logged.
5. Write `profile.toml`, `access.toml`, `usage.toml` and `modules.toml` with
   `kidux.state.write`. A new child's `access.toml` is `mode = "manual"` with
   an empty bank: the safe default, and the one the wizard and the panel
   always ask about.
6. Emit `ChildrenChanged`. Audit `child created` with the username, never the
   password.

If any of 2 to 5 fails, whatever exists of the account is removed with
`deluser --remove-home`, the state directory is removed, and the first error
is raised. adduser can fail after creating the account, when a group is
added, so the account is looked for rather than assumed either way.
`deluser --remove-home` needs `perl`, which a minimal Debian does not have;
the package depends on it.

`Delete(token, username, keep_home)`: refuses with `SessionActive` while the
child has a session of class `user` — a session is ended by logging out,
never by deleting the account under it. For the seconds after a log-out
logind still holds the child's user manager, as a session of class
`manager`, and `deluser` refuses a user with a process: the daemon ends it
(`TerminateUser`) and waits for it to go. Then `deluser` (`--remove-home`
unless `keep_home`), the state directory is removed, `ChildrenChanged`,
audit.

`SetProfile(token, username, changes)`: `display_name`, `language`,
`keyboard`, `avatar`, `age`, each validated as above, and `windows`, a
boolean: whether the child's modules open in windows they move, resize and
put fullscreen, several at once (D46), off for a new child; unknown keys are
`InvalidArgument`. A changed `display_name` also runs `chfn`. Takes effect at
the child's next sign-in.

`SetChildPassword(token, username, password)`: `chpasswd` as in step 4.
Audited.

`List() → aa{sv}`: `username`, `display_name`, `language`, `keyboard`,
`avatar`, `age`, `mode`, `windows`, sorted by `display_name`. What the sign-in screen
draws its rows from. Callable by the trusted screens and by administrators,
never by a child.

## 7. Policy and time

`access.py`. Pure functions over three inputs: the child's `access.toml`, their
`usage.toml`, and a clock that answers `wall()` (aware datetime) and `mono()`
(monotonic seconds). The daemon passes the real clock; the tests pass one they
control.

### The files

```toml
# access.toml
schema_version = 1
mode = "daily"            # "unlimited" | "daily" | "manual"
daily_minutes = 60        # daily only
granted_seconds = 0       # the bank (D14)
days = [true, true, true, true, true, true, true]   # Monday first (D54)
```

`days` is the days of the week the child's time is for, Monday first, all
of them for a new child and for a file written before there were days. A
day not ticked is a **day off** in `daily` and `unlimited` modes; `manual`
is by grant any day and does not ask them.

`GetPolicy(username)` returns the file's fields, `days` as seven booleans.
`SetPolicy(token, username, changes)` takes `mode`, `daily_minutes` and
`days` (`ab`, exactly seven), each checked (`validate_policy`), and keeps
the days as they were when `days` is left out; the bank is not part of a
policy and is refused there, since time is given by a grant, which is
audited. Audited as `policy set` with the mode, the minutes and the days as
seven digits, Monday first, `1111100`.

```toml
# usage.toml
schema_version = 1
last_day = "2026-09-22"   # the accounting day last seen (below)
seconds_used_today = 0
[session]
active = false
lock = "none"             # "none" | "time_up" | "requested" | "power_button" | "grace"
                          # | "idle" | "lid" | "sleep"
boot = ""                 # the boot the session is active in
```

A daemon that starts again under a child's session finds it `active`, and
locks it again with the same reason when it was locked. Only in the same
boot, `/proc/sys/kernel/random/boot_id`: a state from another boot is a
computer turned off, or hung, under a locked session, and the session that
appears is a new sign-in, which the password has already let in. A state
with no `boot` counts as this boot's.

### The accounting day

```
accounting_day(wall) = (wall - reset_hour hours).date()
```

with `reset_hour` from `config.toml`, default 4. The day changes at 04:00, so
an evening session is not cut in half by midnight.

The day is checked at every session start, every tick, every `CheckAccess`
and every `Usage`:

- `accounting_day(now) > last_day` — **rollover**: `seconds_used_today = 0`,
  `last_day = today`, and in `daily` and `unlimited` modes `granted_seconds =
  0` (an extra grant is for today, D14; in `unlimited` mode one only counts on
  a day off). In `manual` mode the bank is untouched.
- `accounting_day(now) < last_day` — the clock went backwards. **No rollover.**
  Audited. A counter never resets because a clock moved.
- More than one day apart in either direction — audited as a clock jump, then
  handled as above.

### Availability

`available(policy, usage, weekday)`, where `weekday` is the accounting day's
(`weekday_of(usage)`, Monday 0: `last_day`'s, which is today's once the day
is checked, or a later one while the clock is behind it):

| Mode | `available` on a ticked day | on a day off |
|---|---|---|
| `unlimited` | −1 | `max(0, granted_seconds − seconds_used_today)` |
| `daily` | `max(0, daily_minutes × 60 + granted_seconds − seconds_used_today)` | `max(0, granted_seconds − seconds_used_today)` |
| `manual` | `granted_seconds` | `granted_seconds` |

A day off is a day whose allowance is none: what an adult gives that day,
from the panel, the sign-in screen or the lock screen, is what the child has,
and it goes with the day. A session still up at the reset hour into a day
off has nothing left at the next tick, and locks `time_up` as when its time
runs out (D54).

### `CheckAccess(username) → (state, seconds)`

While an update is being installed (section 13), `("updating", 0)`: no session
starts under dpkg. After the day check: `available` −1 → `("allowed", -1)`;
`available > 0` → `("allowed", available)`; else a day off →
`("day_off", 0)`, `daily` → `("blocked", 0)` and `manual` →
`("needs_adult", 0)`. The greeter calls this only after greetd has accepted
the child's password, so a wrong password and a spent allowance are never the
same message.

### Counting

While a session is **unlocked**, the daemon holds `unlocked_since` in
monotonic seconds. A tick does:

```
delta = mono() - unlocked_since
seconds_used_today += delta
if mode == "manual": granted_seconds = max(0, granted_seconds - delta)
unlocked_since = mono()
flush usage.toml (and access.toml in manual mode)
```

Ticks run every 30 seconds, and sooner when a threshold is near: the timer is
armed for `min(30 s, seconds until the next warning or until zero)`, so a
warning lands within a second of when it is due rather than up to 30 seconds
late. A tick also runs on lock, on log-out and on daemon shutdown.

Monotonic time means a clock change during a session changes nothing about
that session. Locked time is not counted: on lock `unlocked_since` is cleared;
on unlock it is set again.

### Warnings and time up

After each tick, in `daily` and `manual` modes:

- `available` has just dropped to or below 600, 300 or 60 seconds → emit
  `TimeWarning(username, available)`. Each threshold fires once per unlocked
  period; unlocking after a grant re-arms the ones above the new `available`.
- `available == 0` → lock with reason `time_up` (section 10).

### Grants

`AuthoriseSession(adult_password, username, minutes)` and
`GrantExtraTime(adult_password, username, minutes)` both verify the adult
password (audited either way; a wrong one returns `false` rather than an
error, because the screen's answer is simply to ask again), then
`granted_seconds += minutes × 60` and flush. `minutes` is 1 to 1440, a day.
A grant always gives its minutes: when the day's allowance and the grants
so far are below what was used today, because an adult cut the allowance
after use or because today is no longer a ticked day (D54), that
difference is covered first, so the child has exactly `minutes` more than
they had, which was nothing. A session that is up is charged first.
The difference is where they are called from: `AuthoriseSession` on the
sign-in screen for a child who cannot yet sign in, `GrantExtraTime` on the
lock screen, where it also unlocks a session locked for `time_up`.

`Grant(token, username, minutes)` is the same deposit from the adult panel,
where the adult has already unlocked and is not asked for the password again.
It unlocks nothing; a locked session is continued from the lock screen.

All three audit `grant` with the username and the minutes, `Grant` with
`source = "panel"`, so an adult can see they gave three extra half-hours this
week.

`SetTimeLeft(token, username, minutes)`, from the panel too, sets what the
child has left today to exactly `minutes`, 0 to 1440, zero included (D50),
for an adult who wants a child to stop soon, or to try a limit without
waiting for it. What was used today stays as it was: in daily mode the
difference from the day's allowance is a grant, negative when time is taken
away, which goes with the day as every daily grant does; in manual mode it
is the bank; on a day off the day's allowance is none, in `unlimited` mode
too. A child with no limit today has nothing to set (`InvalidArgument`).
A session that is up is charged first, so the minutes are what it has from
then on, and at zero it locks at the next tick, a tenth of a second later,
as when the time runs out by itself. Audited as `time set` with the child
and the minutes.

### Continuing and ending

`ContinueSession(username, password)`: the session must be locked. The
password is the adult's or the child's, checked in that order, and which one
it was is audited. The adult's is checked first, by the daemon, so that it
never reaches PAM: PAM would log it as a failed attempt at the child's account
and make the adult wait out `pam_faildelay` before answering.
Then `available` must be positive — else `NoTimeLeft`, and the screen says so
and offers the adult path. Then unlock.

`UnlockForSaving(adult_password, minutes)`: unlock the locked session without
counting, for `minutes` (1–15). The clock stays stopped; a timer re-locks with
reason `grace`. For the child who was locked mid-sentence. The lock screen
asks for the machine's `save_minutes` (config, default 5), which the panel
does not offer; the session tests set it to 1.

`EndSession(username, password)`: adult's or child's password, in that order;
then logind's
`Session.Terminate`. greetd shows the sign-in screen. Audited.

`Usage(username) → (used_today, available)`: after the day check, and after
charging a tracked session up to the second, so the launcher never shows time
that has already gone. What the launcher shows all day.

### What the tests cover

Every case below, against the fake clock: a
fresh day; partly spent; exactly spent; a grant added; a grant partly spent
across two sessions; a grant surviving the day change in `manual` and dying in
`daily`; rollover mid-session; a session open across 04:00; the clock set back
a day; the clock set forward a week; the clock changed mid-session; each
warning firing once; warnings re-arming after a grant; the manual bank never
going negative; a grant giving its whole minutes after the allowance was cut
below what was used, or on a day unticked after use; a day off in `daily`
and `unlimited` modes, a grant on it
spent and gone with the day, `manual` mode not asking the days, and a
session running at the reset hour into a day off.

## 8. Sessions

The daemon learns about sessions from `systemd-logind`, never from its own
wrapper or from the launcher, because both of those run as the child and can
be killed by the child. The clock keeps running whatever the child does to the
launcher.

On start: `Manager.ListSessions`. Then `SessionNew` and `SessionRemoved`. For
each session: `User`, `Class`, `VTNr`, `Scope`, `Seat`. A session is
**tracked** when its uid is a member of `kidux-children` and its class is
`user`. The class matters: signing a child in also starts their systemd user
manager, which logind lists as a second session of class `manager`, with no
terminal and nothing to lock. greetd only ever starts one, so a second tracked session at once is
audited as unexpected and tracked anyway.

Tracking starts the clock (section 7) and sets `session.active = true`. A
`SessionRemoved` for a tracked session does a final tick, clears
`session.active`, stops the locker if it is up, and flushes.

If the daemon restarts mid-session, `ListSessions` finds the session and the
clock resumes from that moment. Whatever ran between the daemon's death and its
restart is not counted — a few seconds at most, since `usage.toml` was flushed
at most 30 seconds before the death and `Restart=on-failure` brings the daemon
back at once. If `usage.toml` says `lock != "none"`, the session is locked
again on the same reason, because the locker unit may or may not have survived.

The child's VT is `VTNr` from logind, never a constant. greetd's default is 7
and the locker uses 8, but the daemon reads rather than assumes.

## 9. Modules

The daemon says which learning modules exist and which are enabled for whom;
the screens read the manifests themselves (D34). What is installed is what
`kidux.modules.installed()` finds under `/usr/share/kidux/modules/`: every
directory whose `module.toml` reads, sorted by id (modules.md, section 1).
What is enabled is each child's `modules.toml`, `enabled = ["id", ...]`,
written only here.

- **`Modules1.List(username) → aa{sv}`**: one `{id, enabled}` per installed
  module, in that order, `enabled` from the child's file. The gate is the
  `self` action, then `require_self` and `require_child`: a child lists their
  own, the trusted screens anyone's. The launcher draws a tile for each
  enabled one, the panel a switch for every one.
- **`Modules1.SetEnabled(token, username, module_id, enabled)`**: the token,
  then `require_child`; `InvalidArgument` when `kidux.modules.read(module_id)`
  finds no usable manifest, which also refuses any id that is not one.
  Otherwise the id joins or leaves the child's list, the file is written,
  the audit line is `module enabled` or `module disabled` with `child` and
  `module`, and `ModulesChanged(username)` is emitted, which the child's
  launcher, still open, redraws on. Setting what is already set is not an
  error, and writes, audits and emits nothing.
- **`Modules1.Settings(token, username, module_id) → (a{sv}, as)`**: a
  module's settings for a child (D90), as its manifest declares them: the
  value of every setting but the secrets, the stored one when it is still
  of its kind and the default otherwise, and the keys of the secrets that
  are set. A secret is never read back. The token, then `require_child`;
  `InvalidArgument` for a module that is not installed.
- **`Modules1.SetSetting(token, username, module_id, key, value: v)`**: one
  setting for one child. `InvalidArgument` unless the module declares
  `key` and `value` is of its kind and within its limits
  (`kidux.modules.Setting.value`); a secret set to `""` is forgotten. The
  child's `settings.toml`, a table per module, is written mode 0600, root's
  alone, since it holds secrets, and the audit line is `module setting`
  with `child`, `module` and `setting`, never the value.
- **`Modules1.MySettings(module_id) → a{sv}`**, `self` action: a module's
  settings for the child asking, every one but the secrets, which the
  launcher puts in the module's environment when it starts it. Only a
  child's own session asks; anyone else is `NotAuthorized`.
- **`Modules1.SignIn(module_id) → aa{sv}`**, `self` action: signs the
  child asking in to their module's website with the account an adult
  gave, as the manifest's `sign_in` says, and answers with the cookies it
  names, as Chromium's `Storage.setCookies` takes them. `{key}` in the
  body is the setting of that key, a secret too; one that is empty is
  `SignInNotSet`, with nothing sent. The daemon's unit may open no
  internet socket, so the request runs in a transient unit of its own
  (`kiduxd/signin.py`, `python3 -m kiduxd.signin` as a dynamic user, no
  homes, the internet allowed), given the account on its standard input,
  never on a command line; it waits in a thread of the bus layer's
  (`Later`), so that the daemon goes on answering everyone else. A 4xx
  answer is `SignInRefused`, no answer or no cookie `SignInUnreachable`.
  The audit line says `module sign-in asked`, never the account.
- **Removing a module keeps its settings**, as it keeps its folders (D89).
- **An id whose module is no longer installed** stays in the file and is
  never listed. Removing a package must not rewrite every child's file, and
  putting it back restores the switch as it was.
- **`Modules1.Available() → aa{sv}`**, `screens` class, no token: every
  module package the archive offers, `{id, name, description, installed,
  version, min_age, max_age, before}`, sorted by id. `kiduxd/catalogue.py` reads it from what apt and
  dpkg already know, without the network: `apt-cache search --names-only
  --full '^kidux-module-'`, each package's record as the archive's index
  has it, and `dpkg-query -W` of `kidux-module-*`, run by the daemon,
  read-only. A package whose name after `kidux-module-` is not a module id
  is left out. `name` and `description` are in the machine's language
  (D47): `name` is the installed manifest's, in its own catalogue; for a
  module not installed yet they are its record's `Kidux-Name-<lang>` and
  `Kidux-Description-<lang>`, which every module's `debian/control` carries
  for each language it ships (modules.md section 3), the machine's
  language first, then English; a package without them has its short
  description's, `Kidux learning module: <Name>, <what it is>`, in English.
  `version` is dpkg's, empty when not installed. Who the module is for
  (D55) comes the same way: `min_age` and `max_age` (0 for a bound not
  given) and `before` (the ids of the modules best done first) from the
  installed manifest, and for a module not installed from its record's
  `Kidux-Ages` (`4-8`, `2-`, `-10`) and `Kidux-Before` (ids separated by
  spaces); a field that does not read gives none.
  The lists are as fresh as the last `System1.CheckUpdates`, which the
  panel's *Look for modules* runs. A machine whose sources have no Kidux
  archive gets an empty list.
- **`Modules1.Install(token, module_id)`** and **`Modules1.Remove(token,
  module_id)`**: the token; then the id must match `kidux.modules.ID` and
  must not itself start with `kidux-module-`, or it is `InvalidArgument`.
  The caller never names a package: the daemon makes `kidux-module-<id>`
  from the id it checked. `SessionActive` while any child session exists,
  locked or not, the same rule as `ApplyUpdates`: dpkg never replaces or
  removes what a session may be running. `Busy` while any job runs. Then
  the update job of section 13 runs `kidux-update install` or `remove` with
  that package; `module install started` or `module remove started` is
  audited with `module`. At the end, `UpdateFinished(outcome, detail)` with
  outcome `installed`, `removed` or `failed`, the audit line `module
  installed` or `module removed` with `module` and its outcome, and
  `ModulesChanged("")`, for anything that lists modules. While the job
  runs, `CheckAccess` answers `updating`, so no session starts under it.

The daemon never starts a module: the launcher does, as the child
(launcher.md, section 5).

## 10. The lock

Per tracked session: `unlocked → locking → locked → unlocking → unlocked`, and
`ending` from any of them.

**Lock**, with a reason (`time_up`, `requested`, `power_button`, `grace`,
`idle`, `lid`, or `sleep`, before the computer sleeps: power.md section 5):

1. `systemd1.Manager.StartUnit("kidux-locker@<username>.service", "replace")`,
   then wait until logind shows a session for `_greetd` of class `greeter` on
   VT 8 (up to 5 s). The locker is `greeter-session --lock <username>`, which runs
   `cage` with `kidux-greeter --lock <username>` in it,
   as `session.md` describes.
2. `Seat.SwitchTo(8)` on `seat0`. logind revokes the child's compositor's access
   to the display and the input devices; the compositor cannot refuse. Then
   wait until the child's `Session.Active` is false (up to 3 s).
3. `systemd1.Manager.FreezeUnit(<scope>)`, then
   `FreezeUnit("user@<uid>.service")`, the child's user manager, under which
   every module runs in a scope of its own (D32, D40). Nothing of the
   child's runs: no script, no music, no module, no counting.
4. Stop the clock; `session.lock = <reason>`; flush; emit
   `Locked(username, reason)`; audit.

If step 2 does not confirm within its timeout, the lock has **not happened**:
the child still has the screen. The daemon audits `lock failed`, and falls
back to `Session.Terminate` (D28). Losing unsaved work is the lesser harm
against a time limit that can be ignored, and the launcher already warned
about saving at the 10, 5 and 1 minute marks. This is the "switching virtual
terminals misbehaves on some GPU" risk from the plan, made explicit.

**Unlock** (after `ContinueSession`, `GrantExtraTime` or `UnlockForSaving`):

1. `ThawUnit("user@<uid>.service")` and `ThawUnit(<scope>)` first, so the
   module and the compositor are running when the display comes back.
2. `Seat.SwitchTo(<child VTNr>)`; wait until `Session.Active` is true.
3. Half a second later, `udevadm trigger --subsystem-match=input
   --action=change`. A compositor that gets the screen back takes its
   input devices back too, but wlroots 0.18 resumes libinput without
   reading its queue, so the devices are only set up when the first event
   comes; that event, the first key the child presses, is spent on the
   set-up and never reaches the window. The change event on the input
   devices is what makes the compositor read the queue first.
4. Start the clock, unless this is a grace unlock.
5. `StopUnit("kidux-locker@<username>.service")`; `session.lock = "none"`;
   flush; emit `Unlocked(username)`; audit.

**End** (`EndSession`, or `Delete`'s refusal path): both units thawed, since
a frozen process cannot act on the signal that asks it to stop, then
`Session.Terminate`; the locker is stopped, and `SessionRemoved` does the
rest.

A locked session can also lose its compositor while frozen: when greetd
stops, it ends the process that is the session, and the kernel ends that
process's group with it, the compositor included; but the compositor starts
the launcher in a group of its own, and a frozen process cannot end itself. logind
then tries to stop the session's scope, systemd refuses to stop a frozen
unit, and the session is left `closing` for ever, with the launcher frozen
in it and the lock screen up over nothing. So whenever a session appears
(a new sign-in screen is what greetd starting again looks like) and on
every tick, a locked session whose `State` is `closing` is *abandoned*:
both units are thawed, its scope is stopped through systemd, since logind
does not try again, and its lock screen is stopped; the audit says
`abandoned session ended`, and `SessionRemoved` does the rest.

The child's user manager outlives their session. So a locked session that
disappears on its own has its lock screen stopped and the user manager
thawed; and every child session that starts unlocked
thaws its user manager first, in case a lock whose session ended while the
daemon was away left it frozen. A frozen manager would hang the next
session's modules and its log-out.

systemd refuses to stop a frozen unit, and a frozen process cannot act on
the signal that asks it to save and go. So before `System1.Shutdown` or
`Reboot` asks logind, and when the daemon itself is asked to stop
(`SIGTERM`), every locked session's two units are thawed without being
unlocked: the lock screen keeps the display, and a daemon that starts again
finds the session locked in `usage.toml` and freezes it again.

`Lock()` from a child's session finds the caller's session by uid among the
tracked ones — not by pid, which can be reused — and locks it with reason
`requested`. `LockFor(reason)` is the session locking itself (D67), with
reason `idle`, left alone for `idle_lock_minutes` (`kidux-idle`, session.md
section 5), or `lid`, its lid closed (the launcher's `lid.py`); any other
reason is `InvalidArgument`. A lock for `idle` less than
`IDLE_LOCK_GRACE_SECONDS` (10) after the session was given the screen back
is refused with `NoSession`: it is a timer that ran out while the session
was frozen, firing as it thaws. The reason is in the audit line and in the
`Locked` signal.

## 11. Secure attention

`attention.py` opens every `/dev/input/event*` device whose capabilities
include `KEY_POWER`, the lid's switch (`SW_LID`, whose close suspends the
computer: power.md section 3), or the keyboard set `KEY_LEFTCTRL`, `KEY_LEFTALT` and
`KEY_ESC`, with `python3-evdev`, read through a GLib IO watch. The devices are
**not** grabbed: the compositor still gets every key. `/dev/input` is watched
with `Gio.File.monitor_directory` so a keyboard plugged in later is picked up.

- `KEY_POWER` pressed, or Ctrl+Alt+Escape (either Ctrl, either Alt) — with a
  tracked session unlocked: lock it with reason `power_button`. With no child
  session: emit `AttentionRequested("power_button")`, which the sign-in screen
  answers with its power dialog. Either way, whatever screen appears next is
  trusted, which is the whole point (D16).
- The lock screen itself, on these keys, does nothing: it is already the
  trusted screen.

logind gets `HandlePowerKey=ignore` from `kidux-session`, so it does not power
off before the daemon sees the key. The daemon works without that drop-in; the
guarantee needs it. A firmware long-press power-off cannot be intercepted by
anything, which is why `usage.toml` is flushed every 30 seconds.

## 12. First boot

`kidux-firstboot.service`: `Type=oneshot`, `ConditionPathExists=!/home/.kidux/config.toml`,
after `local-fs.target`, before `kidux-daemon.service` and `greetd.service`.
Runs once per machine, on the first boot after `kidux-daemon` is installed —
including the first boot of a fresh install from the phase 2 image, where the
administrator account did not exist at package build time (D18).

1. `/home/.kidux` `root:kidux-admin 0750`, with `children/` and `state/`.
2. `config.toml`: `default_language` from `LANG` in `/etc/default/locale` if it
   is a locale Kidux ships, else `en_US.UTF-8`; `default_keyboard` from
   `XKBLAYOUT` in `/etc/default/keyboard`, else `us`; `display_scale = 0`,
   automatic (D53);
   `reset_hour = 4`; `idle_lock_minutes = 5`; `screen_off_minutes = 10`;
   `save_minutes = 5`; `setup_complete = false`; `apt_statistics = true`, with
   `apt_statistics_id`, a random identifier of this machine's, and the apt
   snippet it goes into written (`kiduxd/statistics.py`, D109).
3. The GRUB recovery password: 16 characters from `secrets.choice` over
   lower-case letters and digits, hashed with `grub-mkpasswd-pbkdf2`, both
   written to `adults.toml`. Then `update-grub`, so that `session.md`'s
   `09_kidux` can pick the hash up. Done here rather than at package install
   because the password has to exist before the hardening that relies on it.
4. Every account with uid ≥ 1000 that is a member of `sudo` is added to
   `kidux-admin` (`gpasswd -a`) and audited by name. The daemon never adds
   anyone to `sudo`, so no child can arrive here.
5. Audit `first boot`.

`kidux-daemon.postinst` does the parts that belong to package installation:
`addgroup --system kidux-admin`, `addgroup --system kidux-children`, and
enabling both units. It does not touch `/home/.kidux`.

## 13. System

`Shutdown()` and `Reboot()` call logind's `PowerOff(false)` and
`Reboot(false)`. No polkit, no password: a child may always turn the computer
off, and it is the daemon calling logind, not the child, so logind's own
`power-off-multiple-sessions` policy does not get in the way.

`SleepWhenIdle() → s`, the `self` class, is what `kidux-idle` asks when a
screen is still left alone `idle_sleep_minutes`: logind's `Suspend(false)`,
as `idle_action` says and the computer can, and nothing for the screen
off only or while logind's `BlockInhibited` holds `idle` or `sleep`; it
answers what it did, "sleep" or "" for nothing, and audits a suspend
(power.md section 4). The lid's close, read with the power button
(section 11), suspends the computer as `lid_action` says, after locking
a child's session and when the lid still reads closed; and the daemon
holds a delay lock on sleep, which locks every child's session before the
computer sleeps (power.md sections 3 and 5).

`Versions() → a{sv}`, the `screens` class: every Kidux package dpkg has
installed, `kidux-*` and `python3-kidux`, and its version, from `dpkg-query
-W`; `kidux-base`'s is Kidux's. The sign-in and lock screens say it under
the logo, and the panel's System page lists each part's; empty when dpkg
cannot be read, which never stops a screen. The module packages are there
too; the Modules page reads a module's own from its manifest, and the
archive's for one on offer from `Modules1.Available`'s `offered_version`.

### Updates

Two things install packages on a Kidux machine: the jobs below, which
the panel asks for, and Debian's daily upgrade, `apt-daily-upgrade.service`,
whose `unattended-upgrades` installs Debian's security updates and
Kidux's stable suite every morning. Both keep to one rule: dpkg never
changes anything under a child's session. The daily upgrade has, from
kidux-base, a drop-in with `ExecCondition=/usr/libexec/kidux-no-child-session`,
so that systemd skips it while any member of `kidux-children` has a
session, and its result is then `exec-condition`; the daemon answers
`updating` to `Access1.CheckAccess` while it runs, as while its own job
installs; and when the last child's session ends the daemon starts it
(`StartUnit`) if its last run was skipped, the condition checked again
by systemd (D115).

The fence has no time limit, by choice. A daily upgrade that hangs keeps
children at the waiting screen until it ends or the computer restarts,
which ends it; stopping it after a while instead would kill dpkg half way
and leave packages half installed, which is worse than a child waiting.
apt's own timeouts end a download that hangs. And the condition sees
sessions logind has registered: a child the daemon has just let in and
whose session logind has not yet registered, a fraction of a second, is
not seen by a daily upgrade starting in that instant. The timer starts
it once a day, at a random moment within the hour after 06:00, so the
two meeting is left as it is.

The daemon never runs apt itself. Its unit has no network and a read-only
system (section 14), and an update can replace and restart the daemon
half-way through. So every apt job runs in a transient system unit,
`kidux-update.service`, started through systemd's `StartTransientUnit` and
running `/usr/libexec/kidux-update check` or `apply`, or `install` or
`remove` with a module's package (section 9), a script this package
ships. The script writes apt's own progress (`APT::Status-Fd`) and its
verdict, one `kidux:` line, to `/run/kidux/update.status`; the daemon
watches the file and turns it into signals. The unit's fixed name is what
makes two jobs at once impossible: systemd refuses the second, and the
daemon answers `Busy`.

- `System1.CheckUpdates(token)`: `apt-get update`, then a simulated
  `dist-upgrade`. Answered by the signal `UpdatesChecked(u count, as
  packages, s error)`. Allowed while children have sessions: it changes
  nothing.
- `System1.ApplyUpdates(token)`: `dpkg --configure -a` first, so a power cut
  in an earlier update is finished before anything new starts; then
  `apt-get -y dist-upgrade`, non-interactive, keeping edited configuration
  files, and waiting up to ten minutes for apt's lock, which
  the daily upgrade may hold. Refused with `SessionActive` while any
  child session exists, locked or not: dpkg must never replace the launcher
  or a module under a running session. `UpdateProgress(d fraction, s
  package)` while it runs; `UpdateFinished(s outcome, s detail)` at the end,
  outcome `updated`, `up-to-date`, `restart-needed` (`/run/reboot-required`
  exists) or `failed`.
- `kidux-update install <package>` and `remove <package>`, for section 9:
  the script checks again that the package is `kidux-module-` and a module
  id, since it runs as root, and otherwise writes `failed:not a module`
  and stops; `tests/project/module-jobs.sh` tries it with every kind of
  wrong name. `install` is `dpkg --configure -a`, `apt-get update`, then
  `apt-get install --no-install-recommends` of that package, with the lock
  timeout, the status descriptor and the configuration-file options of
  `apply`; `remove` is `apt-get purge --auto-remove` of that package: the
  module, and with it what was installed for it alone and nothing else
  needs, Thunderbird and its language packs after Mail, say (D100); the
  children's own files under their homes stay theirs. A module that is
  only a folder, `/usr/share/kidux/modules/<id>/` with no package of
  that name known to dpkg, as the tests' stand-ins are, has nothing for
  apt to purge: `remove` takes the folder away and writes Chromium's policy
  again, as a package's removal triggers it, and says `done:removed`
  (D101). The daemon could not do it itself: its system is read-only to
  it (section 14). The
  verdict is `done:installed`, `done:removed` or `failed:<apt's last
  line>`; a `kidux:module:<package>` line says which package, so that a
  daemon restarted mid-job still audits the right module.
- `System1.UpdateState() → (s job, d fraction, s package, s outcome, s
  detail, as packages)`, `screens` class: the job, `idle`, `checking`,
  `applying`, `installing` or `removing`, how far it has got and the package it is on; and the last
  job's outcome, `checked` or one of `UpdateFinished`'s, with its detail and,
  after a check, the packages it found. The panel asks it once a second
  while a job runs, which also carries it across a restart of the daemon,
  when it cannot be asked for a moment; the signals are there for anything
  else that listens.

The status file is `/run/kidux/update.status`, in the daemon's
`RuntimeDirectory`, which is kept across a restart of the daemon
(`RuntimeDirectoryPreserve=yes`). If the daemon is restarted by the update,
it finds the unit still running and the status file still there when it
comes back, and carries on watching; a unit that has already ended leaves its verdict in the file,
which is emitted once and deleted. The panel listens for the signals on the
bus name, so it survives the restart too; only its token dies with the
daemon (section 4), and the next thing the adult does asks for the password
again. Our own packages never restart greetd (`session.md`), so an update
never ends anyone's screen. `update check`, `update started` and `update
finished` are audited, the last with its outcome.

## 14. The unit

The programs are `/usr/libexec/kidux-daemon`, `/usr/libexec/kidux-firstboot` and
`/usr/libexec/kidux-update`: nothing a person types.

```ini
[Service]
Type=dbus
BusName=org.kidux.Daemon1
ExecStart=/usr/libexec/kidux-daemon
Restart=on-failure
RestartSec=1
RuntimeDirectory=kidux
RuntimeDirectoryPreserve=yes

# It keeps the family's state, manages the children's accounts and asks
# logind and polkit things. Everything below is a wall around exactly that.
ProtectSystem=strict
ReadWritePaths=/etc /home /var/log
ProtectHome=no
PrivateTmp=yes
ProtectKernelTunables=yes
ProtectKernelModules=yes
ProtectKernelLogs=yes
ProtectControlGroups=yes
ProtectClock=yes
ProtectHostname=yes
RestrictRealtime=yes
RestrictNamespaces=yes
LockPersonality=yes
DevicePolicy=closed
DeviceAllow=char-input r
RestrictAddressFamilies=AF_UNIX AF_NETLINK
NoNewPrivileges=yes
SystemCallFilter=@system-service
SystemCallErrorNumber=EPERM
```

`/etc` as a whole, because adduser, chpasswd and deluser rewrite
`/etc/passwd` and its siblings by renaming files inside it; `/var/log` for
useradd's login records. Input devices are read, never written. The daemon
never speaks to the network: updates run in a unit of their own (section 13).
First boot runs in its own unit without these walls, because `update-grub`
writes `/boot`. `PrivateTmp` gives the daemon a `/tmp` of its own, so no
program the daemon runs may wait for an answer through a socket under
`/tmp`: whatever would answer cannot see it, and the program waits out its
own timeout. `wpa_cli` is such a program (its reply socket is
`/tmp/wpa_ctrl_*`), which is why the Network page asks `iw` (section 16).
Each line is tested by the thing it could break: `Create`,
`SetChildPassword`, the lock and first boot. A line that breaks one of them is
loosened and the reason is written next to it, not removed silently.

The introspection XML is shipped inside the Python package and in
`/usr/share/dbus-1/interfaces/`, and holds exactly the methods the daemon
answers: interfaces are added to it as they are built, and a test fails if a
method in it has no polkit decision in `gate.py`.

The D-Bus policy, `/usr/share/dbus-1/system.d/org.kidux.Daemon1.conf`, lets
root own the name and lets everyone send to it: polkit decides, not the bus.
The activation file, `/usr/share/dbus-1/system-services/org.kidux.Daemon1.service`,
names `kidux-daemon.service` as `SystemdService`.

## 15. The machine's settings

- `Daemon1.GetConfig() → a{sv}`: `default_language`, `default_keyboard`,
  `display_scale`, `reset_hour`, `setup_complete`, `language_chosen`,
  `chromium_flags`, `pointer_speed`, `scroll_speed`, `idle_lock_minutes`,
  `screen_off_minutes`, `save_minutes`, `apt_statistics`, `lid_action`,
  `idle_action`, `idle_sleep_minutes`, and `can_sleep`, whether the
  computer can suspend (power.md). The
  trusted screens run as `_greetd`, which cannot read `config.toml`, and they
  need the scale and the language before they draw anything. `screens` class.
- `Daemon1.SetConfig(token, changes a{sv})`, `manage` class: any of
  `default_language` (one of the shipped locales), `default_keyboard` (the
  pattern of section 6), `display_scale` (0, automatic, or 1.0 to 3.0),
  `setup_complete` (a boolean), `chromium_flags` and `pointer_speed` and
  `scroll_speed` (below), `idle_lock_minutes`
  (a whole number, 1 to 120) and `screen_off_minutes` (1 to 240), the
  minutes a session may be left alone before it locks and before the screen
  turns off (D67), `save_minutes` (1 to 15), how long *Unlock to save*
  gives, which no page offers and the session tests set, and
  `lid_action` (`sleep` or `nothing`),
  `idle_action` (`sleep` or `screen_off_only`) and `idle_sleep_minutes`
  (1 to 240), the power settings (power.md, D119),
  `apt_statistics` (a boolean), whether every fetch of the archive carries
  an identifier of this machine's, `apt_statistics_id`, made once and kept:
  `/etc/apt/apt.conf.d/61kidux-statistics` written or removed at once
  (`kiduxd/statistics.py`, D109). Anything else, the
  reset hour included, is
  `InvalidArgument`: nothing offers to change it. Setting a language
  also sets `language_chosen`, which is how the first-run wizard, restarted
  to apply a new keyboard, knows it is past its first two steps. Audited
  with the names of the fields.

  `chromium_flags` is the first of the machine's advanced settings, what
  depends on its hardware (`kiduxd/advanced.py`, D51, D52): a list of at
  most 20 flags for Chromium, each `--name` or `--name=value`, lower-case
  name, no spaces or control characters, at most 200 characters, blank
  ones dropped; and none that would take a web module out of Kidux's hold
  (D36), the list in `kiduxd/advanced.py`: another page, profile or window
  (`--app`, `--app-id`, `--kiosk`, `--user-data-dir`, `--profile-directory`,
  `--incognito`, `--guest`, `--new-window`, `--homepage`), the
  `--remote-debugging-*` doors, extensions (`--load-extension`,
  `--disable-extensions-except`, `--enable-remote-extensions`), the sandbox
  in whole or in part (`--no-sandbox`, `--single-process`, `--no-zygote`,
  `--disable-setuid-sandbox`, `--disable-seccomp-filter-sandbox`,
  `--disable-namespace-sandbox`), the web's own rules
  (`--disable-web-security`, `--allow-file-access-from-files`,
  `--allow-running-insecure-content`, `--ignore-certificate-errors`,
  `--unsafely-treat-insecure-origin-as-secure`,
  `--disable-site-isolation-trials`), and another way to the network (the
  proxy flags, `--host-resolver-rules`, `--host-rules`, the auth-server
  lists). Anything else is
  `InvalidArgument`, and nothing changes. Saved, the list is also written
  to `/etc/kidux/chromium-flags` (`paths.CHROMIUM_FLAGS`), root's and 0644,
  one flag a line, and the file removed when the list is empty:
  `kidux-webapp` runs as the child and reads the file, not the daemon.

  `pointer_speed` and `scroll_speed` are the others: the pointer's speed
  and the touchpad's two-finger scroll, a whole number from -2 to 2 each,
  slower to faster, 0 by default (`kidux.pointer`; phase-4c-plan.md,
  4.19). Saved, either is also written, with the other, to
  `/etc/kidux/input.xml` (`paths.INPUT_XML`), root's and 0644, as the
  `<libinput>` part of labwc's configuration, libinput's pointer speed for
  every pointer and labwc's scroll factor for a touchpad: a child's
  session reads the file when it starts (session.md section 3). Without
  the file a session takes the middle steps, so the machine has them
  before an adult chooses any.

  On a machine with no adult password yet, the language and the keyboard,
  and only those, may be set with an empty token, as `SetPassword` allows
  the first password: the wizard sets them before the password, so that the
  password is typed in the keyboard it will always be typed in (D29).
- `Parental1.GetRecoveryPassword(token) → s`, `manage` class: the GRUB
  recovery password (section 5), for the adult to read off the panel. An
  empty string if first boot has not made one. Audited, without the
  password.
- `Daemon1.AttentionRequested(s source)` signal: section 10.

All are part of version 1; `kidux.client.Client` has a method for every call
the screens make.

## 16. The network

The panel's Network page (panel.md section 3, D62) reads and changes the
machine's network through `Network1`, `kiduxd/network.py`. Every method is
the `manage` class and takes the panel's token: a child reaches none of
them, and the page is in no screen a child can open.

- `Network1.GetNetwork(token) → (a{sv} summary, aa{sv} interfaces, aa{sv}
  networks)`. The interfaces, from `ip -j addr`: every one but the loopback
  with a device behind it or an IPv4 address (`name`, `kind` wifi,
  ethernet or other, `up`, `address`, `managed` by NetworkManager, and for
  a Wi-Fi its `network` and `signal`). A Wi-Fi NetworkManager manages is
  named by `nmcli device status`; one it does not, a Wi-Fi `ifupdown` set
  up when Debian was installed, by `iw dev <name> link` (netlink, which
  the unit allows), its signal from `/proc/net/wireless`. The summary: whether NetworkManager runs
  (`manager`), whether there is a Wi-Fi (`wifi`) and whether it can be
  changed here (`wifi_changeable`: NetworkManager manages it), the default
  route's `gateway` and its interface, the router's answer (`router`,
  `answers` or `silent`, "" before it has been asked or when the gateway
  has changed since), the job running (`job`: idle, checking, connecting,
  forgetting), and how the last one ended (`outcome` connected, failed or
  forgotten, the `ssid` it was about and the `detail`, `wrong_password` or
  nmcli's own sentence). The networks, only when the Wi-Fi can be changed,
  from `nmcli device wifi list --rescan no`: each once, at its strongest,
  hidden ones left out, the one in use first (`ssid`, `signal`, `secured`,
  `security` open, psk, sae or unsupported, `active`, `known`: a saved
  connection has its name).
  `GetNetwork` answers in well under a second, inside the greeter's ten;
  the session test `23-network.py` holds it to five with a Wi-Fi as the
  Debian installer leaves one.
- `Network1.Check(token)`: looking again, a job: a Wi-Fi scan when
  NetworkManager runs, waited for (`nmcli device wifi list --rescan yes`
  returns when the scan is done, where `wifi rescan` only asks for it, and
  a card takes a few seconds), so that the page reads a fresh list when
  the job ends; and one ping of the gateway. The unit
  may not open an internet socket (`RestrictAddressFamilies`, section 14),
  so the ping runs outside it, in a transient unit as a dynamic user:
  `systemd-run --wait --collect --pipe -p DynamicUser=yes -p
  ProtectSystem=strict -p PrivateTmp=yes ping -n -q -c 1 -W 1 <gateway>`.
- `Network1.ConnectWifi(token, ssid, password)`: joining a network, a job.
  Checked first, so that the panel hears at once: the network is in reach,
  its name 1 to 32 bytes, and its password what its security takes (for
  WPA personal, what NetworkManager itself takes: printable and 8 to 63
  bytes long, an accented letter counting as two, or the key's own 64 hex
  digits; 1 to 128 characters for WPA3 alone; none for an open one); an
  enterprise or WEP network is
  refused. A network with a saved connection and no new password is joined
  with it (`nmcli connection up`); otherwise the daemon writes a connection
  file of NetworkManager's own, `/etc/NetworkManager/system-connections/
  kidux-<uuid>.nmconnection`, root's and 0600, for the whole machine, so
  that the Wi-Fi comes up before anyone signs in, loads it and brings it
  up, with a wait of 40 seconds. The password is in that file and nowhere
  else: on no command line, where `ps` would show it to any user, and in
  no audit line. Joined, the older connections to the same network go;
  not joined, the new file goes, so that a wrong password is not kept, and
  `Secrets were required` in nmcli's answer is `wrong_password`. Audited:
  `wifi join` started with the caller, then `wifi joined` or `wifi join`
  failed, with the network's name.
- `Network1.ForgetWifi(token, ssid)`: every saved connection to the network
  deleted, a job; audited as `wifi forgotten`.

One job at a time, in a thread of its own, which never touches the bus:
the panel asks `GetNetwork` once a second while one runs. A second job
while one runs is `Busy`. Without NetworkManager, or with a Wi-Fi it does
not manage, the page has the facts and nothing to change, and says why.

## 17. Testing

Three layers, and a change is not done until all three pass.

**Unit**, `pytest`, milliseconds: `access.py` against the fake clock, every
scenario in section 7; `tokens.py` expiry and rebinding; `children.py`
validation and the rollback path with `FakeAccounts`; `adults.py` hashing and
rehash.

**Integration**, `pytest` with `python3-dbusmock`, seconds: the real daemon on
a private system bus, with dbusmock's `logind`, `polkitd` and `systemd`
templates standing in for the machine and `FakeAccounts` for `adduser`. Covers:
unlock and a second connection trying to reuse the token; a child calling
`Usage` about another child; `Delete` of a user not in `kidux-children`;
`Create` end to end; `SessionNew` starting the clock and `SessionRemoved`
stopping it; the lock sequence calling `StartUnit`, `SwitchTo`, `FreezeUnit` in
that order; the fallback to `Terminate` when `SwitchTo` does not take.

**Machine**, the VM, minutes: `ci/vm/` runs, on a clean Debian with the
packages installed, the administrator creating children over one D-Bus
connection (`kidux-as`), `pamtester login <child> authenticate` accepting the
password, and the time-and-lock run on real logind and systemd
(`tests/acceptance/05-time-and-lock.py`): a `daily` child with
one minute, in a real session on terminal 5, is locked when it runs out — the
seat switched to terminal 8, the session's scope frozen, locked time not
counted — an adult grants more from the lock screen and everything is thawed
and switched back, the child locks themselves and continues with their own
password, the daemon is restarted mid-session and loses nothing, `date -s`
moves to the next day and the child continues with a fresh allowance, and an
adult logs the child out. The audit log is read back for every event, in
order.

The acceptance VM never boots into Kidux: it tests the daemon on real
logind and systemd without a screen. So its seed replaces
`kidux-locker@.service` with a stand-in of the same name, a placeholder on
terminal 8 with a logind session of class `greeter`, which is everything the
daemon checks for, and makes the child's session the way greetd makes one, a
PAM session with `pam_systemd` in it, from a unit on terminal 5. The power
button, the `chvt` denial and the real lock screen are the session VM's
(`tests/run session`), which presses keys from outside the machine.
