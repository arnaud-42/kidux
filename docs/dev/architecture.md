# Architecture and decisions

Single source of truth for the technical design, checked against Debian trixie and the
upstream projects it names. Every non-obvious choice is in the decision log at the end;
add to it, do not rewrite history.

## 1. Goals that shape the design

1. **Public distribution.** Anyone must be able to download an ISO, write it to a USB
   stick and install it on an old computer without Linux knowledge.
2. **Upgradable without data loss.** Security updates, feature updates and even a
   Debian major-version upgrade or a full reinstall must keep the children's work and
   the adults' configuration.
3. **Safe by default.** The child boots into a kiosk and cannot leave it. Changing
   what a child may do requires the adult password, which is only ever typed on a
   screen the child's session cannot forge (D6).
4. **Bilingual from day one, multilingual by design.** English and Spanish ship
   together; a new language is a translation job, never a code change.
5. **Light.** Runs on 64-bit hardware from about 2008 with 2 GB of RAM, 4 GB
   recommended.
6. **Reproducible.** Every byte on the user's disk comes from this repository or from
   Debian, through packages and a scripted image build.

## 2. Base system

| Item | Decision | Notes |
|---|---|---|
| Distribution | Debian 13 "trixie" (13.7 as of 2026-09-12) | Full support until 2028-08, LTS until 2030-06. Debian 14 "forky" is expected around mid-2027; plan the first major upgrade for then. |
| Architecture | `amd64` only | trixie dropped the i386 installer and kernel; "old hardware" therefore means any 64-bit x86 CPU (Intel Core 2 and later, 2007+). |
| Kernel | Debian's `linux-image-amd64` (6.12 LTS in trixie) | Firmware from `firmware-linux` and friends; the official trixie images already ship non-free firmware. |
| Boot | Hybrid ISO: UEFI and legacy BIOS | Old PCs are BIOS-only; newer ones are UEFI with Secure Boot, which works through Debian's signed shim. |
| Init | systemd | Needed for `greetd`, logind sessions and `systemd-run` scopes. |
| Display stack | Wayland: `cage` 0.2 for the trusted screens, `labwc` 0.8 for a child's session, with XWayland for a module made for X11 (D58) | See section 5. No Xorg server. |
| Minimum hardware | 64-bit CPU, 2 GB RAM (4 GB recommended), 32 GB disk, 1024x768 | Chromium running the Scratch editor is the heaviest module and needs the 4 GB. |

## 3. Delivery, packaging and upgrades

Three package sources, in order of preference:

1. **Debian trixie archive** (`main`, `contrib`, `non-free-firmware`, `non-free`).
2. **Our apt repository** (`kidux`): everything we write, plus anything we repackage.
   Signed and built with `reprepro` on the development machine. Suites: `stable`,
   which a family's machine follows, published at `https://apt.kidux.org` on a
   web hosting of the project's own, whose logs count the machines that follow
   it, and `testing`, served from the development machine over the LAN for the
   machines that test; each signed with its own key (D2, D82, D109).
3. **Flatpak (Flathub)** is *not* used. It stays documented as plan B (TurboWarp
   Desktop) only if self-hosting the official Scratch editor proves unworkable.

Everything we build is a `.deb` under `packages/`:

- `kidux-archive-keyring` — our signing key in `/usr/share/keyrings/` and the deb822
  `/etc/apt/sources.list.d/kidux.sources`. Nothing else configures the archive, and
  `kidux-base` cannot depend on an unsigned one.
- `kidux-base` — metapackage: depends on the whole system (kernel, firmware, fonts,
  `locales` with every shipped locale generated, `unattended-upgrades` configured for
  our suite, and the packages below).
- `kidux-common` — the Python library `kidux`, shared by everything we write: paths,
  state file I/O, i18n bootstrap, logging, the D-Bus client, the shared GTK widgets and
  the avatar set. It exists so that greeter, locker, launcher and daemon never each own
  a copy of the state format.
- `kidux-daemon` — privileged D-Bus service that does everything requiring root: the
  adult password, child accounts, access policy, time accounting, the lock machinery,
  the secure-attention keys and system updates.
- `kidux-session` — everything that turns a plain Debian install into the kiosk:
  `greetd` configuration, the session wrapper, the locker unit, `cage` for the
  trusted screens and `labwc` for a child's, and every hardening drop-in. Split out from `kidux-base` so the hardening can be installed,
  inspected and removed as a single unit, which is what makes it safe to test.
- `kidux-greeter` — the trusted screens: the sign-in screen, the lock screen, and the
  adult panel and first-run wizard once they exist. One program, run by `greetd` on
  terminal 7 and by the locker unit on terminal 8, always as `_greetd`.
- `kidux-launcher` — the child's full-screen launcher, the only program a child's
  session runs.
- `kidux-webapps` — local static web server plus a Chromium application window, shared by
  every module that is a web application (Scratch, MakeCode, micro:bit Python
  Editor). It is infrastructure, not a module: adults never see it.
- `kidux-module-<name>` — one per learning module (manifest, content, dependencies).
  Each module is independent: it can be installed, enabled, disabled and removed on
  its own from the adult panel, even when several share `kidux-webapps`.
- `kidux-installer-branding` — Calamares configuration and branding for the ISO.
- `kidux-l10n-<lang>` — optional split of heavy per-language content, if needed.

**Upgrade paths:**

| Kind | Mechanism |
|---|---|
| Security updates | `unattended-upgrades` enabled for Debian security and our `stable` suite. Silent, and never under a child's session (D115). |
| Feature updates | The adult panel's *System* page looks for updates and installs them through `kidux-daemon`, which runs apt in a unit of its own, and never while a child has a session (`daemon.md` section 13). |
| Debian major version (trixie → forky) | `kidux-upgrade` tool: rewrites sources, runs the upgrade, reboots. Offered from the panel once we have tested it. |
| Reinstall | Boot the ISO, choose "Reinstall, keep my data": the installer formats `/` only and mounts the existing data partition. |

## 4. Disk layout and where data lives

Guided layout applied by the installer (GPT on both UEFI and BIOS machines):

| Partition | Size | Mount | Purpose |
|---|---|---|---|
| ESP (UEFI) or BIOS boot | 512 MB / 1 MB | `/boot/efi` | Bootloader. |
| system | 24 GB (min 16) | `/` | Debian + our packages. Formatted on reinstall. |
| data | rest of disk | `/home` | Never formatted on reinstall. |
| swap | file on `/` | — | Sized to RAM up to 4 GB, created by the installer (phase 2). |

Both are ext4. Btrfs snapshots were considered and rejected for now (see decision log).

**Rule: anything that must survive a reinstall lives on the data partition.**

- Each child is a Linux user with a normal home directory under `/home/<child>`.
- Everything the system knows about the family lives in `/home/.kidux/` (root-owned,
  group `kidux-admin`, mode `0750`), so a reinstall that keeps `/home` restores the
  exact previous configuration *and* the same time accounting. `kidux-daemon` is its
  only writer, and no child can read it.
- A child's password is **not** kept there: it is their Unix password in `/etc/shadow`,
  set by the daemon (D10).
- Nothing of value is kept in `/var/lib`; it may be regenerated from `/home/.kidux/`.

What that directory holds:

```
/home/.kidux/
  config.toml                 schema version, default language and keyboard for the
                              trusted screens, display scale, daily reset hour
  adults.toml                 argon2id adult password hash, GRUB recovery password
  state/audit.log             every privileged action, every grant, every attempt
  children/<user>/
    profile.toml              display name, language, keyboard, age, avatar
    access.toml               mode, daily_minutes, days of the week, granted bank
    usage.toml                last date seen, seconds used today, session state
    modules.toml              enabled modules
```

Every file carries a `schema_version`: the daemon refuses to start on a newer schema
and migrates older ones. Writes are atomic (`tempfile` + `os.replace`), and `usage.toml`
is flushed every 30 seconds while a session is unlocked, so a power cut, a crash or a
deliberate reboot cannot reset a child's daily counter.

## 5. Sessions, users and kiosk hardening

### Four screens, two of them trusted

| Screen | Runs as | What it is |
|---|---|---|
| **Sign-in screen** (the *greeter*) | `_greetd`, trusted | What the machine boots into: the children's avatars, an "Adult" button and a power button. Each child enters with their own password. |
| **Lock screen** (the *locker*) | `_greetd`, trusted | Appears over a running session when time is up, when the child locks, or when anyone presses the power button. The session underneath is frozen, not ended. |
| **Launcher** | the child | The only application a child's session runs. |
| **Adult panel** | `_greetd`, trusted | Reached from either trusted screen with the adult password. Modal: while it is open nothing else is reachable, and leaving it re-locks. |

Two rules follow from this split:

- **The adult password is only ever typed on a trusted screen**, never inside a child's
  session, because everything in that session runs as the child, and a child who can
  run code (phase 6 gives them Python on purpose) could draw a convincing fake prompt
  and capture it.
- **The adult password gates changing what a child may do; the child's own password
  gates being that child.** Neither is ever needed to use a module that is already
  enabled inside an allowed session.

### Accounts and groups

Nothing we ship depends on a particular user name. It depends on groups (D18).

| Account | Created by | Purpose |
|---|---|---|
| Administrator | the installer, named by whoever installs the machine | `sudo`, SSH, recovery and maintenance. This is **not** "the Adult" of the interface. |
| One user per child | `kidux-daemon`, from the panel or the first-run wizard | The child's session. Shell `/usr/sbin/nologin`, never in `sudo`, home under `/home/<child>`. |
| `_greetd` | the `greetd` package | Runs the trusted screens. |

| Group | Created by | Grants |
|---|---|---|
| `kidux-admin` | `kidux-daemon.postinst`, `addgroup --system` | Read access to `/home/.kidux/` and, through polkit, every daemon method. |
| `kidux-children` | `kidux-daemon.postinst`, `addgroup --system` | Only what a child needs: their own usage and module list, lock, power off and reboot. |

At first boot, `kidux-firstboot.service` adds every human account (uid >= 1000) that is
a member of `sudo` to `kidux-admin`, and records it in the audit log. That is the one
link between the installer's account and our state directory, and it lets our packages
work without ever knowing that account's name. It cannot help a child, because the
daemon never puts a child in `sudo`.

**The Adult is a password, not an account.** It lives hashed in
`/home/.kidux/adults.toml` and is verified by the daemon. There is no adult session,
no adult desktop and no adult login; "Exit to desktop" is deliberately out of scope
(D7).

### Login and sessions

- The machine boots into **our own greeter**: `greetd` runs `cage` with
  `kidux-greeter` in it, through the wrapper that gives both trusted screens the
  machine's display scale and keyboard layout. There is no auto-login (D10).
- A child's password is their **Unix** password, and `greetd` runs the PAM
  conversation; we never re-implement login. Trixie's `/etc/pam.d/greetd` includes
  `login`, which has no `pam_shells`, so a shell of `/usr/sbin/nologin` blocks
  terminals without blocking the graphical session, and `pam_faildelay` adds a
  three-second penalty per failed attempt for free.
- Once the password is accepted, the daemon's `CheckAccess` decides what happens next:
  straight in, ask an adult to authorise, or explain that the time is spent. A wrong
  password and a spent limit are never confused for one another.
- The session is `/usr/libexec/kidux-session`. The child's language, keyboard and
  display scale arrive in its environment from the sign-in screen, through greetd
  (D24); it applies them and `exec`s `labwc` with Kidux's own configuration, which
  starts the launcher and nothing else (D58).
- Switching child is "one logs out, the other logs in" (D9). Every child gets real
  separation, and the sign-in screen becomes the single place where access rules are
  applied.

### Access control

Three modes per child, enforced by `kidux-daemon` and never by anything running as the
child, because anything the child's session owns, the child can eventually kill (D11).

| Mode | Meaning |
|---|---|
| `unlimited` | Nothing to enforce. |
| `daily` | A number of minutes per day, reset at 04:00 local time. |
| `manual` | No session unless an adult grants time. |

- **Time up warns, then locks; the system never ends a session on its own** (D12).
  Warnings at 10, 5 and 1 minute, then the trusted lock screen appears and the child's
  session scope is frozen underneath. From there an adult can give more time, unlock
  briefly so the child can save, or log the child out. Unsaved work is never destroyed
  by a timer.
- **The counter is wall-clock time while the session is unlocked**, with no idle
  detection (D13); locked time does not count. The consequence has to be said plainly
  to families: a session left unlocked over dinner spends the day's time. That is why
  the launcher's "Lock" button is prominent.
- **Granted time is a bank, spent only by use** (D14). In `manual` mode a grant survives
  across sessions and days; in `daily` mode an extra grant dies at the 04:00 rollover.
- The day rolls over only when the calendar date is **later** than the one recorded, so
  a clock moved backwards never resets a counter, and in-session accounting uses the
  monotonic clock. A jump of more than a day in either direction is audited.
- **No lock-out on the adult password** (D15); every attempt is audited instead. Only
  someone at the keyboard can attempt one at all, because of the trusted-screen rule.

### Secure attention

The power button and Ctrl+Alt+Escape always bring up the trusted lock screen (D16). The
daemon reads the input devices directly, so nothing the child runs can intercept them,
and logind is configured with `HandlePowerKey=ignore` so it does not power the machine
off first. This is what makes the trusted-screen rule usable in practice: an adult
presses the power button *before* typing their password, and whatever screen appears is
real. It also means the power button can never turn the machine off without a screen
that asks.

### Why Wayland

Under X11 any application can read every keystroke and inject input into other windows,
so a kiosk on X11 is only cosmetic. The trusted screens run under `cage`, which shows
one maximized application and nothing else. A child's session runs under `labwc`, so
that several modules can be open at once and the child learns to move between them,
with a configuration of Kidux's own: no keys but the four that go home, to the window
used before and close, no menu, and the launcher's bar always on top through the
layer-shell protocol (D58). XWayland is there for a module made for X11: X11 programs
of one child see one another, and nothing else of Kidux's.

### The security boundary

**The child's Unix user is the boundary, not the launcher** (D17). Everything the
child's uid can do, assume the child will do. The kiosk is a user-experience boundary;
the privilege boundary is enforced by the kernel, PAM, polkit and the daemon.

Escape hatches closed, all shipped as packaged drop-ins in `kidux-session`:

- Extra virtual terminals disabled (`NAutoVTs=0`, `ReserveVT=0`, and every
  `getty@tty*` conditional on `kidux.console` being on the kernel command line,
  which only the GRUB menu behind the recovery password can add);
  `ctrl-alt-del.target` masked; `kernel.sysrq=0`.
- `KillUserProcesses=yes`, so a child's processes cannot outlive their session, and
  `kernel.yama.ptrace_scope=2`, so one process of the child cannot read or control
  another. Both override a trixie default that is too permissive for us.
- The child cannot return to their own session from the lock screen: `/dev/tty*` is
  root-only, and the polkit action `org.freedesktop.login1.chvt` — whose trixie default
  lets an inactive session activate itself — is explicitly denied to `kidux-children`.
- Child users: no `sudo`, shell `/usr/sbin/nologin`, `DenyGroups kidux-children` in
  sshd, and polkit denying everything except powering off, rebooting and mounting
  removable media (needed for micro:bit).
- GRUB: a single unrestricted Kidux entry, menu hidden behind a one-second timeout,
  and a superuser password on every other entry and on the editor and shell (D25). The
  recovery password is generated at first boot and written to `/home/.kidux/adults.toml`
  *before* the hardening is applied. Families are told to set a firmware password in the
  install guide.
- Every module runs in its own `systemd-run --user --scope`, which caps its memory,
  ends it cleanly and is frozen with the session under the lock screen (D32, D40).
  There is no sandbox around a module: it runs as the child, and the child's Unix
  user is the boundary (D42).
- `labwc`'s configuration is Kidux's and read-only to the child, and the only one it
  reads; it binds no key to a terminal or a launcher and shows no menu, and
  `kidux-session` conflicts with `foot`, `wmenu` and every `x-terminal-emulator`, so
  that none is installed. What the child's processes can ask the compositor through
  the foreign-toplevel protocol, the launcher's way to its windows, the child can do
  with the frame and the keys already.
