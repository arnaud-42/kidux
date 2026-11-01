# Where everything is

## 1. The repository

```
README.md, README.es.md      the product, presented, in both languages
LICENSE                      GNU General Public License, version 3 (D78, D110)
CONTRIBUTING.md              what a contributor agrees to, so the licence stays possible
site/                        the website: its page, its words in each language, its style (website.md)
CLAUDE.md                    the project's conventions
docs/en/, docs/es/           the user guide, mirrored in both languages
docs/images/en/, es/         the screenshots the user guide and the README show,
                             one folder per language
docs/dev/                    developer documentation, English only
branding/                    the logo, the mascot, the style guide
packages/<name>/             one Debian source package each, debian/ inside
ci/                          every script that builds, publishes or promotes
ci/archive/conf/             the apt archive's configuration, with the key each suite is signed with
ci/archive/development-key.pgp   the public part of the key testing is signed with
ci/vm/                       a throwaway Kidux machine to use over VNC
ci/upstream/                 the build scripts of programs that are not in Debian (D68)
ci/usage-site/               the page of the machines that follow the archive, on the hosting
.github/workflows/           continuous integration (packaging.md)
tests/                       every test, one file each, by kind (tests/README.md)
tests/lib/                   what runs them: the VM runners, their seeds, the
                             screenshot comparison
image/                       the installable image's build configuration
                             (phase 2; not in the repository yet)
build/                       everything the scripts produce; not in git
```

The packages, in dependency order; `ci/build-all.sh` builds the first two
in this order and the rest at once:

| Package | What it is |
|---|---|
| `kidux-archive-keyring` | The archive's signing key, and `kidux-apt-source`, the apt source that follows it |
| `kidux-common` | `python3-kidux`: paths, state files, i18n, the D-Bus client, the shared words, the avatars |
| `kidux-daemon` | The one privileged process |
| `kidux-greeter` | The sign-in screen, the lock screen, the first-run wizard and the adult panel |
| `kidux-launcher` | The child's screen |
| `kidux-module-hello` | The reference learning module, and the one to copy for a new one (modules.md, section 5); each module's content is in its package, under `content/<lang>/` |
| `kidux-webapps` | The server of web applications on 127.0.0.1:8123, `kidux-webapp` that opens one in Chromium, and Chromium's managed policy |
| `kidux-module-hello-web` | The reference web application: hello's page as a web page, and the one to copy for a module made of web pages |
| `kidux-module-gcompris` | GCompris as a learning module: its manifest, its tile, its words and its starter, and GCompris itself, `qt6-wayland` with it, from Debian |
| `kidux-session` | greetd, cage for the trusted screens, labwc and XWayland for the child's session, the lock screen's terminal, the boot splash, every door closed |
| `kidux-base` | The metapackage that brings a machine the whole of Kidux |

## 2. An installed machine

What Kidux puts where, and who may touch it.

### The family's state: `/home/.kidux/`

Owned by root, group `kidux-admin`, mode 0750. Written only by the daemon;
readable by administrators; closed to every child. On the data partition,
so a reinstall that keeps `/home` keeps all of it.

```
/home/.kidux/
  config.toml                 default language and keyboard, display scale,
                              the hour the day resets, whether setup is done
  adults.toml                 the adult password's hash; the GRUB recovery
                              password and its hash
  state/audit.log             every privileged action and every attempt at
                              a password, with its outcome; append-only
  children/<user>/
    profile.toml              display name, language, keyboard, age, avatar
    access.toml               mode, daily minutes, the bank of granted time
    usage.toml                the day, seconds used today, session state
    modules.toml              which modules are enabled for this child
```

A child's own work is in `/home/<user>/`, which Kidux never touches.

### Programs

