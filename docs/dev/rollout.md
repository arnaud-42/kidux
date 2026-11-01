# Rolling Kidux out on the development MacBook

Plan step 9.11, done by the owner at the keyboard, never unattended. The
MacBook is both the development server and the family's machine
(install-debian-macbookpro-2015.md), so the rollout has one rule above the
others: **SSH and the owner's account keep working throughout**, and every
step has a way back.

`<you>` below is the owner's account name, which the repository never
spells (D18).

## 1. Before starting

- Steps 9.6b and 9.7 are green in the `testing` suite: without the wizard
  there is no way to set an adult password without a terminal, and without
  the launcher a child's session is an empty screen.
- A second way in: SSH from another machine, tested, and the MacBook's own
  keyboard.
- A backup of what the rollout touches:

  ```bash
  sudo tar -C / -czf ~/before-kidux.tar.gz etc/default/grub \
      etc/systemd etc/ssh boot/grub/grub.cfg
  dpkg --get-selections > ~/before-kidux.selections
  ```
- No test run going: `pgrep -a qemu` prints nothing. The reboot in section 4
  would cut it, and a build or a VM makes the first minutes on Kidux slow.
- The reboot ends every SSH connection, Claude Code's included. Afterwards,
  connect again and `claude --continue` picks the conversation up.

## 2. What only this machine needs

`kidux-session` sets `KillUserProcesses=yes`: when someone logs out, logind
ends everything they left running. On a family machine that is the point. On
this one it would end the owner's `tmux` and the editor's server every time
an SSH connection drops. logind can exclude users only by name, so the
exclusion is a local file, not a packaged one:

```bash
sudo mkdir -p /etc/systemd/logind.conf.d
printf '[Login]\nKillExcludeUsers=root <you>\n' \
  | sudo tee /etc/systemd/logind.conf.d/zz-development-machine.conf
```

It takes effect when logind restarts, which the reboot in section 4 does.

The lid watcher of the install guide, section 7, `kidux-lid-watch` under
`/usr/local`, goes before Kidux is installed: the launcher and the trusted
screens power the panel off themselves while the lid is closed and leave the
brightness alone (D61), and the watcher, which sets it to zero, would fight
them.

```bash
sudo systemctl disable --now kidux-lid-watch
sudo rm /etc/systemd/system/kidux-lid-watch.service /usr/local/sbin/kidux-lid-watch
```

The install guide's `server.conf` for logind and the masked sleep targets
stay while the machine serves: they keep it awake with its lid closed,
over the lid setting of the panel's *Suspending the computer* page
(power.md). A machine that is only a child's removes both:

```bash
sudo rm /etc/systemd/logind.conf.d/server.conf
sudo systemctl unmask sleep.target suspend.target hibernate.target hybrid-sleep.target
```

## 3. Installing

The machine is also the archive, so beside the public archive's stable suite,
which the shipped source names, it follows its own `testing` suite, as a
second source with the key testing is signed with (packaging.md, "Signing"):

```bash
curl -fsSLO http://kidux.local/apt/bootstrap/testing/kidux-archive-keyring.deb
curl -fsSLO http://kidux.local/apt/bootstrap/testing/kidux-apt-source.deb
sudo apt install ./kidux-archive-keyring.deb ./kidux-apt-source.deb
sudo curl -fsS -o /usr/share/keyrings/kidux-development.pgp \
    http://kidux.local/apt/extra-key.pgp
printf '%s\n' 'Types: deb' 'URIs: http://kidux.local/apt' 'Suites: testing' \
    'Components: main' 'Signed-By: /usr/share/keyrings/kidux-development.pgp' \
    | sudo tee /etc/apt/sources.list.d/kidux-development.sources
sudo apt update
sudo apt install kidux-base
```

apt takes the newest version either source has: a development build from
testing, then the release that replaces it, from testing first and from
stable once it is published. The shipped source and keyring are left as
the packages install them, so an upgrade of either asks nothing.

Then, before rebooting:

- `/boot/grub/grub.cfg` has `menuentry 'Kidux' --unrestricted` booting the
  newest generic kernel, and the other entries are behind a password.
- The GRUB recovery password is readable and written down somewhere safe:

  ```bash
  sudo grep '^grub_password ' /home/.kidux/adults.toml
  ```

  It is what boots Debian's own entries from the menu (session.md,
  section 7) if the Kidux entry ever fails.
- `id <you>` shows `kidux-admin`: first boot adds every member of `sudo`
  (daemon.md, section 12).

## 4. First boot into Kidux

```bash
sudo reboot
```

