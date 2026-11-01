"""kidux-daemon: the one privileged process in Kidux.

The design is docs/dev/daemon.md in the source repository. `kidux` from
kidux-common is the library every component shares; `kiduxd` is the daemon's
own code and nothing else imports it.
"""

VERSION = "0.3.39"