- **SSH is never touched for administrators.** It is the recovery path on every machine
  and the maintenance path on the development machine.

### What Kidux defends against, and what it leaves alone

Kidux is a child's first computer, not a hardened appliance. The level it
aims at is a well-kept Debian's: the child is an unprivileged Unix user with
no shell, no browser outside a module's wall, no `sudo` and no way to another
session, and everything above that is the kernel's, PAM's, polkit's and the
daemon's. A child able to defeat that has outgrown Kidux (D108). So a reader
auditing the system finds these as they are on purpose, each with its
decision:

- **Chromium's `DeveloperToolsAvailability` is 1, not 2** (D91). `kidux-webapp`
  signs a child in to a website through `--remote-debugging-pipe`, which 2
  refuses as well. The tools' own pages are addresses the policy's
  `URLBlocklist` of `*` blocks, so F12 and Ctrl+Shift+I open nothing, which
  session test 32 checks.
- **polkit says yes to `_greetd` for every `org.kidux.daemon.*` action** (D27).
  `_greetd` is the sign-in screen, the lock screen and the adult panel, the
  trusted screens; polkit never sees a call's arguments, so which child a call
  may touch is the daemon's decision, with the adult's token where one is due.
  Narrowing the rule would move nothing: whoever runs as `_greetd` is the
  trusted screens already.
- **A web module's proxy bypass list names the server at `127.0.0.1:8123`
  and the module's hosts**, and the proxy at `127.0.0.1:1` answers nothing
  (D36, D85). It is a wall, not a filter: there is no filtering proxy to
  reach.
- **The GRUB recovery password is kept in clear beside its PBKDF2 hash**, in
  `adults.toml`, `root:kidux-admin 0640` (D25). It is what an adult reads off
  the panel when the machine will not boot; a hash cannot be read off a
  panel, and the people who may read the file are exactly those who may know
  the password.
- **labwc's keys signal the launcher with `pkill -f`** (D45, D57, D64). labwc
  has no socket of its own; the launcher is where Close, Home and Alt+Tab are
  decided, so labwc's native `Close` or `NextWindow` would go round that
  policy. The pattern is anchored to the launcher's command line, a child's
  `pkill` reaches the child's processes alone, and a fork per key press costs
  nothing a child notices.
- **A native module, KDE's Kig, Kalzium or Step, runs as the child with no
  sandbox** (D42). The child's home is the module's, and the child's Unix
  user is the boundary; bubblewrap or AppArmor around each program would be
  a profile to keep per program and per upgrade, for a boundary the kernel
  already holds. The internet those programs could reach is closed by their
  own configuration and by `kidux-closed` (D107).
- **A module is a Debian package** (D31, D42), never a bundle of its own
  format: trixie's packages, one archive, one upgrade path, one place to
  look.

## 6. Module framework

A module is a Debian package `kidux-module-<name>` that installs a manifest:

```toml
# /usr/share/kidux/modules/scratch/module.toml
id = "scratch"
version = "1.0.0"
name = "Scratch"                  # English; translated through i18n_domain
description = "Make games and stories with blocks."
min_age = 7
max_age = 14
launch = { webapp = "scratch" }   # or { exec = "..." } for native apps
categories = ["programming"]
i18n_domain = "kidux-module-scratch"               # gettext domain for name/description
```

Beside it, `icon.svg`, the tile's picture. modules.md is the contract in full.

- **State** per child in `/home/.kidux/children/<user>/modules.toml`
  (`enabled = ["typing", "scratch"]`), written only by `kidux-daemon`.
- **Install/enable are separate.** Installing a module is an apt operation done by the
  daemon (`apt install kidux-module-x`); enabling it is a state change; removing it is
  `apt purge`. The panel offers all four actions per module and per child. All modules
  ship pre-installed on the ISO, but the panel also lists modules available from the
  apt repository that are not installed yet.
- **Web-app modules** declare `launch = { webapp = "<id>" }`. The package installs its
  static files under `/usr/share/kidux/webapps/<id>/`; `kidux-webapps` serves them
  on `127.0.0.1:8123` and the launcher opens a Chromium application window
  (`--app`) on that URL, held to it by the managed policy (D36, D44). One
  module's files never depend on another's, so removing Scratch leaves MakeCode
  intact. Chromium is used (not Firefox) because micro:bit flashing needs WebUSB.
  A third kind of launch, `launch = { web = "https://…" }`, is a door to one
  website on the internet, opened the same way (D85). Every web module's
  Chromium is walled in by a proxy that answers nothing, past which only the
  server and the hosts its manifest names (`hosts`) are reached, and the
  managed policy is written from the installed modules' hosts by a dpkg
  trigger (modules.md section 4).
- **Files.** The child's home is shared by every module: what a child makes in one
  is there for the next (D42). A module's own settings, data and cache go in three
  XDG directories of its own under the child's home, apart from every other
  module's; removing a module leaves them, for when it is installed again (D89).
  Web-app modules get a per-module Chromium
  profile directory and are held by Chromium's policy (D36).
- **On screen.** Each open module's window fills the room above the launcher's
  bar under `labwc`, and the bar takes the child between them and closes the one
  on screen, asking it first (D45, D58). For a child an adult switches windows on,
  every window is in labwc's frame, to be moved, resized, minimised, maximised and
  closed, several in view at once; a module whose manifest says `needs_windows` is
  only for such a child (D46, D57). Chromium's flags for the machine's graphics are an advanced setting of
  the machine (D51, D52).
- **Progress.** Modules that report progress write JSON to
  `~/.local/share/kidux/progress/<module>.json`; the panel reads it (future).
- **Reference module** `kidux-module-hello` validates the framework before any real
  content is written.

## 7. Internationalization (i18n)

The rule is simple: **no user-visible string outside the i18n layer**, in the launcher,
the panel, the installer, the modules and the lesson content.

- **Software strings:** GNU gettext. Domain `kidux` for launcher and daemon, one
  domain per module. Source in English, `po/es.po` maintained alongside; a CI check
  fails if `es.po` has untranslated strings for the current release. Weblate-ready so
  volunteers can add languages later.
- **Content (lessons, projects):** Markdown/YAML in each module's package, under
  `packages/kidux-module-<id>/content/<lang>/`, English is the reference tree; a CI lint fails when the Spanish tree is missing a
  file or is older than its English counterpart. Runtime falls back to English per
  file, never crashes on a missing translation.
- **Locale per child.** The child's profile stores `language` and `keyboard`; the
  sign-in screen hands them to the child's session through greetd (D24), so the
  compositor, the launcher and every module the launcher starts inherit them. Two
  siblings can use different languages on one machine.
- **Installer.** Calamares is already translated; our branding strings go through its
  `.ts` files for `en` and `es`.
- **Third-party apps** are chosen only if they already support both languages
  (Scratch, MakeCode, the micro:bit Python Editor, GCompris, Thonny and tuxtype all do).
- **Fonts.** Andika, SIL's typeface for beginning readers, on every Kidux
  screen (greeter.md, section 8), with DejaVu behind it; enough for all
  Latin-script languages we expect, extend when a new script is added.
- **Documentation.** The user guide in `docs/en` and `docs/es`, the README in both
  languages; developer documentation in English only. See `CLAUDE.md`.

## 8. Technology per module

Verified against trixie on 2026-09-22 (`qa.debian.org/madison`), the
typing and Scratch family's rows in phase 4, on 2026-10-01, and the BASIC,
CodeCombat and Wikipedia rows on 2026-10-03 (phase-4b-plan.md), against
what was built and tested.

| Module | Choice | Source | Why |
|---|---|---|---|
| Early learning (5–8) | GCompris 25.0 | `gcompris-qt` (trixie) | 150+ activities, fully translated, offline. Cheapest high-value first module. |
| Typing | tuxtype 1.8.3 first, own course later | `tuxtype` (trixie), step 4.3 | Kid-oriented and translated; own course in the launcher when the i18n layer is stable. Alternatives `klavaro`, `ktouch` also in trixie. |
| Scratch | The official editor, `scratch-editor`'s `scratch-gui` 15.2.0, built at development time (D68) and served by `kidux-webapps` | packaged by us from our build; AGPL-3 upstream since November 2024 (D69), step 4.4 | The genuine editor children know from school, translated. Its library of characters and sounds comes from the Scratch Foundation's servers. No cloud variables or community. |
| Scratch, faster | TurboWarp's `scratch-gui` (`0+git20260915`), the same way | packaged by us from our build; GPL-3 over BSD-3 upstream (D69), step 4.5 | The same blocks and projects with a compiler that runs them many times faster: for a slower computer, or when Scratch does not run well. |
| ScratchJr (5–7) | The community desktop port `ScratchJr-Desktop` 1.3.2, MIT's HTML5 app, with Electron 44, built for Linux by us (D68) | packaged by us with its Electron; BSD-3 upstream (D69), step 4.6 | MIT ships ScratchJr for tablets and Chromebooks only, and no web version; the port is the app itself, and Linux builds of it exist. |
| Blockly Games (6–12) | Google's `blockly-games` (`0+git20240513`), its offline build, served by `kidux-webapps` | packaged by us from our build; Apache-2.0 upstream (D69), step 4.7 | Puzzles that teach blocks in sixty-five languages, offline, with nothing to serve but files. |
| BASIC (8–14) | Google's `wwwbasic` (`0+git20260223`), a BASIC interpreter in JavaScript, in an editor of Kidux's own with a guide beside it, served by `kidux-webapps` | packaged by us; Apache-2.0 upstream (D84), steps 4.10 and 4.11 | The home computer of the eighties, offline: the books' way of teaching programming, a line at a time, with a guide written for this machine in the child's language. |
| micro:bit, blocks | MakeCode for micro:bit, `pxt staticpkg` build served locally | packaged by us (MIT upstream) | Official editor with simulator, offline, translated. Flashing over WebUSB in Chromium; hex download as fallback. |
| micro:bit, Python | micro:bit Python Editor v3, static build served locally | packaged by us (MIT upstream) | Official editor with simulator and reference, offline, `es-ES` translation shipped upstream. Thonny is the advanced option once the child knows Python. |
| Python | Our own course in Thonny 4.1: `turtle`, then Pygame Zero (`python3-pgzero`, Thonny has a built-in Pygame Zero mode), then micro:bit | `thonny` (trixie) | Real Python in a real editor, offline, free. This is the main road to Python. |
| CodeCombat | `kidux-module-codecombat`, a door to codecombat.com (D85, D86) | ours, nothing of CodeCombat's in it, step 4.13 | Teaches real Python/JavaScript and is translated, but the levels are proprietary (`LICENSE-LEVELS.md`: not open source, not allowed on other servers), so it cannot be shipped locally. First world free, rest by subscription bought by the adult. |
| Wikipedia (8–) | `kidux-module-wikipedia`, a door to the encyclopedia in the child's language and the Wikimedia projects (D85, D87) | ours, nothing of Wikipedia's in it, step 4.14 | The whole encyclopedia, free and in every language Kidux ships, with the rest of the internet closed; written for everyone, so the adult decides. |
| Mail (8–) | `kidux-module-mail`: Thunderbird 140 ESR with the account an adult gives, locked by its policies (D95) | `thunderbird`, `thunderbird-l10n-all` (trixie), step 4.22 | A real mail client that signs in to Google and Microsoft by itself and speaks IMAP to every other provider, with nothing for the child to set up; not for a Family Link account, which Google keeps out of it. |
| Gmail (8–) | `kidux-module-gmail`, a door to Gmail's website with the child's address filled in (D85, D96) | ours, nothing of Google's in it, step 4.23 | The way for a Family Link account, which Google keeps out of Thunderbird, and for a family that prefers the website. |
| Geometry (10–14) | Kig 25.04, interactive geometry, with KDE's actions for a child switched off (`ghns`, `shell_access`) | `kig`, `qtwayland5` (trixie), step 4.27 | Points, lines and circles that keep their rules when dragged; translated, offline. The first KDE Frameworks 5 program on the machine, so it brings Qt 5. |
| Chemistry (10–16) | Kalzium 25.04, the periodic table, with the same restrictions as Kig | `kalzium`, `kalzium-data`, `qt6-wayland` (trixie), step 4.28 | Every element with its facts, picture and atom, the states of matter on a slider, a glossary; translated, offline. Frameworks 6 and Qt 6, which GCompris already brings. |
| Physics (10–16) | Step 25.04, a physics simulator, with the same restrictions, which take away its *Download New Experiments* | `step`, `qt6-wayland` (trixie), step 4.29 | Bodies, springs and forces on a plane, run and measured, with tutorials and examples in its File menu; translated, offline. |
| Simulations (6–14) | PhET Interactive Simulations, 51 of them, each in the newest version PhET built before 29 March 2026, under CC BY 4.0 (D105), in a page of Kidux's own, served by `kidux-webapps` | taken as PhET's built files at development time (D68), step 4.30 | Physics, chemistry, maths and the Earth, made for children to explore alone, each translated into Spanish by PhET; offline. Their current versions are CC BY-NC, which Kidux does not ship. |
| Photography (8–12) | `kidux-module-photography`, a guide in thirty chapters for a child with a real camera, served by `kidux-webapps` (D102) | ours; its photographs are free ones by other people, credited in the page and in `debian/copyright`, and pictures made with Gemini's image model where no photograph showed the effect (D103), steps 4.28 to 4.34 | Photography taught as the BASIC guide teaches programming, a chapter at a time, tried on the camera the same day; the Olympus XZ-2 is the example, and every camera box says how to find the same on another camera. |
| AI agents | `kidux-ai-gateway` (ours) | packaged by us | Local service that holds the adult's API key and applies guardrails; the child's projects talk to the gateway, never to the provider directly. Local models rejected for old hardware. |
| Web (future) | Firefox ESR 140 in kiosk mode with policy-managed allow/deny lists | `firefox-esr` (trixie) | Enterprise policies give whitelist/blacklist without a proxy. |

## 9. Image build and CI