The machine shows Kidux's logo, then the first-run wizard, and SSH keeps
working. The wizard is drawn at scale 1 on a 2880x1800 panel, so it is small;
that is expected. Through the wizard: Spanish, the Spanish keyboard, the adult
password, the first child. The display scale is automatic, 1.75 on this
panel, which draws every screen at 1645x1028, roomy (D56); *Adult*, the
adult password, and the panel's *System* page choose another, 2 or 2.25 to
see everything larger, 1.5 for more room still. It applies the next time
the screen starts, which *Turn off* and a restart, or signing a child in,
brings about. A machine set up before the scale was automatic keeps the 1
it was given until *Automatic (175 %)*, as the list says it there, is
chosen.

If the screen stays black, SSH in and follow section 6.

## 5. What only real hardware can show

Each of these is something no VM proves (plan step 9.11):

| Check | How | Expected |
|---|---|---|
| The Retina scale | sign in as the child | the launcher at scale 2, sharp text |
| Locking on `radeon` | the power button, then *Continue* | the lock screen, then the same session; `journalctl -u kidux-daemon` shows no "lock failed" (D28) |
| Locking twenty times | lock and continue repeatedly | no black screen, no lost keyboard |
| A session left alone | five minutes without a touch, signed in as a child | the lock screen; ten minutes, the screen off, back with a key |
| The lid locks | close it with a child signed in, and open it | the lock screen, and the child continues with their password |
| The lid | close it on the sign-in screen, and open it | the panel goes dark and comes back, the machine stays up and SSH answers |
| Turning off | *Turn off* on the lock screen | the machine powers off |
| An update | `sudo apt upgrade` over SSH with a child signed in | the child's session carries on |

### Taking a change

The machine follows its own archive's `testing` suite, so it is never
installed again: every package published there, by a step's battery or by
`tests/run vm push` while a change is being tried (tests/README.md, "The
quick loop"), reaches it with

```bash
sudo apt update && sudo apt upgrade
```

or with *Install* under *Updates* on the panel's System page, which refuses
while a child is signed in. What each package needs afterwards:

| Package | Takes the change |
|---|---|
| `kidux-daemon`, `kidux-webapps` | at once: the upgrade restarts its service |
| `kidux-greeter` | when the sign-in screen next starts: *Turn off* and on, or `sudo systemctl restart greetd` with nobody signed in |
| `kidux-common` | both of the above |
| `kidux-launcher` | at a child's next sign-in |
| a module | the next time a child opens it |
| `kidux-session` | at the next restart of the machine |

A development build's version ends `~dev.<time>`, which sorts before the
version itself; a step's battery publishes development builds too, which
the owner tries here, and the release, which the owner's yes starts,
replaces them with the versions themselves at the next upgrade (D77,
D93).

### Chromium on this machine's graphics

A web module (hello-web), or ScratchJr, whose Electron is Chromium, may be
drawn as noise or old pictures on the `radeon` graphics, cleared where the
pointer passes, or frozen until it moves: Chromium's own way of
handing its pictures to the compositor going wrong on this hardware, which no test
machine has, since theirs draw in software (D51). The cure is found here,
in the panel's System page, *Advanced*, *Chromium's options*, one option at
a time, in this order, each saved, then hello-web opened as a child and
looked at as it opens, after the lock and *Continue*, and after its link
and back:

1. `--disable-gpu-compositing`: Chromium puts the page together itself and
   hands the compositor finished pictures, as on the test machines. The likeliest
   cure; WebGL is somewhat slower.
2. `--disable-gpu`: nothing on the graphics card at all. Slower, and the
   proof that the card is the cause.
3. `--use-gl=angle` and `--use-angle=gl`, two lines: another way of drawing
   inside Chromium, for when the fault is there rather than in the handing
   over.
4. `--disable-features=WaylandLinuxDrmSyncobj`: the newer way Chromium and
   the compositor agree when a picture is finished, turned off.

The first that draws cleanly is the answer; whether modules are then any
slower is part of it. `kidux-webapp --print hello-web`, run as the child
(`sudo -u <child> /usr/libexec/kidux-webapp --print hello-web`), shows the
command line with the options at its end. If none of the four cures it,
Chromium says what went wrong in the child's journal:
`sudo journalctl _UID=$(id -u <child>) | grep -i -e gpu -e viz`.

## 6. The way back

- **From SSH:** `sudo apt purge kidux-session && sudo reboot` gives the
  machine back as plain Debian; `tests/run session` proves this path on
  every run. The children's accounts and `/home/.kidux` stay, ready for the
  next attempt.
- **Without SSH:** at the boot menu, *Esc*, then the user name `kidux` and
  the recovery password, and one of Debian's own entries.
- **The screen stays black on `radeon`:** the install guide, section 6,
  `radeon.dpm=0`.