```
/usr/libexec/kidux-daemon            the daemon
/usr/libexec/kidux-firstboot         runs once per machine, before the daemon
/usr/libexec/kidux-update            one update job, in a unit of its own
/usr/libexec/kidux-greeter           the sign-in and lock screens
/usr/libexec/kidux-launcher          the child's screen
/usr/libexec/kidux-module-hello      the reference module's program
/usr/libexec/kidux-module-gcompris   GCompris's starter, which answers its first questions
/usr/libexec/kidux-webapps           the web applications' server
/usr/libexec/kidux-webapp            opens one web application in Chromium
/usr/libexec/kidux-session           a child's session
/usr/lib/kidux/greeter-session       runs cage for the trusted screens
/usr/lib/kidux/session-inner         inside the compositor: scale, idle, then the program
/usr/lib/kidux/kidux-idle            a screen left alone: the lock, the screen off
```

Nothing a person types is on the `PATH`.

`kidux-update.service` exists only while an update job runs: the daemon
starts it through systemd, and its status file is
`/run/kidux/update.status`, in the daemon's runtime directory.

### Configuration our packages install

```
/usr/share/kidux/greetd.toml                        greetd, pointed at by
/usr/lib/systemd/system/greetd.service.d/kidux.conf   this drop-in
/usr/share/kidux/labwc/{kiosk,desk}/                the child's compositor's configurations
/usr/lib/systemd/system/kidux-daemon.service
/usr/lib/systemd/system/kidux-firstboot.service
/usr/lib/systemd/system/kidux-locker@.service       the lock screen, per child
/usr/lib/systemd/system/getty@.service.d/kidux.conf no text logins
/usr/lib/systemd/logind.conf.d/kidux.conf           no spare terminals, no power
                                                    key, no lid, kill on logout,
                                                    the delay before a sleep
/usr/lib/systemd/sleep.conf.d/kidux.conf            no hibernation
/usr/lib/sysctl.d/60-kidux.conf                     no SysRq, no ptrace
/etc/ssh/sshd_config.d/kidux.conf                   no SSH for children
/etc/pam.d/kidux                                    the daemon checking a child's password
/etc/pam.d/kidux-locker                             the lock screen's own session
/etc/systemd/system/ctrl-alt-del.target             a symlink to /dev/null
/usr/share/polkit-1/actions/org.kidux.daemon.policy
/usr/share/polkit-1/rules.d/50-kidux.rules          who may call the daemon
/usr/share/polkit-1/rules.d/40-kidux-children.rules what a child may not ask logind
/usr/share/dbus-1/system.d/org.kidux.Daemon1.conf
/usr/share/dbus-1/system-services/org.kidux.Daemon1.service
/usr/share/dbus-1/interfaces/org.kidux.Daemon1.xml  the API, as the daemon answers it
/etc/default/grub.d/90-kidux.cfg                    the Kidux entry boots by default
/etc/grub.d/09_kidux                                that entry, and the password
/etc/apt/sources.list.d/kidux.sources               the archive
/etc/apt/apt.conf.d/60kidux-user-agent              every fetch says it is a Kidux machine's
/etc/apt/apt.conf.d/61kidux-statistics              and which one, while an adult shares statistics
/usr/share/keyrings/kidux-archive-keyring.pgp       its key
```

Everything under `/usr/lib` and `/usr/share` is the package's and is
replaced on upgrade. Everything under `/etc` is a configuration file and is
kept if edited, which is why the packages put as little there as Debian
allows.

### Shipped data

```
/usr/share/kidux/avatars/<name>.svg     the pictures children choose from
/usr/share/kidux/branding/logo.svg      Kidux's logo, and its mascot, for the screens
/usr/share/kidux/branding/mascot.svg
/usr/share/plymouth/themes/kidux/       the boot splash
/usr/share/kidux/locales                the locales kidux-base generates
/usr/share/locale/<lang>/LC_MESSAGES/kidux.mo   the translations, one domain
/usr/share/kidux/modules/<id>/module.toml       each learning module's manifest
```

### Identities

- `kidux-admin`, a system group: administrators. Created at package install;
  every member of `sudo` is added at first boot.
- `kidux-children`, a system group: the children. The daemon adds each child
  it creates, and nothing else is ever in it.
- `_greetd`, the user the trusted screens run as, from the `greetd` package.
- No user name is fixed. The administrator is whoever installed the machine
  (D18).