- `image/` holds the `live-build` configuration (trixie's `live-build` 20250505).
  Output: hybrid ISO with a live session that runs Calamares 3.3 (in trixie, with
  `calamares-settings-debian` as the starting point for our branding).
- The ISO only contains packages; the live session is the kiosk itself so adults can
  try it before installing.
- **GitHub Actions** runs the repository's checks on every push, builds every package
  with its tests and lintian on every pull request, and runs the whole release battery,
  the test machines included, when started by hand, in a `debian:trixie` container with
  a signing key made for the run (D38, `packaging.md`). From phase 2 it also builds the
  ISO on every tag, runs a QEMU smoke test of it, attaches the ISO and its checksums to
  a GitHub Release, and publishes the packages to the apt repository on GitHub Pages.
- The development server (MacBook Pro 2015) is a *test target*, not the source of the
  image. It installs `kidux-base` from the `testing` suite like any other machine.
- That same machine is also the owner's children's daily computer (dogfooding). A
  child's kiosk session and the administrator's SSH development session run side by
  side.
  Because nothing on it may be hand-edited, every change reaches it as a package, which
  is the discipline that keeps the shipped image honest. See the install guide for the
  rules this implies.

## 10. Repository layout

```
CLAUDE.md                    conventions
README.md, README.es.md      the product, presented
docs/en/, docs/es/           the user guide, mirrored; docs/images/en|es/ its screenshots
docs/dev/                    developer documentation, English, including the
                             requirements and the roadmap
branding/                    the logo, the mascot, the style guide
packages/                    one directory per .deb (debian/ inside)
  kidux-base/ kidux-greeter/ kidux-daemon/ kidux-module-*/ ...
                             a module's lessons are in its package, content/<lang>/
image/                       live-build config, Calamares branding
ci/                          build, publish and promote scripts, and a Kidux
                             machine to use over VNC
tests/                       every test, one file each, by kind: tests/README.md
.github/workflows/           continuous integration (packaging.md)
```

`content/` and `image/` arrive with their phases, 3 and 2.

`layout.md` lists every file, in the repository and on an installed machine.

## 11. Decision log

- **2026-09-22 — Base is trixie, not bookworm.** The earlier plan targeted bookworm
  and the "unofficial non-free firmware" images; both are obsolete. Official images
  include firmware since Debian 12.
- **2026-09-22 — amd64 only.** trixie has no i386 installer; supporting 32-bit would
  mean maintaining a kernel. Not worth it.
- **2026-09-22 — Wayland kiosk with `cage`, no desktop environment.** The earlier plan
  proposed XFCE/LXQt plus a launcher; a desktop is attack surface and RAM we do not
  need. XFCE is X11-only; on X11 a kiosk cannot isolate input.
- **2026-09-22 — Data on a separate `/home` partition, config under `/home/.kidux/`.**
  Required by "upgrade and reinstall without data loss".
- **2026-09-22 — ext4, no Btrfs snapshots.** Rollback would be nice, but old disks are
  small and slow, and a reinstall-keeping-data path covers the failure case with far
  less complexity. Revisit for 2.0.
- **2026-09-22 — Calamares instead of `debian-installer` preseed.** Parents need a
  graphical, translated installer with a "keep my data" option; Calamares is what
  Debian's own live images use.
- **2026-09-22 — CodeCombat stays online-only, optional.** Its code is MIT but the
  levels are proprietary and explicitly not allowed on other servers, so a local or
  bundled CodeCombat is legally impossible for a public distribution.
- **2026-09-22 — Hedy dropped.** Considered as a bridge to Python; the owner wants
  real Python, so the road is our own Thonny course. Fewer modules, less to translate.
- **2026-09-22 — Self-hosted official web editors instead of desktop rebuilds.**
  Scratch (`scratch-gui`), MakeCode and the micro:bit Python Editor are all open
  source and build to static files; serving them locally through `kidux-webapps` in
  Chromium kiosk mode gives the genuine, translated, offline editors with one browser
  engine instead of Electron bundles. TurboWarp Desktop (Flatpak) is plan B for
  Scratch only.
- **2026-09-22 — Chromium, not Firefox, as the kiosk browser.** WebUSB (micro:bit
  flashing) exists only in Chromium. Firefox ESR policies remain the plan for the
  future graded web browsing module; revisit whether one engine can serve both.
- **2026-09-22 — Thonny for the Python course; `mu-editor` left Debian.**
- **2026-09-22 — No Flatpak.** Everything is a `.deb`; Flatpak remains documented as
  plan B.
- **2026-09-22 — Modules stay independent even when they share infrastructure.**
  `kidux-webapps` is a hidden dependency; Scratch, micro:bit and the Python course
  are separate packages that parents install, enable, disable or remove one by one.
- **2026-09-22 — i18n is a launch requirement, not a future item.** Earlier
  requirements said "Spanish first, more languages later". Retrofitting i18n is far
  more expensive than starting with it.
- **2026-09-22 — Product name must change before public release.** Debian's trademark
  policy forbids "Debian" in a derivative's product name. Repository name can stay for
  now.
- **2026-09-22 — The development MacBook is also the family's real machine.** Chosen
  deliberately: continuous dogfooding by real children, on real old-ish hardware, from
  phase 1 onwards. Consequences: package-only changes, builds off-hours or in CI,
  separate `/home` so a reinstall from our ISO keeps their work.
- **2026-09-22 — First ISO comes early (phase 2), not last.** Testing on real old
  hardware needs an ISO; waiting until all modules exist would hide hardware problems
  until the end. Superseded by D31 for the order of phases 2 and 3.

### Phase 1 decisions, 2026-09-22

Taken while writing `phase-1-plan.md` and its two reviews. They are numbered because
the plan and the code refer to them by number.

- **D1 — Python 3 + PyGObject for every component we write.** GTK4 4.18 and libadwaita
  1.7 are in trixie with GObject introspection, `dh-python` packaging is standard and
  gettext is native. Iteration speed matters more than 0.3 s of start-up on the target
  hardware. Revisit only if measurements on a 2008 machine say otherwise.
- **D2 — Local apt repository first.** `reprepro` on the development machine, served by
  nginx on the LAN; GitHub Pages publishing moves to phase 2. The GitHub repository is
  private, so Pages is not available, and nothing about the package format or the client
  configuration changes when the archive later moves to a public URL.
- **D3 — Keep the `kidux-` package prefix; choose the public name in phase 2.** Package
  names are an internal contract; the trademark problem is about the *product* name,
  which first becomes visible in the installer and the boot screens.
- **D4 — Test the kiosk and the hardening in a QEMU/KVM VM before installing on the
  development machine.** That machine is also the family's daily computer; a hardening
  mistake must not cost a USB recovery.
- **D5 — An adult password, not a PIN.** Free-form text, no minimum length, no
  digits-only rule. Forcing digits stops adults from using something they can actually
  remember. How strong it is, is the family's call; the panel advises and never blocks.
- **D6 — The adult panel is modal, lives only on trusted screens, and dies on exit.**
  `Unlock(password)` returns a token that lives exactly as long as the panel is open.
  The panel blocks the whole screen, so it cannot be left open unnoticed, and it runs as
  `_greetd`, never inside a child's session.
- **D7 — "Exit to desktop" (`labwc`) is out of phase 1.** A compositor is not a desktop:
  it would pull a launcher, a panel, a terminal, a file manager and a screen lock onto
  every installed machine, plus a second session type to harden. Configuration never
  needed it — that is what the panel is for. Revisit when a real adult asks.
- **D8 — The adult is called "Adult" ("Adulto"), never "parent".** Mothers, fathers,
  grandparents and teachers all use the same machine; "Adult" fits all of them and a
  six-year-old reads it without help. Applies to every user-visible string and to the
  public documents. The D-Bus interface keeps the name `Parental1`, because "parental
  controls" is the established technical term and the API is never seen by a user.
- **D9 — Every child has their own password; switching child is "one logs out, the other
  logs in".** Gives every child real separation and makes the sign-in screen the single
  place where access rules are applied. Supersedes the earlier single shared kiosk
  session.
- **D10 — The machine boots into our own greeter.** `greetd` runs
  `cage -- kidux-greeter`; the child's password is their Unix password and `greetd`
  does the PAM conversation. Supersedes "auto-log the last active child in": the
  authentication that starts a session must be the system's, not ours.
- **D11 — Three access modes per child: `unlimited`, `daily`, `manual`.** Enforced by
  `kidux-daemon`, never by anything running as the child, because anything the child's
  session owns the child can eventually kill.
- **D12 — Time up warns, then locks; a session is never ended by the system on its
  own.** Warnings at 10, 5 and 1 minute, then a trusted lock screen with the session
  frozen underneath. Chosen in review over ending the session: unsaved work is never
  destroyed by a timer, and a `daily` child who leaves the session locked overnight
  simply continues the next day.
- **D13 — The daily counter counts wall-clock time while the session is unlocked**, with
  no idle detection, reset at 04:00 local time; locked time does not count. Simple to
  implement and to explain to a child. The consequence — that a session left unlocked
  over dinner spends the day's time — is documented for families, and the launcher's
  "Lock" button is prominent for exactly that reason. *No idle detection: superseded
  by D67, which locks a session left alone; the counter is still wall-clock while
  unlocked.*
- **D14 — Granted time is a bank, spent only by use.** In `manual` mode a grant lasts
  until it is spent, across sessions and days; in `daily` mode an extra grant is for
  today only and is lost at the 04:00 rollover. What an adult gives should not evaporate
  because a child logged out early, but a daily limit is a daily limit.
- **D15 — No lock-out on the adult password.** Every attempt is audited; nothing is
  delayed or blocked. Choosing a password children cannot guess or see is the adult's
  responsibility, and because the password is only typed on trusted screens (D6) no
  child process can attempt it at all — only someone at the keyboard can.
- **D16 — The power button and Ctrl+Alt+Escape always bring up the trusted lock
  screen**, handled by the daemon reading the input devices directly, not by the
  compositor. This is the "secure attention" rule that makes D6 hold in practice: an
  adult presses the power button *before* typing their password, and whatever screen
  appears is real. It also means the power button can never turn the machine off without
  a screen that asks.
- **D17 — The child's Unix user is the security boundary, not the launcher.** Everything
  the child's uid can do, assume the child will do. Phase 6 hands children arbitrary
  code execution by design (Python in Thonny), and any write into the home directory is
  a potential foothold. The kiosk is a user-experience boundary; the privilege boundary
  is enforced by the kernel, PAM, polkit and the daemon.
- **D18 — Accounts are named by whoever installs; our packages depend on groups, never
  on names.** Three consequences, in order of importance. First, the Adult of the
  interface is a password held by the daemon, not a Unix account: there is no adult
  session and no adult desktop (D6, D7). Second, the Unix administrator account is
  created by the installer with a name the family chooses; shipping a fixed name such as
  `parent` would publish half a credential on every installation in the world and gain
  nothing, since Calamares asks for a name anyway. Third, the only identities that are
  fixed across every machine are the system groups `kidux-admin` and `kidux-children`,
  created by `kidux-daemon.postinst`, and `_greetd`, which comes from the `greetd`
  package. `kidux-firstboot.service` adds every human account that is in `sudo` to
  `kidux-admin` at first boot, which is the single link between the installer's account
  and our state directory; it cannot help a child, because the daemon never puts a child
  in `sudo`. To keep this honest, `tests/project/no-local-identity.sh` fails the build if a
  developer's user name, host name, e-mail address, home directory or LAN address
  appears anywhere under `packages/`, `image/` or `ci/`.
- **D19 — The product is called Kidux, and every identifier uses `kidux`.** Supersedes
  D3, which had deferred the public name to phase 2, and settles the older entry above
  about the trademark: "Debian" no longer appears in the product name, only in the
  honest statement that the system is built on Debian. The name is *kid* plus *tux*: it
  says what the system is in the one vocabulary every Linux user already shares, in any
  language, which matters for a project that ships in two languages and means to ship in
  more.

  Choosing the name now cost one search and replace over the documents, because not a
  single package had been built yet. The same rename after phase 1 would have meant
  migration code running on real families' machines to move the state directory, rename
  two system groups and rename a D-Bus service that the greeter, the locker and the
  launcher all talk to. One word now covers the product name, the package prefix, the
  state directory `/home/.kidux/`, the D-Bus name `org.kidux.Daemon1`, the groups
  `kidux-admin` and `kidux-children`, the apt suite, the repository and the development
  machine's host name.

  **The name was chosen second.** The first choice was "Kiddos", and it was already
  taken: [kiddos.dev](https://kiddos.dev/) is KidDOS, a free and open-source computing
  environment for children aged seven to thirteen that even advertises kiosk hardening
  and a Raspberry Pi image. Same audience, same techniques, same word. About forty
  candidates were then checked for an existing software project of that name and for
  free domains, which killed most of them: Ludus and Tortuga and Ábaco and Pharos and
  Protos were all taken, Stemos sits one letter from Valve's SteamOS, Espiral is
  Debian's own logo, and Exploros and MindOS are both education platforms already.
  Kidux was the only candidate with no software project of that name and with `.com`,
  `.org`, `.dev`, `.io` and `.net` all free. The lesson, learned the expensive way and
  written down so it is not repeated: **check a name against existing projects before
  proposing it, not after adopting it.**

- **D20 — Kidux is licensed GPL-3.0-or-later.** *Superseded by D78.* Decided 2026-09-22, when the first
  package needed a `debian/copyright` and the repository still had no licence at all.

  Kidux exists so that a family can be handed a computer their child can use, and so
  that other families, schools and teachers can take it and adapt it. Strong copyleft is
  what keeps that true for the people downstream: anyone may take Kidux, change it and
  give it to their own children, and anyone who distributes their changes has to pass
  the same freedom on. A permissive licence would allow a vendor to take the work,
  close it and sell a locked-down box, which is the opposite of the point.

  Version 3 "or later" rather than 2, for the patent grant and the anti-tivoisation
  clause: a distribution meant for cheap hardware should not be usable as the software
  half of a device its owner cannot modify. It also matches Debian's own ecosystem and
  GCompris, a module planned for the first wave.

  Content shipped with learning modules may carry its own licence where that suits the
  material better; each module records what it ships in its `debian/copyright`.

- **D21 — The apt source ships as its own package, `kidux-apt-source`, separate from
  `kidux-archive-keyring`.** Decided 2026-09-22 while building the first packages.

  A single package holding both the key and `/etc/apt/sources.list.d/kidux.sources` is
  what the phase 1 plan assumed, and `lintian` rejects it: a package must not choose an
  administrator's installation sources. The exception Debian grants is a naming rule —
  a package whose name ends in `-apt-source` may do exactly this — so the source
  package `kidux-archive-keyring` now builds two binaries. `kidux-apt-source` depends on
  the keyring, so installing it is still one command, and the split says out loud which
  of the two changes the machine's trust and which changes where it looks.

  Taken over silencing the tag with a `lintian` override: the rule exists because
  adding an apt source is a real change to a machine, and the naming convention is
  Debian's own answer to needing to do it.

- **D22 — A package's `debian/changelog` names the Debian release it targets; the
  suite it is published to is chosen when it is published.** Decided 2026-09-22.

  Two different things were both called a distribution. The changelog now says
  `trixie`, which is a fact about the package: the Debian release it was built and
  tested against. Our suites `testing` and `stable` say how far a package has got
  through our own testing, which is a fact about the moment, decided by whoever runs
  `ci/publish-local.sh`. Keeping them separate means promoting a tested package from
  `testing` to `stable` never means editing and rebuilding it, and `reprepro` is told
  to expect the mismatch rather than the changelog being bent to match the archive.

- **D23 — Every package must build twice into identical bytes, and CI checks it.**
  Decided 2026-09-22, after a rebuild of an unchanged `kidux-base` produced a different
  package under the same version and the archive refused it.

  The architecture already said everything on a user's machine is reproducible from
  this repository. Nothing checked it, which made it a wish rather than a rule, so
  `tests/run reproducible` now builds each package twice and compares.

  It is not tidiness. A version number is a promise about specific bytes. `reprepro`
  refuses to replace a published version with different content, which is what caught
  this; and promoting a package from `testing` to `stable` only means anything if what
  a family installs is byte for byte what was tested on a clean machine. Two builds of
  one source that disagree break both of those at once.

  The cause was a changelog dated in the future. `dpkg` clamps file modification times
  to `SOURCE_DATE_EPOCH`, taken from the newest changelog entry, but only clamps times
  that are newer than it — so a future date clamps nothing and each build writes its
  own wall clock into the package. **Changelog dates come from the clock**,
  through `ci/hours.py changelog-date` since D99, never from memory.

- **D24 — A child's session gets its environment from the greeter, through greetd;
  a child's session never reads `/home/.kidux`.** Decided 2026-09-22 while designing
  the daemon.

  The session wrapper runs as the child, and the state directory is closed to the
  child by design. So the language, keyboard and display scale a session needs are
  fetched by the greeter — which runs as `_greetd` and may ask the daemon — and passed
  to greetd's `start_session` as environment, which greetd adds to PAM's. The wrapper
  applies what it is given and asks nothing. The alternative, a world-readable copy of
  the profile, would have put every child's settings where every child can read them.

- **D25 — GRUB boots one unrestricted Kidux entry; Debian's entries stay behind the
  recovery password.** Decided 2026-09-22.

  Setting a GRUB superuser protects every entry, including the one the machine boots by
  itself, and trixie's `10_linux` never marks an entry `--unrestricted`: a machine
  hardened the obvious way asks for a password to boot at all. `kidux-session` ships
  `/etc/grub.d/09_kidux`, which emits the password stanza only once first boot has
  written the hash, and one `--unrestricted` entry booting `/vmlinuz` and `/initrd.img`
  — the symlinks Debian keeps pointing at the newest kernel, so the entry never needs
  regenerating. Debian's own entries, generated after it, remain restricted, which is
  exactly the split wanted: the kiosk boots by itself; editing a boot line or choosing
  recovery mode needs the adult. Assumes no separate `/boot`, as the disk layout says.

- **D26 — An adult-panel token dies after fifteen minutes without use.** Decided
  2026-09-22. Configurable as `panel_timeout_minutes`. *The fifteen minutes and
  `panel_timeout_minutes`: superseded by D67; the token and the panel follow
  `idle_lock_minutes`.*

  D6 binds a token to the panel being open. A panel left open on a machine in a
  family's living room is open to whoever walks past, so the token also expires on
  its own; the panel asks for the password again and nothing is lost. Fifteen minutes
  is long enough to set up three children and short enough that "I left it open" is
  a nuisance rather than a hole.

- **D27 — polkit decides who may call; the daemon decides which child.** Decided
  2026-09-22.

  polkit sees an action and a caller, never the arguments. A child allowed to ask about
  their own time could otherwise ask about a sibling's, and an unlocked panel could
  delete the administrator's account. So beyond polkit the daemon checks, itself, that a
  child names only themselves, that only members of `kidux-children` are ever managed,
  and that a token belongs to the connection presenting it. These checks are in one
  module, `gate.py`, and each has a test that tries to get past it.

- **D28 — A lock has happened only when logind confirms the child's session is
  inactive; otherwise the session is ended.** Decided 2026-09-22.

  The lock works by switching virtual terminals through logind, which revokes the
  child's compositor's devices. If that switch does not take on some driver, the child
  still has the screen and a limit that can be ignored, which is worse than the
  alternative. So the daemon waits for confirmation, and without it terminates the
  session after auditing why. The launcher has warned about saving at ten, five and one
  minute, which is what makes this the lesser harm.

- **D29 — Passwords are typed in the machine's keyboard layout, on every trusted
  screen.** Decided 2026-09-23 while building the sign-in screen.

  A child's profile has a keyboard layout, and their session uses it. The sign-in
  screen cannot: `cage` takes its layout from the environment when it starts, before
  anyone has tapped a picture, and has no way to change it afterwards. The lock screen
  could, but a child whose password contains a character that sits on different keys
  in the two layouts would then type it one way to sign in and another to unlock. So
  the sign-in screen, the lock screen and the panel, where passwords are set, all use
  the machine's layout from `config.toml`. The language still follows the child.

- **D30 — Every screen fits 1280x800 whole.** Decided 2026-09-23 with the owner, from
  the pictures of the first full test run.

  Kidux is for computers about ten years old, and 1280x800 is a common screen
  among them; the development MacBook, at scale 2, is 1440x900. The first screens, drawn with large type and large
  targets, did not fit that: the panel's page for a child hid its time buttons
  and its Back button below the edge. So text, buttons, avatars and margins are
  sized to fit 1280x800 with the tallest screen whole, a smaller screen scrolls
  rather than hides anything, and the launcher keeps its bars small so that the
  room between them is the modules'. The greeter logs any screen that has to
  scroll, and the session tests fail on it (greeter.md, section 8).

- **D31 — Phase 3 comes before phase 2: modules before the ISO.** Decided 2026-09-23
  with the owner, after he had used Kidux in the VM of `ci/vm/try.sh`.

  The owner's children use the development MacBook, which gets Kidux from the
  package archive (rollout.md), not from an ISO, and the VMs of `tests/` and
  `ci/vm/try.sh` show every screen and every door without one. So the ISO and
  the installer, phase 2, wait for as long as they can, and the module
  framework with GCompris, phase 3, comes first: that is what puts something
  on the children's screen. Step 9.11, the rollout on the MacBook, is the
  owner's and blocks nothing; phase 3 is built and tested on the VM as every
  step of phase 1 was. The reason for the earlier order, finding hardware
  problems early, is served by the rollout instead, on the one machine
  Kidux is being built for first. The ISO's smoke test replaces the VM runs
  when phase 2 comes; until then they are the test.

### Phase 3 decisions, 2026-09-23

Taken while planning `phase-3-plan.md`, which explains each in its section 3.

- **D32 — A module runs in a systemd user scope, and without the network when
  its manifest says so, through bubblewrap.** The scope is what ends a module
  cleanly, caps its memory and lets it outlive a launcher crash; the network
  namespace is what makes `needs_network = false` a fact rather than a promise.
- **D33 — Installing and removing a module goes through the daemon and the
  update job runner**, refused while any child session exists. dpkg never
  replaces what a session may be running.
- **D34 — The daemon says which modules exist and which are enabled; the
  screens read the manifests themselves**, through one reader,
  `kidux.modules` in `kidux-common`. A module's name and description are in
  its manifest, translated through its own gettext domain.
- **D35 — Every child's session has PipeWire**, from `pipewire-audio`, started
  by the child's user manager; no system-wide sound server.
- **D36 — Web-application modules are confined by Chromium's policy, not by a
  network namespace.** A namespace without network has no loopback either, so
  a web app served on `127.0.0.1` cannot live in one; the managed policy
  allows that origin and nothing else. *Nothing else: superseded in part by D69,
  which allows the child's own files, downloads and the Scratch library's servers,
  and by D85, which writes the allowlist from the installed modules' hosts and
  walls each module's Chromium in to its own.*

- **D37 — The adult panel is a set of forms, dense, not a sequence of
  screens.** Decided 2026-09-23 by the owner, after using the panel in the VM.

  The children's screens are large and ask one thing at a time, because a
  child who cannot read yet has to use them. The panel is used by adults, who
  want to see a child's settings at a glance and change three of them at
  once. So each page of the panel shows everything it is about on one screen,
  with smaller controls and libadwaita's own widgets, and changes are made in
  place; the wizard keeps its steps only for what needs a restart between
  them, and adds the first child with the same form. The colours, the
  typeface and D30 stay. `phase-1-plan.md`, step 9.7b.

- **D38 — Continuous integration runs the whole release battery by hand and
  weekly, not on every push.** Decided 2026-09-24 while building plan step 9.9.

  The repository is private, and GitHub's minutes for a private repository
  are few: `ci/test-release.sh` takes more than an hour here, longer on a
  runner, and this project pushes to `main` many times a day. So every push
  gets the repository's own checks, which take a minute; every pull request
  and every push to a working branch gets every package built with its tests
  and lintian, which is what catches a broken translation, a lintian rule or
  a developer's name, the plan's acceptance; and the release battery, with
  both test machines, runs when started by hand and once a week. The
  development machine keeps running it before every commit of a step, as
  before. Revisit when the repository is public and minutes are free.

- **D39 — The tests live on the development machine; GitHub runs the release
  battery only when asked.** Decided 2026-09-24 by the owner, refining D38: no
  weekly run. The owner does not want the project to depend on GitHub, and a
  private repository's minutes are few. Every push still gets the repository's
  checks and every pull request the packages built with lintian, which is what
  catches a broken translation, a lintian rule or a developer's name; the
  whole battery runs here before every commit of a step, and on GitHub by hand
  before a release.

- **D40 — The lock freezes the child's user manager with their session.**
  Decided 2026-09-24 while building phase-3-plan.md step 3.2. A module runs in a
  scope under the child's systemd user manager (D32), which is outside the
  session's scope, so freezing the session alone left an open module running
  under the lock screen: its sound playing, its work going on, against
  modules.md's promise that a module is frozen like everything else. The
  daemon freezes `user@<uid>.service` after the session's scope and thaws it
  first, and thaws both before ending a session; since the user manager
  outlives the session, it is also thawed when a locked session disappears
  and when a child's session starts. PipeWire, which runs there
  too (D35), is silent while the screen is locked, which is what a lock is
  for. The alternative, running a module inside the session's scope, would
  lose the memory cap and the module's life beyond a launcher crash.

- **D41 — Every native module runs in one sandbox, and the network is the
  only difference between them.** Decided 2026-09-24 in the review of step
  3.2. As first built, only a module without the network ran under
  bubblewrap, with the whole of the child's home and runtime directory
  writable. That left `needs_network = false` a promise a program could
  break without leaving the child's own rights: through the user bus or the
  user manager's private socket in the runtime directory it could ask
  `systemd --user` to start a program outside the sandbox, with the network;
  through the writable home it could leave a unit in
  `~/.config/systemd/user` for the next session to start. It could also read
  another module's files, against modules.md. So every native module now
  runs in the same sandbox: an empty home with only the module's own three
  directories in it, an empty runtime directory with only the Wayland and
  PipeWire sockets, pid, ipc and uts namespaces of its own, and the network
  namespace only when the manifest says so. The launcher's own argv is the
  specification, and `tests/session/16-module-open.py` checks from inside a
  module what it can see. What the sandbox does not try to be: a boundary
  against the child, which is the Unix user (D17); a module still reaches
  the system bus, where a child may do only what a child may do.
  **Superseded by D42.**

- **D42 — The child's home is shared by every module, there is no sandbox,
  and the manifest says nothing about the network.** Decided 2026-09-24 by
  the owner, on the review's account of what D41 cost and what it closed.
  Kidux is a child's first computer, not a vault: what a child makes in one
  module must be there for the next, to open, send or print, as on any
  computer, and a child who learns to program will one day write a program
  that reaches the internet, which is a risk the owner accepts. The
  boundary stays the child's Unix user (D17): the system, the family's
  state and the other children's files are closed to a module by the same
  permissions that close them to the child. What D41 protected beyond that
  — one module's files from another, the network from a module that said
  it did not need it — is what the owner wants open, and it cost five runs
  of the battery and still had holes. So a module runs in its scope (D32,
  D40) and nothing else: it sees the child's home and saves the child's
  work there; its own settings, data and cache go in three directories of
  its own, so removing it removes only those. Whether a module uses the
  network is not something Kidux tracks or shows: what matters is what a
  module lets a child reach. Native programs and web applications held to
  their own local server (D36) are closed doors; a module that opens the
  web, when there is one, with a list of sites or a filter, is one the
  adult switches on or not, like any other. A module that must truly have
  no network is not something Kidux promises.

- **D43 — Several modules at once: `sway` is the child's compositor, and the
  launcher draws the bar.** Decided 2026-09-24 by the owner: learning to
  work with a computer includes having more than one thing open and moving
  between them, and the owner wants it from the first module rather than
  later. `cage` shows one window and has no way to switch; it stays for the
  trusted screens, which want exactly that. A child's session runs `sway`
  (1.10 in trixie) with a configuration of Kidux's own: each module on a
  workspace of its own, the launcher on the first, no borders or title
  bars, no bar of sway's, no XWayland, and three bindings: Super for home,
  Alt+Tab and Alt+Shift+Tab round the open modules. The launcher draws a
  bar along the bottom, always on top (the layer-shell protocol through
  `gtk4-layer-shell` 1.0), with Home, one button per open module, the time
  left and Lock, and drives sway through its IPC socket (`python3-i3ipc`):
  a new window goes to its module's workspace, a module that asks for the
  whole screen gets the screen minus the bar, and the bar is how a child
  who uses the mouse comes back. Tried on the test machine before deciding:
  sway under QEMU, two windows side by side, the bar through layer-shell
  (the library must be loaded before GTK opens its display, `LD_PRELOAD`
  from the launcher's wrapper), the IPC from Python. Chosen over `labwc`
  (stacking, no IPC of its own) because sway's IPC lets the launcher own
  the policy, and tiling gives two modules side by side for free later.

- **D44 — A web application opens in a Chromium application window, not in
  kiosk mode, and the launcher knows Chromium's window by its children.**
  Decided 2026-09-25 while building phase-3-plan.md step 3.7, after trying
  it on the test machine. `--kiosk` hides Chromium's tabs and address bar
  only while its window is fullscreen, and the launcher gives no window the
  whole screen, so the bar stays (D43): under sway, a kiosk window showed
  every bar Chromium has. `--app=<url>` is a window with neither, which
  keeps its place above the bar like any module; the managed policy of D36
  still holds it to the local server, and turns off translation, guest
  mode and adding people besides. And Chromium moves its browser process
  into a systemd scope of its own when it starts, out of the module's
  scope, which is how the launcher tells a module's windows (D32); the
  processes it starts stay in the module's scope, so a window whose process
  is in another scope under the child's user manager belongs to the module
  its children are in, read from `/proc/<pid>/stat` and `/proc/<pid>/cgroup`;
  the launcher, in the session's scope and the parent of every module, is
  never taken for one. The environment would
  have said it directly, but `kernel.yama.ptrace_scope=2` closes a
  process's environment to the child's other processes, and that stays.

- **D45 — Every module closes from the launcher's bar: asked first, forced
  as the emergency.** Decided 2026-09-26 by the owner, on the review of
  step 3.7. A module's window has no frame and no close button, and a web
  application's own *Done* stops working once its window has more than one
  page in its history (Chromium refuses `window.close()` then), so a child
  had no sure way to close what they opened. The bar gets a close button for
  the module on screen. It asks the module to close first, the way a
  window manager does (the `xdg_toplevel` close request through sway's
  `kill`), so that a program with unsaved work can say so and decide; only
  when the module does not go does the launcher offer, after asking the
  child, to end it by force through its scope. Every module, native or
  web, is closed the same way.
- **D46 — Windows are a setting of the child, and a module may require
  them.** Decided 2026-09-26 by the owner. A module on its own workspace,
  filling the screen above the bar, is right for the youngest child and for
  a program like GCompris. It is not enough for a real web application (a
  site as it is, not a page of Kidux's own) or for an editor with several
  files open: those need windows a child can move, resize, put fullscreen,
  and have several of at once. So windows are a per-child setting an adult
  switches on in the panel, and a module's manifest may say it requires
  them, in which case the panel says so and the tile does not appear for a
  child without. sway already tiles and floats windows; what changes is
  what the launcher tells it to do with them. The setting exists before
  the first real web module ships (phase 4).
- **D47 — A module carries its name and description in every language in
  its package's control fields.** Decided 2026-09-26 by the owner. The
  panel offers the modules the archive has; of one not yet installed the
  machine knows only the archive's index, whose short description has one
  language. Each module's `debian/control` carries
  `XB-Kidux-Name-<lang>` and `XB-Kidux-Description-<lang>` for every
  language it ships; the archive keeps the fields in its index, `apt-cache
  show` prints them, and the daemon's catalogue reads the machine's
  language from them, falling back to English and then to the short
  description. A new language is a new field in each module, a new module
  is its package, and Kidux's code changes for neither. A list of known
  modules in `kidux-common` is rejected: every new module would have to be
  added to it.
- **D48 — Kidux answers GCompris's first-start questions and leaves its
  downloads on; the module's description says it needs the internet.**
  Decided 2026-09-26 by the owner. The module's starter writes GCompris's
  settings before its first start, so a child never meets its questions,
  and turns automatic downloads on, so voices, words and music arrive by
  themselves when an activity needs them. The description of the module, in
  every language, says it needs an internet connection at least when it is
  set up, or always if that is what the owner's use at home shows.

- **D49 — One display scale for every screen, chosen by the adult, and the
  room a larger screen has is used.** Decided 2026-09-26 by the owner, from
  the first hand test on the MacBook: the adult panel looked far too small
  and the child's desktop cramped, while the same scale is meant to reach
  both. The sign-in screen, the lock screen, the panel and the child's
  session share the one scale in the machine's settings, applied the same
  way in each, and the adult chooses it from a finer set (1, 1.25, 1.5,
  1.75, 2, 2.5, 3). Every screen still fits 1280x800 whole (D30); on a
  larger screen the same screen has more room and uses it: wider forms,
  more tiles to a row, longer lines, never a small drawing in the middle of
  an empty screen. phase-3-plan.md, step 3.12.
- **D50 — The adult sets a child's time left for today, zero included.**
  Decided 2026-09-26 by the owner. The panel could only give time; an
  adult who wants a child to stop soon, or who is trying the machine and
  cannot wait an hour for the time to run out, needs to take it away. The
  panel's page for a child sets what is left today to any number of
  minutes from zero up; a child signed in sees the time-is-up screen when
  it reaches zero, as when it runs out by itself. Step 3.13.
- **D51 — Chromium's drawing on a machine's graphics is settled on the
  machine, through a file of flags Kidux reads.** Decided 2026-09-26 by
  the owner, who saw hello-web's window drawn as noise and remains on the
  MacBook's `radeon` graphics, cleared as the pointer moved over it: a
  fault of Chromium's GPU path on that hardware, which no test machine has
  (theirs draw in software, cleanly). `kidux-webapp` reads
  `/etc/kidux/chromium-flags`, root's, one flag a line, and adds them to
  Chromium's command line, so the flags that draw cleanly on a machine are
  found by trying them there, one at a time, and the ones that prove
  general go into the package for every machine. Step 3.14. (D52 puts
  the panel over the file: the adult sets the flags there, not by hand.)
- **D52 — The settings that depend on a machine's hardware are on the
  panel's System page, under *Advanced*, Chromium's flags first.** Decided
  2026-09-26 by the owner. Kidux is meant to be installed by other
  families on whatever old computer they have, and what draws cleanly on
  one may not on another; a setting that lives only in a file under `/etc`
  is out of reach of the adult the panel is for. So the System page gets
  an *Advanced* section, with each such setting explained in a line, its
  default the one that works on most machines, and the value this machine
  needs typed there. The daemon keeps it in the machine's settings and
  writes the file the program reads (`/etc/kidux/chromium-flags`, which
  `kidux-webapp` reads as the child), so the panel is the one way in and
  the file is Kidux's own.
- **D53 — The display scale is automatic until an adult chooses one.**
  Decided 2026-09-26 while building phase-3-plan.md step 3.12. The owner's
  MacBook, where the adult panel looked far too small and the child's
  desktop cramped, turned out never to have had its scale changed: it drew
  every screen at 1 on a 2880x1800 panel, and nothing asked. A machine now
  has `display_scale = 0`, automatic, until an adult chooses one on the
  System page: the largest quarter at which the screen's mode still holds
  1280x800 whole (D30), never less than 1, worked out when each screen
  starts (`kidux.screen.automatic_scale`), so the sign-in screen, the
  wizard and a child's session are the size they are meant to be on any
  panel from the first boot. An adult who wants more room on a large screen
  chooses a smaller scale; a machine's saved 1 stays 1. And what D49 calls
  using the room of a larger screen is, in the owner's words, simply more
  space: on a screen with more than 1280x800 to spare the screens keep
  their size, and the launcher puts more tiles to a row. The rule of the
  scale itself, 1280x800 held whole, is superseded by D56.
- **D54 — A child's time is for the days of the week an adult ticks.**
  Decided 2026-09-27 by the owner, on the review of steps 3.9 to 3.15. A set
  time each day is not always every day: a family may want the computer on
  Fridays and at the weekend only. The child's page gets seven boxes, all
  ticked for a new child; a child with a set time each day, or with no
  limit, has it on the ticked days and, on the others, only what an adult
  gives that day, so a grant from the panel or the sign-in screen still
  works. The sign-in screen says that today is not the child's day, and
  offers the adult's grant as it does when the time is spent. Time given
  case by case has no days: the adult decides each time. A grant always
  gives its minutes: on a day unticked after the child used time that
  morning, the grant covers what was used first, so that fifteen minutes
  given are fifteen minutes had, and the same when a daily allowance is
  cut below what was used.
  phase-3-plan.md, step 3.17.
- **D55 — A module says who it is for: an age range, and the modules best
  done first.** Decided 2026-09-27 by the owner. A manifest's `min_age` and
  `max_age`, which the panel had not shown, are shown as *Ages 4 to 8*;
  `recommended_before` names the modules a child does well to have done
  before this one, and the panel names them after the description. Both
  travel in the package's fields (D47), so the panel says them for a
  module not yet installed too. They are for the adult to weigh, never for
  Kidux to enforce: an adult switches on what they like for whom they
  like. Step 3.18.
- **D56 — The automatic scale leaves room to spare, and the panel says
  what it comes to.** Decided 2026-09-27 by the owner, on trying 2.25 on
  the MacBook: everything too large, and a wish for more space by
  default. The automatic scale is the largest quarter at which the
  screen's mode still holds the roomy size of D53, 1600x960, never less
  than 1: 1.75 on the MacBook's 2880x1800 (1645x1028 logical, roomy, eight
  tiles to a row), 1 on 1920x1080 and on anything smaller, 1.5 on
  2560x1600, 2.25 on 3840x2160. A screen that can be roomy is. And the
  System page's list says what automatic comes to on this screen,
  *Automatic (175 %)*, so an adult choosing a larger or a smaller size
  knows where they start from; `session-inner` exports the mode for that.
  Step 3.12 as it is now.
- **D57 — With windows on, a child's modules share one desk: every
  window in view at once, with a frame and its buttons, and the bar as the
  taskbar.** Decided 2026-09-27 by the owner, on trying step 3.15: a
  window on a workspace of its own, black around it and one at a time, is
  not the multitasking wanted. A child with windows should see every
  window at once and copy from one into another, and each window should
  have a frame with minimise, maximise and close, drawn for every program,
  since most programs leave the frame to the window manager. So with
  windows on every module's windows are on one desk, over Kidux's cream,
  each in the frame the compositor draws (D58), and the launcher's bar
  lists every window, brings it forward and brings a minimised one back.
  Without windows nothing changes for the child. D46's "several at once"
  is this. Step 3.20.
- **D58 — labwc replaces sway as the child's compositor, and XWayland is
  on.** Decided 2026-09-27 by the owner, on the same review. `sway` draws
  a title bar with no buttons and never will, and has no minimise: with
  it, the frame every ordinary program expects from its window manager
  (TuxType, Thonny, Scratch, GCompris all leave it to the compositor) is
  impossible, and D57 could only be faked on Kidux's bar. `labwc` (0.8 in
  trixie) is a stacking compositor of the same family (wlroots, like
  `sway` and `cage`): it draws frames with iconify, maximise and close
  for any program, minimises for real, takes the same `wlr-randr` scale,
  the same layer-shell bar and the same output protocols, is as small,
  and is configured by files root owns, with menus left empty and only
  Kidux's keys. What it lacks is `sway`'s command socket: the launcher
  reads and drives windows through the foreign-toplevel protocol instead
  (list, activate, minimise, maximise, fullscreen, close), and what
  `sway` was told window by window becomes rules in two configurations,
  one for the kiosk (every window maximised and frameless above the bar,
  raised by the bar: D43's workspace per module is superseded by this)
  and one for the desk (D57). A full desktop environment was weighed and
  set aside: GNOME cannot carry Kidux's bar and is too heavy for old
  machines; KDE could, with its kiosk framework, but weighs a gigabyte
  and its lock-down never ends; XFCE, MATE and LXQt are X11, where every
  program reads every key. XWayland comes with `labwc` and is on from
  now, so that a program made for X11 (Tk, and so Thonny in phase 6) runs
  in a child's session: X11 programs of one child see one another's keys
  and windows, as on every Linux desktop, and nothing else of Kidux's;
  that is within D42's "no sandbox between modules". Under wlroots an X11
  window is drawn at scale 1 and enlarged to the screen's scale, so on a
  high-density screen at a fractional scale it looks blurred, and at 200 %
  pixel-doubled; sharp only at 100 %, which is what the old machines
  Kidux is for have. `labwc` 0.8 has no XWayland scaling option (Hyprland
  and KDE do; neither is an option here). So modules made for Wayland
  are preferred, an X11 stand-in module is in the tests from the start,
  and the owner judges the softness on the MacBook (step 3.21). Steps
  3.19 to 3.21.
- **D59 — The sizes that are whole multiples of 100 % are the preferred
  ones, and the panel says why.** Decided 2026-09-27 by the owner, with
  D58. On the System page the sizes that are not whole (125, 150, 175,
  250 %, and automatic when it comes to one of those) carry a mark, and a
  note under the list says that the marked sizes can make a module that
  runs through XWayland look blurred, and that the cure is a size without
  the mark. The automatic rule (D56) stays as it is. Step 3.19.

- **D60 — Kidux's modules start in a window, not in fullscreen.** Decided
  2026-09-27 while building step 3.19. `labwc` 0.8.3 does not change the
  decoration of a fullscreen window, and gives a window taken out of
  fullscreen its frame back whatever a rule said; `<maximizedDecoration>`,
  which would take it off, is a later labwc's. So in the kiosk a program
  that comes up fullscreen, once the launcher has taken it back (D43),
  keeps a thin title bar with a close button, while one that starts in a
  window is frameless like every other. Kidux's own modules start in a
  window (`kidux-module-hello`; GCompris with `--window`), and modules.md
  asks the same of every module; a program that insists on fullscreen gets
  the title bar, whose close button works. A later `labwc` with
  `maximizedDecoration` would lift this. Step 3.19.
- **D61 — A laptop's keys and its corner: brightness, keyboard light,
  sound, battery and the lid, and the keys written where a child sees
  them.** Decided 2026-09-28 by the owner, from the first hand test of
  labwc on the MacBook, and on 2026-09-29, from the second, for every
  screen: the child's screen, and the sign-in, lock and adult screens too
  (`kidux.corner`), show, top right, what the machine has and nothing it
  has not: the battery's charge, and the
  screen's brightness, the keyboard's light and the sound's volume as
  buttons with a slider, the sound's with *Mute*; everything read from
  `/sys`, or from `wpctl`, by `kidux.hardware`, and set through
  `brightnessctl`, which writes `/sys` itself and so needs group `video`,
  which every child and `_greetd` are in and to which kidux-session gives a
  keyboard's light too (brightnessctl's own rule gives it to `input`, which
  reads every keyboard), and `wpctl`; what else `video` opens to a child,
  the console's framebuffer and a webcam where there is one, is a door
  session.md's table names. On a screen narrower than 1200 logical pixels
  the corner is compact, its icons without their percentages, so that it
  never reaches what is centred at the top of a screen.
  The laptop's own keys for those, `XF86` keysyms that a MacBook and a PC
  send alike, are labwc keybinds in both configurations that run
  `kidux-keys` as the child. Closing the lid powers the machine's own
  panel off through `wlopm` (wlr-output-power-management, which labwc
  implements) and opening it powers it on, from the launcher, which reads
  the lid switch that a udev rule of `kidux-session`'s makes readable;
  brightness, windows and an external screen are left alone, and logind
  still ignores the lid, so closing it is never a way out of a time
  limit. The bar writes the keys beside the buttons that do the same,
  Home, Close and the one Alt+Tab would go to, so that a child learns
  them by seeing them; on a Mac, where the function keys are media keys
  first, `Alt+(fn)F4`, as `hid_apple`'s `fnmode` says, and `⌘` for the
  key that goes home. keys.md says how a keyboard that sends something
  else is added. Steps 3.22 and 3.23. *The keys written beside the
  buttons: superseded by D64, which makes them the buttons' tooltips.*
- **D62 — The network from the adult panel, through NetworkManager.**
  Decided 2026-09-28 by the owner, from the first hand test of labwc on the
  MacBook: an adult must be able to see the machine's connection and fix it
  without a terminal. The panel gets a fourth page, *Network*, and the
  daemon an interface, `Network1`, both adults only: each connection with
  its network and address, whether the router answers one ping, and, when
  NetworkManager manages the Wi-Fi, the networks in reach, joined with
  their password or forgotten. NetworkManager is Kidux's network stack
  (`kidux-base` depends on it and on `wpasupplicant`): it keeps a Wi-Fi up
  before anyone signs in, from a connection file the daemon writes for the
  whole machine, root's and 0600, so that the password is on no command
  line. A Wi-Fi the Debian installer set up with `ifupdown` is left alone
  and shown read-only, with the user guide saying how to hand it over; a
  wired connection another tool manages, as on the test machines, too. The
  daemon may not open an internet socket, so the ping runs in a transient
  unit of its own. Nothing else of the network is offered: addresses,
  proxies, VPNs and an office's Wi-Fi are set up from Debian. Step 3.23.
- **D63 — What does not fit scrolls, and shows it.** Decided 2026-09-29 by
  the owner, before the second hand test's fixes were tried: what a screen
  holds grows, with more children, more modules, more updates, a smaller
  screen or a larger scale, and no screen can be drawn for every case. So
  every part of a screen whose content can grow scrolls where it does not
  fit, down and sideways, and shows it without anyone having to try: its
  scrollbar is drawn for as long as there is more, in Kidux's browns and
  wide enough to see, where GTK's own, an overlay, hides until the pointer
  moves; a shade lies along each edge beyond which there is more; and the
  bar's row of buttons, which has no room for a scrollbar, gets an arrow
  either side while its buttons do not all fit, and brings the one in use
  into view. `kidux.scroll` makes such an area for the greeter and the
  launcher alike. Each screen is still meant to fit 1280x800 whole (D30),
  and the session tests still fail on one that does not; a screen that
  must scroll is logged, tall or wide. Lists are not cut short to fit: the
  Network page lists every network in reach. Step 3.25.
- **D64 — The bar's room is the modules': keys and the time left on hover,
  and Alt+Tab going round with the bar.** Decided 2026-09-29 by the owner,
  from the third hand test on the MacBook, who found the keys written
  beside the bar's buttons (D61) and "51 minutes left" taking the room of
  the modules' buttons. The keys are the buttons' tooltips: Home's says
  the key that goes home, Close's `Alt+(fn)F4` or `Alt+F4`, and the one
  Alt+Tab would go to says `Alt+Tab`. The time left is an hourglass and
  the time as a clock reads it, `00:51`, the sentence on hover and on a
  tap, on the bar and on the child's screen alike. The modules' buttons
  take all the room between Home and the time left. Alt+Tab goes round
  with the bar, as a desktop's switcher does, instead of labwc's
  `NextWindow`: labwc sends the launcher a signal for Alt+Tab and one for
  Alt+Shift+Tab; each is a step round the launcher's window and every
  module's, in the order they were last in use; the bar lights the
  button of the one pointed at, and follows the keyboard's state, which
  labwc sends every program, until Alt is let go, which goes there. A
  quick Alt+Tab is still the window used before. Step 3.27. *The order last used,
  with Home in the round: superseded by D66.*
- **D65 — The pictures in each language.** Decided 2026-09-29 by the owner:
  the English user guide and README showed the Spanish screens. The session
  tests run twice in the battery, on a machine set up in Spanish and on one
  set up in English, at the same time; each language's pictures go to
  `docs/images/<language>/`, and each document shows its own. Photographing
  the screens again in a second language on one machine would reach only the
  screens a script can get back to; a whole run in English also tests every
  screen in English. The README shows the sign-in screen, a child's screen,
  the adult panel and GCompris. Step 3.28.
- **D66 — Alt+Tab goes round the modules in the bar's order, and Home is not
  in it.** Decided 2026-09-30 by the owner, from the fourth hand test: the
  round of D64 went through the windows in the order they were last used,
  the launcher's among them, so a child holding Alt could not tell where the
  next Tab went and was sent home by a key meant for the modules. The round
  is the bar, left to right: from the module after the one on screen, and
  from the last to the first; from the launcher's screen, the first. Home is
  not a module: Super goes home, and Home's tooltip says Super alone, while
  the module Alt+Tab would go to says `Alt+Tab`. On the desk, the same with
  the windows in the bar's order. Step 3.29.
- **D67 — A session left alone locks itself, the screen turns off, and
  closing the lid locks; the minutes are the adult's to set.** Decided
  2026-09-30 by the owner, from the fourth hand test: a child walks away
  and the session stays open, spending the day's time and open to anyone,
  and a dark backlight was the only sign. After `idle_lock_minutes` without
  a key or a movement (default five) the child's session locks, as the Lock
  button does, so the counter stops (D13); after `screen_off_minutes`
  (default ten) the screen is turned off through the compositor, on a
  desktop as on a laptop, and comes back with the first touch; closing the
  lid locks the session and powers the panel off. Both numbers are on the
  panel's System page, and the panel's own timeout is the first of them,
  replacing D26's fifteen minutes. A session counts only while its
  terminal is the active one, and never fires a timer that expired under
  the lock screen. Step 3.30.
- **D68 — A program that is not in trixie is built at development time in a
  machine of its own, published as a tarball, and packaged from it.**
  Decided 2026-09-30 by the owner, for the Scratch family: Scratch,
  TurboWarp, ScratchJr's desktop port and Blockly Games are built with
  Node.js or Java from their repositories, with the network, which the
  package build has not (D23). `ci/build-upstream.sh` builds them on the
  development machine, with a pinned Node.js release of its own and the
  tools packaging.md lists, from a commit pinned in the package's
  `upstream.toml`, and leaves a tarball whose SHA-256 is recorded there
  and committed; the tarball lives in a GitHub release of this repository
  and in `build/upstream/`, never in git; `ci/build-package.sh` stages the
  package from it, and the `.deb` is reproducible as every other. A new
  build of the program is a new version, never the same version with other
  bytes. What the development machine has installed never stands in for a
  dependency: a Kidux machine gets what a package's `Depends` names, and the
  test machines, which start from Debian, are where a forgotten one shows.
  Step 4.1.
- **D69 — The Scratch family, and what Chromium lets a child do with their
  files.** Decided 2026-09-30 by the owner. Two Scratch editors, each a
  module, both served locally and opened in Chromium's application window:
  the official editor (`scratch-editor`, AGPL-3 since November 2024, which
  the GPL-3 of Kidux is compatible with), and TurboWarp, the fork with a
  compiler that runs projects many times faster, for a slower computer or
  when Scratch does not run well; neither has cloud variables nor the
  community. Their libraries of characters, backdrops and sounds come from
  the Scratch Foundation's servers when a child opens them: the machine has
  the internet, as GCompris already needs it, and mirroring the library is
  not worth its size. ScratchJr, for the youngest, is the community
  desktop port of MIT's own HTML5 app in Electron, built for Linux and
  packaged with its Electron, since MIT ships no Linux or web version and
  running the tablet or Windows apps through an emulator or Wine would be
  the same web code under a heavier wrapper. Blockly Games, Google's
  puzzles, are a module of their own between the two. Chromium's policy
  (D36) allows file dialogs and downloads that are not dangerous file
  types, so that a child saves a project into their home and opens it
  again, and allows the library's hosts; everything else stays closed.
  Steps 4.4 to 4.7.
- **D70 — The test modules say so in their names, and are not in the user
  guide.** Decided 2026-09-30 by the owner: *Hello*, *Hello on the web*,
  the canary and the robin exist to test the framework, and an adult who
  saw them on the panel took them for something to use. Their names begin
  with `[Test]` (`[Prueba]` in Spanish), the guide's section 9 lists only
  the modules a child is meant to use, and the developer documents keep
  them as the reference. Step 4.2.
- **D71 — Everything an upstream build fetched is published beside what it
  built.** Decided 2026-09-30 by the owner. The source of a program built
  at development time (D68) is more than its repository at the commit: its
  build installs hundreds of npm packages, and some fetch other
  repositories, Electron and Node.js, and any of them can vanish. And
  Scratch's AGPL-3 and TurboWarp's GPL-3 ask whoever gives the built
  program to give its source, which a link to someone else's repository
  does not guarantee. So each build fetches only through one helper,
  `ci/upstream/fetch.sh`, npm and Electron keep their caches where the
  build says, and `ci/build-upstream.sh` packs all of it, with the Node.js
  release and its own scripts, into a source tarball published in the same
  GitHub release as the built one, its SHA-256 recorded in `upstream.toml`
  as `source_sha256`. `ci/build-upstream.sh <package> --from-source`
  builds the program again from that tarball alone, with npm offline, in a
  network namespace where nothing answers, and checks the result is the
  recorded bytes; that is how each source tarball is proved whole before
  it is published. Every part is under a licence that allows passing it
  on, and keeps its own notices. Step 4.4.
- **D72 — Partial tests while developing, the whole battery before pushing,
  and a battery that does only what has changed.** Decided 2026-10-01 by the
  owner, after a phase in which each step's battery took an hour and a
  battery failed for a test's own fault was run again whole. A change is
  tested on the quick loop's machine for what it touches; the whole battery
  runs in one go before the work is pushed, and a failure that is a test's
  own needs only that test run again alone (CLAUDE.md). And the battery
  does less of what it already knows: a package built from a source whose
  key (`ci/build-key.py`) is unchanged within a week is taken from the build
  cache, and one shown reproducible for that key is not built twice again;
  in English only the tests that photograph the guide's screens, set the
  machine up or check that every screen fits run, since everything else is
  the same in any language; *Unlock to save* lasts the machine's
  `save_minutes`, which the session tests set to one; and `tests/run vm up`
  keeps its machine as a snapshot and starts from it the next time.
- **D73 — The Modules page is by age, the test modules last, with a box to
  find one; a version is shown without how it was built.** Decided
  2026-10-01 by the owner, from reviewing the page with six modules on it:
  listed by id, the `[Test]` modules sat among the real ones, and an adult
  reads `0+git20240513` as noise. Both lists go from the youngest to the
  oldest, the test modules last, and say so in a line; a search box narrows
  them by name or description, for the adult who wants one in particular;
  and a version is shown without what follows a `+` (`15.2.0`, not
  `15.2.0+build2`), a program with no version of its own by its snapshot's
  date. *Unlock to save* stays at five minutes, `save_minutes` a setting
  the tests change and no page offers.
- **D74 — `kidux-base` recommends `firmware-linux`, the free and the
  non-free firmware together.** Decided 2026-10-01 by the owner. The
  drivers for a machine's graphics card and Wi-Fi are in Debian's kernel
  and in Mesa; what differs from one machine to the next is the firmware
  those drivers load, which Debian ships in `non-free-firmware`.
  `firmware-linux` brings all of it, and the kernel loads only what the
  machine asks for, so a Kidux installed on any old computer has what its
  graphics card needs, as the development MacBook has `firmware-amd-graphics`.
  It is a recommendation, so an installation without recommends leaves it
  out, and the installer of phase 2 ticks it by default and lets it be
  unticked. NVIDIA's proprietary driver stays out: `nouveau` serves an old
  card, and an adult who wants the other installs it from a terminal.
- **D75 — Chromium's policy allows `blob:` addresses, and ScratchJr takes the
  machine's Chromium options.** Decided 2026-10-01 from the owner's hand
  test of the editors on the development MacBook. Scratch saves a project
  by making the file in the page, giving it a `blob:` address and asking
  the browser to download that; the policy's `URLBlocklist` of `*` blocked
  the address, and Save did nothing. A `blob:` address is only ever made by
  a page already open, so allowing `blob:*` opens nothing to the internet;
  TurboWarp, which saves through the file system's own dialog, never
  needed it. ScratchJr's Electron is Chromium, and drew with the same
  noise and frozen pictures as Chromium did on the MacBook's Radeon before
  `--disable-gpu-compositing` (D52): its starter reads
  `/etc/kidux/chromium-flags` too, so one setting serves both.
- **D76 — A download asks where to keep it.** Decided 2026-10-01 by the
  owner. Scratch saves a project as a download, which went straight into the
  child's Downloads, while TurboWarp asks in the file dialog; a child who
  keeps projects in folders of their own, or names them, needs the dialog
  in both. Chromium's policy sets `PromptForDownloadLocation`, so every
  download in a web module opens the file dialog, in the child's Downloads
  folder, with the name the page gave it. It is the same dialog Load opens.
- **D77 — A development build is `<version>~dev.<time>`, below the version
  it tries.** Decided 2026-10-01 by the owner, advised that this is
  Debian's convention, after four packages on the development MacBook
  stayed at `+dev` builds that apt held over the versions the battery
  published, `+` sorting after a version. Debian's `~` sorts before it:
  the battery's build of a version replaces every try of it on every
  machine, and nothing has to be bumped at the end. The tree's version is
  therefore always one the archive has not published, bumped when a
  package is first changed, and `tests/run vm push` refuses a package the
  archive already holds at the tree's version or above.
- **D78 — Kidux's own work is under the Business Source License 1.1, and
  GPL-3.0-or-later four years after each version.** Decided 2026-10-01 by
  the owner, before the first public release, on advice. Kidux is meant to
  be free for a family, and the owner keeps the right to ask an
  organisation, a school or an academy, for a licence: free at first,
  against registration, paid if Kidux grows. The GPL forbids any condition
  on who uses a program or for what, and what is once published under it
  cannot be taken back, while a stricter licence can always be opened
  later. The BSL, MariaDB's text, which HashiCorp and CockroachDB use,
  gives everyone the right to read, change and pass on the code, grants
  production use in a household (its *Additional Use Grant*, `LICENSE`),
  leaves every other production use to a licence from the owner, and turns
  each version into GPL-3.0-or-later four years after it is published, so
  nothing stays closed for good. It covers Kidux's own work only: the
  programs Kidux starts and the modules' programs are separate works,
  reached over D-Bus, sockets and processes, never linked, and the
  libraries Kidux's code imports are LGPL, MIT or BSD, which allow any
  licence; the changes Kidux builds Scratch and TurboWarp with stay AGPL-3
  and GPL-3, their source published (D71). Each `debian/copyright` says
  `BUSL-1.1` for Kidux's files and the upstream licence for the program a
  module packages. Kidux is not called free software or open source: free
  for families, its code published. The name and the penguin are outside
  the licence, for a trademark. A contributor licenses their work to the
  owner so that the dual licence stays possible (`CONTRIBUTING.md`).
- **D79 — A website at kidux.org, donations through GitHub Sponsors, and
  one address to write to.** Decided 2026-10-02 by the owner. Kidux's
  website is one page, in English and Spanish, that shows a parent in a
  minute what Kidux is: a whole, safe system for a child; one thing on the
  screen at a time, and windows when the child is ready; learning modules
  set up and ready, with the focus on STEM; on the computer the family
  already has. It is built from `site/` by `ci/build-site.py`, its words a
  file per language with the same keys, its pictures the battery's own, and
  published by a workflow on GitHub Pages, at `kidux.org` (website.md). It says what D78
  says and no more: free for families; for a school or any other
  organisation the licence is free too and is asked for by writing, so
  that the owner knows where Kidux is used; the code published. A donation
  is made through GitHub Sponsors, from a button always in view on the
  page and from the repository's own. The address to write to, on the site
  and as the maintainer's in every package, is `info@kidux.org`; where
  Kidux's developer is named, the site and the READMEs link to
  `https://antonio.mg`.
- **D80 — The public repository's history begins at its first published
  version.** Decided 2026-10-02 by the owner. The repository was made
  public with the first ten days of development in it: commits signed with
  the owner's personal address, and Kidux's tree under the licence D20 gave
  it until D78. Its history now starts at one commit, the tree as first
  published under D78, and every commit is authored as
  `othermore <info@kidux.org>`, the repository's own `git config`. The
  earlier commits, whose messages say why each change of those days was
  made, are kept in a private repository.
- **D81 — Two ways to install: Kidux's own image, said to be coming, and on
  Debian, step by step.** *Said to be coming: superseded by D116, which
  made the image.* Decided 2026-10-02 by the owner. The README, the
  user guide and the website name both. The image is the one thing the
  user documents speak of before it exists: *coming soon*, and what
  installing from it will be, the image downloaded, written to a USB
  stick, an SD card or another external drive, and the computer started
  from it. Installing on Debian is the way there is: a Debian 13 with
  nothing else on it and a `/home` of its own, Kidux's archive added with
  the two bootstrap packages, and `kidux-base` installed, as the
  development machine was (rollout.md). The guide's section 2 writes it
  for an adult at a text console, every line to type, with the step that
  takes a Wi-Fi the Debian installer set up out of
  `/etc/network/interfaces` before the first restart, so that the panel's
  Network page can run it (D62). Its lines fetch from the archive's public
  address, `https://kidux.org/apt`, the move to a public URL that D2 left
  for the day the repository was public.
- **D82 — The stable suite is public at kidux.org/apt, signed with a key of
  its own; testing and the development key stay on the LAN.** Decided
  2026-10-02 by the owner. A family's machine has to fetch Kidux from
  somewhere anyone can reach, and until now the only archive was the
  development machine's (D2). The stable suite is published as it is,
  packed on the development machine and sent to a release of the
  repository, from which the site's workflow unpacks it under `apt/` of
  the same GitHub Pages site: no server of its own, nothing signed outside
  the development machine, and the indexes the workflow publishes are
  checked against the keyring first (packaging.md, "The public archive").
  `kidux-apt-source` names `https://kidux.org/apt`, suite `stable`.

  The key matters more than the address: whoever holds the key a family's
  machine trusts can install anything on it, unattended. The development
  key was made for the LAN, says so in its name, has no passphrase and is
  used by every test, so it is not that key. Stable is signed with a new
  one, `27E3FC17DBA9E4578268F8EEB3768AF190169C5E`, whose public part is all
  `kidux-archive-keyring` holds; testing keeps the development key, which
  the machines that follow testing take from beside the archive and no
  package ships. The new key has no passphrase either, the owner's choice,
  so that a release is promoted without anyone typing; it can be given one
  later without the machines noticing, since the public key does not
  change. A machine that follows testing turns the shipped source to the
  development archive and adds its key (rollout.md, section 3).

- **D83 — The website counts its visits with Google Analytics, and only
  after the visitor says yes.** *Superseded by D94.* Decided 2026-10-03 by the owner, on
  phase-4b-plan.md. The owner wants to know whether anyone comes, and from
  where. Google's tag, `gtag.js`, with the measurement id as a fact of the
  site, `analytics` in `site/site.toml`; empty, the page carries no tag and
  no notice. Google's tag sets cookies, and the rules where the owner lives
  (the AEPD's, in Spain) want the visitor asked first, so the page loads
  nothing of Google's until the visitor accepts in a notice at the foot of
  the page; a refusal loads nothing, both answers are remembered in the
  browser, and a link in the footer asks again. The site sets no other
  cookie.

- **D84 — BASIC is wwwBASIC behind an editor of Kidux's own, in the browser,
  with the guide beside it.** Decided 2026-10-03 by the owner, on
  phase-4b-plan.md. The BASIC a child learns from is the one of the first
  home computers, the one *BASIC para niños* teaches: numbered lines,
  `PRINT`, `INPUT`, `GOTO`, a screen of text that also draws, colours and
  sounds. And the owner wants the lesson on the same screen as the machine.
  No program in trixie gives both: Matrix Brandy draws in an SDL window that
  can share a window with nothing; PC-BASIC has no installable package in
  trixie; `bwbasic` is text in a terminal; `yabasic` has no line numbers.
  Writing an interpreter would be two thousand lines with a long tail of
  small differences to chase. So the interpreter is **wwwBASIC**
  (`github.com/google/wwwbasic`, Apache-2.0, one JavaScript file,
  maintained, with its own test suite): a QBasic/BASICA BASIC, the books'
  *conventional BASIC*, that runs in a page, draws its own text screen on a
  canvas with the look of the PCs of the time, has `INPUT`, `INKEY$`,
  `READ`/`DATA`, `DIM`, `ON GOTO`, the string functions, `PSET`, `LINE`,
  `CIRCLE`, `PAINT`, `COLOR`, `BEEP`, `SOUND` and `PLAY`, and runs a program
  in slices so that a loop that never ends can be stopped. It arrives as
  every program not in trixie does, a pinned commit built into a tarball
  (D68, D71). Kidux adds no immediate mode and changes nothing in it: the
  child writes the program in an editor, presses *Run*, and sees it on the
  screen below; the guide is written for this machine, not for the one in
  the books, so what wwwBASIC does not do (`CONT`, reading a variable after
  a run, `GO TO` with a space) the guide does not teach. A child's programs
  are saved and opened as files, as Scratch's projects are (D75, D76), and
  the one being written is kept in the browser's storage between sessions.
  BASIC's words are the same in every language; the module's own words and
  its guide are in both.

- **D85 — A web module may be a door to one website on the internet, held to
  that site's hosts: the policy is the machine's ceiling, a proxy is the
  module's wall.** Decided 2026-10-03 by the owner, on phase-4b-plan.md. D42
  foresaw a module that opens the web with a list of sites, switched on by
  an adult like any other. Chromium's managed policy is one for the whole
  machine and cannot hold one module to one site, so a module names its
  hosts in its manifest (`hosts`), `kidux-webapps` writes the policy from
  the manifests of the installed modules, its `URLAllowlist` the union of
  their hosts, and `kidux-webapp` starts every module's Chromium with a
  proxy that answers nothing (`--proxy-server=127.0.0.1:1`) and a bypass
  list of the module's own hosts, which is what confines each module to its
  site, the policy still refusing whatever no installed module names.
  Chromium honours these as documented (tried 2026-10-03: a host not in the
  bypass list fails with `ERR_PROXY_CONNECTION_FAILED` under the policy as
  it is). Scratch and TurboWarp name their library hosts the same way, and
  the policy carries no host of its own. A `web` module gets no
  `--enable-unsafe-swiftshader`, which is unsafe for pages from anywhere.

- **D86 — CodeCombat is a door to codecombat.com, nothing of it shipped, and
  Kidux says it is not connected with CodeCombat.** Decided 2026-10-03 by
  the owner, on phase-4b-plan.md. The levels are proprietary and cannot be
  served locally (architecture.md section 8); the site is translated and
  teaches real Python and JavaScript. The module reaches CodeCombat's own
  hosts and no other: an account is signed in with email and password, the
  sign-ins through Google, Facebook or Clever lead nowhere, a subscription
  is bought by the adult on another computer, and the module's words say the
  site is CodeCombat's, that most of it needs a paid subscription, and that
  Kidux has no connection with CodeCombat Inc.

- **D87 — Wikipedia is a door to the whole encyclopedia in the child's
  language, and the Wikimedia projects, with the rest of the internet
  closed.** Decided 2026-10-03 by the owner, on phase-4b-plan.md. The
  address is the child's language's edition; the hosts are Wikipedia's,
  Wikimedia's (where the pictures come from) and the sister projects'. It is
  the whole of Wikipedia, written for everyone, and the module's words say
  so, so that an adult switches it on knowing it.

- **D88 — Small fixes to wwwBASIC are kept as patches in the module.**
  Decided 2026-10-03 by the owner, during step 4.11, refining D84, which
  changed nothing in wwwBASIC. Writing the guide's second part found
  wwwBASIC's `SLEEP` broken in `wwwbasic.mjs`, the file the page loads
  (its `wwwbasic.js` has the fix), and its `TIMER` counting from 1970, a
  number too long for a single-precision variable, so that `T = TIMER`
  lost the seconds. Working round both in the guide meant teaching a
  child double-precision variables to wait a second. A small fix to
  wwwBASIC, when it is simpler than working round it, is a patch in
  `packages/kidux-module-basic/patches/`, applied at build time to a copy
  of the file, so that the tarball stays wwwBASIC's own and what Kidux
  changed is plain to read; the patched file says so at its top, as the
  Apache licence asks. Nothing is added to wwwBASIC's language: a statement
  it lacks, such as `PLAY`'s tunes, is still left out of the guide
  (docs/dev/basic.md, section 2).

- **D89 — A removed module's directories stay in the child's home.**
  Decided 2026-10-03 by the owner, during step 4.13. Removing a module
  removes its package, but not the three directories each child has of it,
  `~/.config/kidux/<id>/`, `~/.local/share/kidux/<id>/` and
  `~/.cache/kidux/<id>/`: they may hold a child's progress, settings or
  work a module kept for itself, and a module installed again finds them.
  The documents had said removing a module removed them, which nothing
  did; they now say what is done.

- **D90 — A module declares the settings an adult gives it for each
  child.** Decided 2026-10-03 by the owner, on phase-4c-plan.md. BASIC's
  *Type it in for me* and a child's CodeCombat account are settings that
  differ from one child to another and that only the module understands.
  Each module declares its own in its manifest, `[[settings]]`, each with
  a key, a kind of five (switch, integer, number, text, secret), a label
  and a description of what it does, both translated through the
  module's catalogue, and a default; Kidux keeps no list of them and knows
  only the kinds. The daemon keeps each child's values, root's alone, and
  refuses a value not of its kind; the panel shows them in a page of the
  module's own; the launcher hands them to the module in its environment,
  and `kidux-webapp` in a web application's address. A secret never
  reaches the child's session: the daemon uses it itself.

- **D91 — Chromium's DevTools are allowed by the policy, and their pages
  stay blocked.** Decided 2026-10-03 during phase-4c-plan.md's 4.17,
  refining D36. `kidux-webapp` signs a child in to a module's website by
  driving its Chromium through `--remote-debugging-pipe`, a pipe only it
  holds, and `DeveloperToolsAvailability` 2, which D36 set, refuses that
  pipe too. It is 1 now; the tools a child could open with F12 or
  Ctrl+Shift+I stay closed, since their pages are addresses the policy's
  `URLBlocklist` of `*` blocks, and Chromium says *DevTools is not allowed
  on this page* (tried 2026-10-03); the daemon still refuses every flag
  that would open a debugging port or another profile.
- **D92 — The panel's pages of settings may scroll.** Decided 2026-10-03
  by the owner, refining D63: the Advanced page, and the page of a
  module's settings, grow as modules and machines bring more settings, so
  they are not held to fitting 1280x800 whole. They scroll where they do
  not fit, and show it, as every screen does; the greeter does not log
  them as screens that should fit (`GROWS` in view.py), and every other
  screen still must.
- **D93 — A version made only of numbers is a release, built once every
  test and the owner have passed the work.** Decided 2026-10-03 by the
  owner, refining D77. A release never changes: a version once published
  keeps its bytes, and the next change to the package goes under the next
  number. A package gets that number at its first change in a piece of
  work, and everything until the release is a `~dev` build of it, the
  quick loop's pushes and the battery's own builds alike, which the
  testing archive and the owner's machine take. So the numbers run on
  without a gap, since no number is spent on a try that turns out wrong,
  and no release goes out unreviewed: the battery must have passed, the
  owner must have tried the work and said yes, and the further review the
  owner asks for, when they ask for one, is done first. Then
  `ci/test-release.sh <label> --release`, which takes a battery of the
  same commit, or of one the commit differs from only outside the
  packages' sources, builds the versions themselves,
  the bytes the reproducibility stage already built twice and kept, publishes
  them into testing in place of the `~dev` builds, runs every test again
  on them and writes the guide's pictures, which only a release run does;
  the push, `ci/promote.sh` and `ci/publish-public.sh` follow, each on the
  owner's word. Nothing is released as part of developing or testing.
  Before D93 the battery published each version it tested, so a fix found
  after a battery cost the next number.
- **D94 — The website counts every visit: Google Analytics with consent,
  Google Analytics in consent mode without it, and GoatCounter always.**
  Decided 2026-10-04 by the owner, replacing D83, whose notice, a thin bar
  at the foot of the page in the page's own colour, was easy to miss, and
  a visit went uncounted until it was answered. Three counts:
  - **Google Analytics with consent.** A card in the brand's night over
    the page's corner asks whether it may use cookies, to tell a new
    visit from a returning one; a yes grants Google's tag its storage.
    The two answers weigh the same, and the card says what each does.
  - **Google Analytics in consent mode without it.** Google's tag loads on
    every visit with its storage denied, and counts the visit without
    cookies until a yes, and after a no.
  - **GoatCounter in any case.** It uses no cookies and counts every
    visit, `goatcounter` in `site/site.toml`, so that the owner can compare
    it with Google's and keep one; the footer says so.
- **D95 — Mail is Thunderbird, with the account an adult gives and its
  policies closing what a child could break.** Decided 2026-10-12 by the
  owner, on phase-4d-plan.md, and 2026-10-15 after its step 4.21. A
  child's mailbox is Debian's Thunderbird, not a client of Kidux's own: it
  signs in to Google and Microsoft by itself and speaks IMAP to every
  other provider. The adult gives the address, the name and, for a
  provider Mozilla's autoconfiguration database does not know, the
  servers, as the module's settings (D90); never a password, which
  Thunderbird asks for once and keeps in the child's profile, as any mail
  client keeps it on a shared Linux machine, while Google and Microsoft
  accounts have none to give, only a sign-in in their own window. The
  module writes Thunderbird's `user.js` afresh at every start, so the
  account a child changes or adds is back as given the next time, and
  ships `/etc/thunderbird/policies/policies.json`, which closes updates,
  add-ons, `about:` pages, the primary password, chat, the choice of
  another program for a link or an attachment, and the pop-up notices a
  kiosk would show full screen. Google does not let a Family Link account
  sign in to Thunderbird (tried 2026-10-12), so Mail serves every other
  account and Gmail, a door module, serves that one.
- **D96 — Gmail is a door to its website, and a website's address may
  name a module's settings.** Decided 2026-10-12 by the owner, on
  phase-4d-plan.md, and 2026-10-15 after its step 4.21. Gmail is the way
  for a Family Link account (D95), and for a family that prefers the
  website: a door module (D85), its Chromium walled in to Gmail's own
  hosts, read from Chromium's net log, and to the `accounts.` host of
  every domain Google lists as its own, since signing in passes through
  the family's country's (`accounts.google.es` in Spain); never Google
  whole, nor Search, Play or Drive. It opens Google's sign-in for Gmail
  with the child's address in it, which Google's page takes from its
  address: `kidux-webapp` puts a module's settings into a website's
  address where it names them in braces, as it puts the language in
  `{lang}`, encoded and never a secret. The adult signs in with the child
  the first time, in Google's page, and the module's Chromium profile
  keeps the session (D89); the daemon holds nothing of it.
- **D97 — The keyboard's light goes off with the screen and comes back as
  it was.** Decided 2026-10-12 by the owner, on phase-4d-plan.md, refining
  D61, from the MacBook: closing the lid turned the screen off and left the
  keyboard lit under it. Wherever the screen goes off for the lid or for
  being left alone, the launcher, `kidux-lid-watch` on the trusted screens
  and `kidux-idle`, the keyboard's light goes off after it, its level
  remembered, and comes back before it, as it was; a level already
  remembered is kept, and a light already off stays off. The level is
  remembered in `/run/kidux-light/`, group `video`, which a child's session
  and the trusted screens share, since a lid closed in a child's session is
  opened on the lock screen; where it cannot be remembered, the light is
  left on. The screen's own brightness is still left alone.
- **D98 — Kidux shows a module's notices itself, as a bubble.** Decided
  2026-10-15 by the owner, on phase-4d-plan.md's 4.26. A program tells its
  user something through the desktop's notifications; a child's session
  had nobody to show them, so Thunderbird showed its own notice, a window
  with no parent that labwc maximised over everything and that neither
  Escape nor time closed, and silencing it hid why a Family Link mailbox
  stayed empty. The launcher owns `org.freedesktop.Notifications` on the
  child's session bus and draws each notice as a bubble rising from the
  bar, above its right end, on gtk4-layer-shell's overlay layer, from the
  module whose scope sent it: eight seconds, or until it is closed when
  its program marks it urgent or never expiring; never a sound; never on
  the sign-in or lock screens, which run no launcher. The bar's bell, at
  its right end, keeps the last twenty, gone or not, with how many came
  since the child last looked, so that a notice missed, or one an adult is
  asked about, is read again. The launcher's own warnings that time is
  running out are bubbles too, from Kidux, staying until closed: the bar
  keeps only the time left. Websites never notify:
  Chromium's policy blocks it (`DefaultNotificationsSetting` 2). Not
  `mako`, `dunst` or `fnott`, all in trixie: none speaks Kidux's language
  or looks like it, or knows a module from a program.
- **D99 — Kidux is seen working on GitHub only in the evening and at the
  weekend.** Decided 2026-10-16 by the owner. Nothing of Kidux's reaches
  GitHub, or carries a time that is read there, outside Madrid's 19:00 to
  02:00 around a weekday night and the whole weekend. The work itself goes
  on whenever it does, in commits as encapsulated and reviewable as ever;
  what changes is their dates, set at the push: `ci/push.sh`, the one way
  to push, dates the commits not yet on GitHub inside the hours, the
  author's and the committer's dates alike, and pushes, now or by a timer
  at the hours' next opening, so that nobody has to wait for them; the
  release of the archive on GitHub keeps to them too. A changelog's date
  comes from `ci/hours.py changelog-date`, the last moment inside the hours
  not after now, since a changelog date is in the package and in the
  repository; a date in the past keeps a build reproducible (D23). A
  commit once pushed never changes. *The hours themselves, 19:00 to 02:00
  and the weekend: superseded by D114, which widens them.*
- **D100 — Removing a module takes with it what was installed for it
  alone.** Decided 2026-10-16 by the owner. `remove` is `apt-get purge
  --auto-remove` of the module's package: Thunderbird and its sixty-five
  language packs go with Mail, GCompris with its module. A program nothing
  else needs has no business on a child's computer, and a family machine
  holds nothing an adult installed by hand for apt to mistake; the
  children's own files stay. Installing the module again brings it all
  back.
- **D101 — A module that is only a folder is said so, and Remove takes the
  folder away.** Decided 2026-10-16 by the owner, on phase-4e-plan.md's
  4.27. A folder under `/usr/share/kidux/modules/` that no package put
  there, as the tests' stand-ins are, answered *That did not work.* to
  *Remove*, since apt had nothing to purge. Its row on the Modules page
  says it is a folder, not from a package (`kidux.modules.Module.package`,
  from dpkg's list of the package's files), and Remove asks to remove the
  folder; `kidux-update remove` takes it away and writes Chromium's
  policy again, as a package's removal does, in the same job, with the
  same rules and the same audit line. The update runner does it and not
  the daemon, whose system is read-only to it (`ProtectSystem=strict`).
  This extends D100.
- **D102 — The photography guide shows photographs a camera took, and a
  generated picture only where none is found.** Decided 2026-10-16 by the
  owner, on phase-4e-plan.md. A guide that teaches what a camera does
  shows each effect in a photograph that came through a lens: a free one
  from Wikimedia Commons, under CC0, CC BY, CC BY-SA or in the public
  domain, credited under it and in `debian/copyright`, or, later, one of
  the owner's. Where a chapter needs one scene with a single thing
  changed, one photograph is changed as a camera would change it, in
  linear light, and its credit says so. A picture generated with Gemini's
  image model is allowed only for an effect no photograph shows, since a
  generated depth of field did not come through a lens and may lie in its
  details; it is credited as made by a computer, its prompt kept beside
  it, and the key is a file outside the repository. Ideas and the
  camera's screen are drawings of Kidux's own. No picture shows a child's
  face.
- **D103 — A generated picture also where a free photograph does not show
  the effect clearly.** Decided 2026-10-17 by the owner, after the
  course's first draft; this extends D102. A chapter that teaches one
  thing at a time is best shown by one scene with only that thing
  changed: the focus moved from a near toy to a far one, a tap at 1/1000
  and at 1/8, a coin lit from the front and from the side. Free pairs of
  that kind are rare, and the ones found showed their effect faintly or
  across two different scenes. Gemini's image model, given its own first
  picture and told what to change, makes such a pair; each is looked at
  for its physics before it is kept, credited as made by a computer, and
  named in the chapter's box for the adult. A free photograph that shows
  its effect clearly stays, and a picture of the XZ-2 itself is never
  generated.

- **D104 — A program of KDE's runs as a module with KDE's action
  restrictions in the module's own configuration.** Decided 2026-10-16 by
  the owner, on phase-4f-plan.md. Kig, Kalzium and Step come from trixie
  as they are; each module ships a `kdeglobals` of KDE's action
  restrictions beside its manifest, which its starter puts first in
  `XDG_CONFIG_DIRS`, where every program of KDE's reads it: no Get Hot
  New Stuff (downloads from store.kde.org, Step's *Download New
  Experiments*), no shell, no handbook, bug report, donation page or
  language switch in the Help menu, which open a web browser the child
  has not or change the session's words, and no whole screen, which a
  module never asks for. The file is the package's, immutable and always
  current, and nothing is written into the child's configuration for it.
  Each module depends on its program and on the Wayland plugin of its Qt,
  which the program's own package does not bring.

- **D105 — PhET's simulations are shipped in the versions published under
  CC BY 4.0, in a module named Simulations.** Decided 2026-10-16 by the
  owner, on phase-4f-plan.md. PhET publishes its simulations since 29
  March 2026 under CC BY-NC 4.0, which Kidux's licence to organisations
  cannot carry; the versions published before, by PhET's agreement for
  its historical collection, are CC BY 4.0. The module serves, for each
  simulation, the newest version PhET still serves that was built before
  that day and does not name CC BY-NC, fetched as PhET built it and never
  changed, with PhET's attribution beside it; the build refuses any other.
  The module's name says what it is, not PhET's, which is a trademark,
  and its description names PhET as the simulations' author and says that
  Kidux is not connected with PhET. The current versions, if ever wanted,
  would be a door to PhET's site (D85), shipping nothing.

- **D106 — A module may have a guide, shown by the launcher in a pane of
  its own on the right.** Decided 2026-10-17 by the owner, on
  phase-4g-plan.md. A child opening Kig or Step meets an empty canvas and
  forty tools; lessons of Kidux's own, with steps, pictures, the mascot and
  missions, files of the program's half done, show beside the program.
  The pane is the launcher's own layer surface on the right edge with an
  exclusive zone, not a second window the compositor places: it works the
  same with windows and without, needs no window rules, and follows the
  module on screen; it folds to a rail for room. Without windows it shows
  the guide of the module on screen and goes for one without; with
  windows it stays while a module with a guide is open, shows the one in
  use, keeps the last one shown, and lets the child pick one and pin it.
  The lessons are a small Markdown the launcher draws, since a browser in
  the launcher would be a second engine on the machine (D36); the
  missions are copied into the child's Documents and opened from the
  program's own File, Open, which is itself a thing to learn, and which a
  second start of a program already open could not do but in a second
  window.
- **D107 — A link out of a module opens nothing, and a bubble says so.**
  Decided 2026-10-17 by the owner, on phase-4g-plan.md. Step's *Open in
  browser*, a link in a program's help, or anything else that asks the
  desktop to open a web page started a plain Chromium window in the
  child's session, with tabs and an address bar, outside every module's
  wall. The child's session makes `kidux-closed` the default for web
  pages and links, through a `mimeapps.list` and a desktop file in
  directories it puts first in `XDG_CONFIG_DIRS` and `XDG_DATA_DIRS`,
  which `xdg-open`, GLib and KDE's KIO all read; it sends the bubble
  *That opens the internet, which is closed here.* from the module that
  asked, and opens nothing. A program's own setting for a browser was the
  alternative, one per program and not every program has one; a module
  that is a web page starts its browser itself and is not touched.
- **D108 — Kidux's security is a well-kept Debian's, and an audit's
  suggestions beyond it are declined on purpose.** Decided 2026-10-18 by
  the owner, on an audit of the whole tree by Gemini. The owner's rule: a
  child who can defeat an unprivileged Unix user with no shell, no browser
  and no `sudo` has outgrown Kidux, so the system is not hardened against
  that child; what it must be is robust, scalable and maintainable for
  years. The audit's eight points, and what came of each, so that the next
  audit starts here (section 5, "What Kidux defends against, and what it
  leaves alone"):
  `DeveloperToolsAvailability` 1, kept (D91, and the pages blocked);
  polkit's unconditional yes to `_greetd`, kept (D27); the proxy bypass
  list, narrowed to the server's port, `127.0.0.1:8123`, a one-line
  tightening with no change in what a page can reach, since the policy
  allowed that port alone already; bubblewrap or AppArmor around KDE's
  programs, declined (D42); the GRUB recovery password in clear, kept
  (D25, with its hash beside it); labwc's `pkill -f`, kept (D45, D57,
  D64); first boot's administrators, now found by each user's groups and
  not the group's member list, which missed a user whose primary group is
  `sudo`; window rules pinning a guide's geometry, declined, since the
  launcher owns the pane and labwc maximises every main window already
  (D106); and modules as Flatpak-like bundles, declined (D31, D42, and the
  working agreement that Flatpak is plan B only).
- **D109 — The stable suite is public at `apt.kidux.org`, on a web hosting
  of the project's own, for the count its logs give.** Decided 2026-10-18
  by the owner, refining D82's address and keeping D82's key. GitHub Pages
  served the suite well and logged nothing, so the project could not say
  how many machines follow it nor which modules they install. The suite
  now goes over SFTP to the folder `apt` of the owner's OVHcloud web
  hosting, served as `https://apt.kidux.org` with a Let's Encrypt
  certificate, in an order a machine can fetch from at any moment, and
  `ci/publish-public.sh` checks afterwards what the address serves
  (packaging.md, "The public archive"). The hosting's git integration was
  the alternative, declined: it deploys a GitHub repository, which caps a
  file at 100 MB when ScratchJr's package is 119 MB, grows by a suite per
  release for ever, and puts GitHub back in the way. Every fetch says it
  is a Kidux machine's, through a `User-Agent` `kidux-apt-source` sets, and
  nothing more; an identifier of the machine's own goes with it too, which an
  adult may turn off from the panel. The old address keeps serving the same suite
  while the machines installed before `kidux-apt-source` 0.1.5 follow it,
  since Pages cannot redirect in a way apt follows; then the tarball and
  the site's job go.
- **D110 — Kidux is free software, under the GNU General Public License,
  version 3 or later.** Decided 2026-10-18 by the owner, superseding D78.
  D78 kept Kidux under the Business Source License so that the owner could
  ask an organisation for a licence, free against registration, which was
  the one way to learn where Kidux is used. The archive's own server
  (D109) gives that sight without asking anyone for anything: its logs say
  how many machines follow Kidux and which modules they install. So the
  reason for a licence that is not free is gone, and the GPL says what
  the owner wants said: anyone may use, study, change and share Kidux, a
  family and a school alike, and what is built on it stays free.
  `LICENSE` is the GPL's text; every `debian/copyright` says
  `GPL-3.0-or-later` for Kidux's files and the upstream licence for the
  program a module packages; the pictures Kidux made for Photography carry
  the same licence; the website, the READMEs and `CONTRIBUTING.md` say
  Kidux is free software, and a contributor's change is published under
  the same licence rather than licensed to the owner. The name and the
  penguin stay outside the licence, for a trademark. Each package gets its
  next version with the change, since `debian/copyright` is part of it.
- **D111 — BASIC installs wwwBASIC as it is published.** Decided
  2026-10-18 by the owner, refining D88. The one patch D88 brought,
  `SLEEP` reading its number in `wwwbasic.mjs`, was sent to wwwBASIC from
  the owner's fork and merged as its pull request 61. So `upstream.toml`
  pins the merge, `dda9602`, the package copies `wwwbasic.mjs` unchanged,
  and `patches/` and its step in `debian/rules` are gone: a program as its
  authors publish it is one thing less to keep. D88 stands for the next
  fix: a patch while wwwBASIC has not taken it, offered upstream, and
  dropped once it is in.
- **D112 — A module stopped by force is killed five seconds later, and Tux
  Typing has Kidux's own lessons.** Decided 2026-10-18 by the owner, on the
  owner's finding that Tux Typing's lessons opened nothing, refining D45.
  Tux Typing lists the lessons of its theme and opens them from the theme
  too, so that Debian's Spanish theme, which has none, listed the English
  drafts by their file names and opened nothing; and its Spanish keyboard
  table lost its ñ to a character that replaced it, so that a practice
  with ñ drew a second keyboard. Patching Tux Typing would mean building it
  rather than taking Debian's; Kidux instead brings a theme of its own for
  each language it has lessons in, `kidux-es` and `kidux-en`, with Tux
  Typing's words linked and twelve lessons of its own written as data and
  checked at build time against what the program can show
  (`lessons/build.py` of kidux-module-tuxtype). Trying them found that Tux
  Typing, made with SDL 1.2, turns SIGTERM into a quit it does not heed on
  its lessons' list, so that *Close it anyway* left it on the screen for
  the user manager's ninety seconds: every module's scope now has
  `TimeoutStopSec=5s`, the time a program that saves on SIGTERM needs and
  no longer than a child waits. *Taking Debian's Tux Typing rather than
  building it: superseded by D113, which builds it with patches of
  Kidux's.*
- **D113 — Kidux builds Tux Typing itself, with patches for keyboards
  other than the US one, and its course has the accents.** Decided
  2026-10-18 by the owner, on the acceptance test of D112's lessons,
  refining D112. Four things no theme can put right are Tux Typing's own
  code: its practice learns where a key is from each key pressed, through
  a list of the US keyboard's keys, so that the ñ, the comma, the full stop
  and the hyphen of a Spanish keyboard lost their finger the first time
  they were pressed; the dead key of an accent counted as a wrong key, and
  the games took it for a letter; its keyboard labelled every key twice,
  the capital over the small letter, or only the keys of earlier
  practices; and its games' menu listed a theme's word lists in the
  disk's order. So Kidux builds Tux Typing from Debian's own source, 1.8.3
  as Debian's 1.8.3-7 patches it, with four small patches of its own, as a
  package of its own, kidux-tuxtype, which installs
  `/usr/games/kidux-tuxtype` beside Debian's `tuxtype` and reads Debian's
  tuxtype-data; the module runs it. Its source is taken as files by their
  SHA-256 from snapshot.debian.org (D68's way, as PhET's simulations are),
  and the patches are kept in the package, as D88 has them, to offer to
  Tux4Kids, though its repository has had no release since 2014. On top,
  the module's data: each language's keyboard table gives every key its
  place, the keyboard of a practice labels the keys of that practice
  alone, so that a child finds them at once, the Spanish course ends with
  two lessons of the accented vowels, and the Spanish games have word
  lists of Kidux's own, with the ñ in all and the accents only in the
  last, as the owner asked.
- **D114 — The hours Kidux is seen working on GitHub run to 03:00, and
  Monday is a whole day of them.** Decided 2026-10-19 by the owner,
  refining D99. The hours are Madrid's 19:00 to 03:00 around a night from
  Tuesday to Friday, and the whole of Saturday, Sunday and Monday, so from
  Friday 19:00 to Tuesday 03:00 without a break. Everything else of D99
  stands: `ci/push.sh` the one way to push, the commits dated inside the
  hours at the push, the changelog's date the last moment inside them not
  after now, the archive's release on GitHub keeping to them.
- **D115 — Debian's daily upgrade is fenced as the panel's install is.**
  Decided 2026-10-19 by the owner, on finding that the daily upgrade,
  which installs Kidux's stable suite as well as Debian's security
  updates, ran under a child's session as readily as under none, against
  the rule the panel's *Install* keeps and the user guide states. It stays
  Debian's, with a condition from kidux-base that skips it while a child
  has a session; the daemon keeps children from signing in while it runs;
  and a run skipped for a child is made up when the last child logs out,
  so that a machine in use every morning still gets its updates that day
  (daemon.md, section 13; updates-plan.md). The lists' daily refresh,
  which installs nothing, is left alone.
- **D116 — Kidux's image: an installer made on the release machine,
  published with every release, and trial images made from it.** Decided
  2026-10-19 by the owner (phase-2-plan.md). The image is a hybrid ISO
  for UEFI, with Secure Boot, and for a BIOS, built without root by
  mmdebstrap, sqfstar and xorriso from trixie and Kidux's archive,
  reproducible, and named by the kidux-base it carries and its suite's
  date. Its live system is a Kidux machine with Calamares in place of the
  sign-in screen, `kidux-installer`, which copies it to the disk and takes
  itself off, so that an installed Kidux is the Kidux the guide installs on
  Debian, partitions and first start alike. Not on GitHub: the owner does
  not want the project to depend on it (D39), its releases take no file
  over two gigabytes, and its runners keep its hours (D114); the image is
  served by the project's hosting at `iso.kidux.org`, beside the archive,
  under its own name and under one without a version that the website
  links to, its sums signed with the archive's key. The install test
  installs it under UEFI and a BIOS, starts it under Secure Boot, and runs
  the first-start tests on it; the disk it leaves becomes the images to
  try Kidux in an emulator, with a demonstration family, for QEMU, UTM and
  VirtualBox. The user documents and the website offer the installer and
  the trial as the two ways in, the installation on Debian after them
  (image.md).
- **D117 — Test machines and trial images say who they are to the
  archive's usage count.** Decided 2026-10-19 by the owner. A test
  machine's address changes, and the identifiers its first starts made
  had to be listed by hand; every test machine now sends a fixed one,
  sixteen zeros and its number (1 and 2 the session machines, 3 the
  acceptance machine, 4 the install test's, 5 ci/vm/try.sh's), which the
  usage page leaves out at sight. Every copy of a trial image shares the
  image's identifier, sixteen f's and its number (1 Spanish, 2 English),
  listed in `ci/usage-trial-ids.txt`, and the page counts trials apart
  from the families' machines, one for each address (image.md, section 7).
- **D118 — The trial images start in VirtualBox and UTM as they are, and
  Kidux's compositors draw in software where the card cannot draw for
  them.** Decided 2026-10-19 by the owner, after the images were tried in
  VirtualBox on the release machine and in UTM on a Mac. The OVA carries
  VirtualBox's own description of the machine (`vbox:Machine`, which
  other importers skip) for what OVF cannot say: UEFI, the VMSVGA card,
  a USB tablet for the pointer, HD Audio; so the page on trying Kidux
  asks for no setting. VMSVGA without 3D has a render node and no working
  OpenGL ES, which wlroots neither draws with nor falls back from, so cage
  and labwc stopped at once and the screen stayed black. Both now start
  through `/usr/lib/kidux/compositor`, which starts a compositor once
  more with `WLR_RENDERER=pixman` when it stops within five seconds with
  no renderer named, and leaves the first start on any other card; a
  wrapper rather than a setting, since greetd gives the greeter a clean
  environment (session.md, section 2; image.md, section 5). On a Mac with
  an Apple processor UTM emulates the PC, and the page asks for four
  cores, since two are too slow to use.

- **D119 — A closed lid and a computer left alone suspend, never
  hibernate, and a child's session locks before any sleep.** Decided
  2026-10-31 by the owner. Closing the lid suspends at once, on battery
  as on mains power, and does nothing while docked or with another
  screen connected; a computer still left alone `idle_sleep_minutes`
  (twenty) after its last touch suspends too, as the second stage after
  D67's screen off, unless an idle inhibitor is held. The adult chooses
  each on the panel's *Suspending the computer* page: suspend or nothing
  for the lid, suspend or the screen off only for idleness. logind keeps
  ignoring the lid: the daemon suspends on the lid's close, an event it
  reads with the power button's, after locking a child's session and only
  if the switch still reads closed, since the same MacBook's switch read
  closed with the lid open after a failed resume, and logind, which acts
  on the state, suspended at every start. A delay inhibitor on sleep locks
  every child's session before any sleep, whatever caused it, so a closed
  lid is never a way out of a time limit. The second stage goes through the daemon
  (`System1.SleepWhenIdle`), not logind's `IdleAction`, which needs an
  `IdleHint` from every session, and not the screens themselves, which
  polkit does not let suspend.

  Hibernation was designed first, suspend and then hibernate a minute
  later, and dropped the same day after the owner's MacBook (two
  graphics cards, Intel and AMD) hibernated and then hung at every start
  trying to restore, until `noresume` was typed at GRUB's prompt. Whether
  restoring works cannot be known before trying it, logind's
  `CanHibernate` says yes all the same, and a family cannot be asked to
  edit a boot line. So Kidux never hibernates: kidux-session's
  `sleep.conf.d` sets `AllowHibernation`, `AllowSuspendThenHibernate`
  and `AllowHybridSleep` to no, and Kidux never changes swap, the
  kernel's command line or the initramfs (power.md).
