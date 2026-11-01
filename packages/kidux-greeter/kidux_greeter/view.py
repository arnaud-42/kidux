"""GTK 4 and libadwaita: draws what `flow.py` decides, and reports what was tapped.

Nothing here decides anything. Each screen `flow.py` can answer with has one
`_draw_<name>` method below, and each button calls a method of the flow by
name. The flow's answer is drawn in its own language: the view keeps one
catalogue per screen, so the sign-in screen can change language between one
tap and the next.

How it looks, typeface, sizes, colours and layout, is greeter.md section 8,
settled with the owner, and the adult's forms are D37; it is kept in `CSS`
and the constants below.
"""

import logging
import re
import threading

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk, Pango  # noqa: E402

from kidux import avatars, i18n, paths, scroll, vocabulary  # noqa: E402
from kidux import screen as kidux_screen  # noqa: E402
from kidux.corner import CSS as CORNER_CSS, Corner  # noqa: E402

from . import words  # noqa: E402
from .flow import FINAL, GRANT_CHOICES, Screen  # noqa: E402
from .screen import only_progress_differs  # noqa: E402
from . import laptop  # noqa: E402
from .panel import (  # noqa: E402
    IDLE_LOCK_MINUTES, IDLE_LOCK_RANGE, IDLE_SLEEP_MINUTES, IDLE_SLEEP_RANGE, MODES,
    SCREEN_OFF_MINUTES, SCREEN_OFF_RANGE, parse_access, size_label,
)

log = logging.getLogger("kidux.greeter")

#: A child's screen left untouched this long goes back to where it started:
#: everyone's pictures, or the lock screen's first page.
IDLE_SECONDS = 60
#: The adult panel left alone this long closes and locks, when its page does
#: not say how long (D67): a panel left open in a living room is open to
#: whoever walks past. Each page says the minutes the adult chose.
PANEL_IDLE_SECONDS = 300
#: How often the waiting screen asks the daemon again.
RETRY_SECONDS = 5
#: A screen that should be the last one — the session starting, the machine
#: turning off — and is still up after this long did not end as it should.
#: Rather than leave a child looking at a spinner, start over.
STUCK_SECONDS = 30

AVATAR_SIZE = 128
#: How long a toast stays, in seconds.
TOAST_SECONDS = 5
#: Kidux's logo: the mascot and the wordmark side by side, 5:2.
LOGO = str(paths.LOGO)
#: How tall the logo is where it welcomes someone, and in the bottom middle of
#: every other screen (greeter.md section 8, item 10).
LOGO_LARGE, LOGO_SMALL = 64, 32
#: The screens that show it large, and so not again in the corner.
WELCOMES = frozenset({"wiz_language", "choose"})
#: The panel's pages of settings, which grow as modules and machines bring
#: more: they scroll where they do not fit, like every screen, and are not
#: meant to fit 1280x800 whole (D92).
GROWS = frozenset({"panel_advanced", "panel_module_settings"})
#: How far beyond the fold a control brought into view is shown, so that
#: its focus ring and the shade at the edge do not hide it.
FOCUS_MARGIN = 24
#: How long a page drawn again may take to be laid out before the place
#: kept is taken as it is (keep_place), in milliseconds.
SETTLE_MS = 200
AVATAR_SIZE_SMALL = 96

CSS = """
window.kidux {
  background-color: #fff6e9;
  color: #3b2f2a;
  font-family: "Andika", sans-serif;
  font-size: 20px;
}
.kidux-title { font-size: 30px; font-weight: bold; }
.kidux-clock { font-size: 44px; font-weight: bold; color: #7a6a60; }
.kidux-name { font-size: 24px; font-weight: bold; }
.kidux-toast { background-color: #24313f; color: #fdf6f0; border-radius: 16px;
  padding: 10px 22px; font-size: 18px; }
.kidux-notice {
  font-size: 20px;
  background-color: #ffe2c6;
  color: #7a3310;
  border-radius: 14px;
  padding: 10px 20px;
}
window.kidux button {
  min-height: 64px;
  min-width: 64px;
  border-radius: 18px;
  padding: 0 24px;
  font-size: 20px;
}
window.kidux button.kidux-child {
  padding: 16px;
  border-radius: 24px;
}
window.kidux button.kidux-small {
  min-height: 52px;
  font-size: 18px;
  padding: 0 16px;
}
window.kidux button.kidux-quiet {
  background-color: transparent;
  color: #7a6a60;
  font-size: 18px;
}
window.kidux entry, window.kidux passwordentry {
  min-height: 60px;
  min-width: 440px;
  font-size: 24px;
  border-radius: 14px;
}
window.kidux button.kidux-selected {
  box-shadow: inset 0 0 0 3px #3b2f2a;
}
/* The adult's screens (D37): the same colours and typeface, smaller. */
window.kidux .kidux-adult {
  font-size: 16px;
}
window.kidux .kidux-adult button {
  min-height: 40px;
  min-width: 40px;
  border-radius: 10px;
  padding: 0 14px;
  font-size: 16px;
}
window.kidux .kidux-adult entry, window.kidux .kidux-adult passwordentry {
  min-height: 38px;
  min-width: 320px;
  font-size: 16px;
  border-radius: 8px;
}
window.kidux .kidux-adult .kidux-title { font-size: 24px; }
window.kidux .kidux-adult .kidux-notice { font-size: 16px; padding: 6px 14px; }
window.kidux .kidux-field-label { color: #7a6a60; }
window.kidux .kidux-module-name { font-weight: bold; }
window.kidux .kidux-module-suits { font-size: smaller; }
window.kidux .kidux-version { font-size: 13px; color: #7a6a60; }
window.kidux .kidux-option { font-family: monospace; font-size: 15px; }
window.kidux .kidux-field-error { color: #b3261e; font-size: 14px; }
window.kidux popover { font-size: 16px; }
"""

#: The picture on each button that has one. A child who cannot read yet goes
#: by the picture.
ICONS = {
    vocabulary.ADULT: "system-users-symbolic",
    vocabulary.TURN_OFF: "system-shutdown-symbolic",
    vocabulary.RESTART: "system-reboot-symbolic",
    vocabulary.BACK: "go-previous-symbolic",
    vocabulary.CANCEL: "window-close-symbolic",
    vocabulary.TRY_AGAIN: "view-refresh-symbolic",
    vocabulary.CONTINUE: "go-next-symbolic",
    vocabulary.SIGN_IN: "go-next-symbolic",
    vocabulary.LOG_OUT: "system-log-out-symbolic",
    vocabulary.UNLOCK_TO_SAVE: "document-save-symbolic",
    vocabulary.ASK_ADULT_FOR_TIME: "system-users-symbolic",
}

_FILL = re.compile(r'<circle[^>]*\bfill="(#[0-9a-fA-F]{6})"')


def avatar_colours() -> dict[str, str]:
    """Each avatar's background colour, read from its own circle.

    Each child's button is tinted with it, so the picture and the colour say
    the same thing.
    """
    colours = {}
    for name in avatars.available():
        try:
            match = _FILL.search(avatars.path_for(name).read_text(encoding="utf-8"))
        except OSError:
            continue
        if match:
            colours[name] = match.group(1)
    return colours


def install_style(display: Gdk.Display) -> None:
    tints = "".join(
        f"window.kidux button.avatar-{name} {{ background-color: {colour}; }}\n"
        for name, colour in avatar_colours().items()
    )
    provider = Gtk.CssProvider()
    provider.load_from_string(CSS + CORNER_CSS + scroll.CSS + tints)
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def drawing(path: str, width: int, height: int) -> Gtk.Widget:
    """An SVG drawn at exactly width by height, sharp at any display scale.

    Drawn with librsvg into the area GTK gives it, rather than loaded as a
    picture: a picture grows to the size its file says, whatever is asked."""
    try:
        gi.require_version("Rsvg", "2.0")
        from gi.repository import Rsvg
        handle = Rsvg.Handle.new_from_file(path)
    except (ValueError, ImportError, GLib.Error):
        return Gtk.Box()
    area = Gtk.DrawingArea(content_width=width, content_height=height,
                           halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)

    def draw(_area, cairo, w, h):
        viewport = Rsvg.Rectangle()
        viewport.x, viewport.y, viewport.width, viewport.height = 0, 0, w, h
        try:
            handle.render_document(cairo, viewport)
        except Exception:  # noqa: BLE001 — a missing picture is not worth a crash
            log.exception("could not draw %s", path)

    area.set_draw_func(draw)
    return area


def keyboard_grid(grid: Gtk.FlowBox) -> Gtk.FlowBox:
    """A grid of buttons the arrow keys work in.

    The arrows move the focus from cell to cell, and a cell is not its
    button: Enter on a cell activates the cell. Activating the cell presses
    the button in it, so the arrows and Enter do what a tap does."""
    grid.connect("child-activated", lambda _grid, cell: cell.get_child().activate())
    return grid


def top_of(room) -> float:
    """Where `room` starts on its window, in pixels from the top; 0 before
    it is laid out."""
    root = room.get_root()
    found, bounds = room.compute_bounds(root) if root is not None else (False, None)
    return bounds.get_y() if found else 0.0


def keep_place(old, new, then=None) -> None:
    """Scroll `new` so that what `old` showed stays where it was on the
    screen, as soon as it has the room to: a page drawn again in place of
    itself stays put, even when a notice above the room has moved the room
    down, or its going has moved it up. `then` is called once it is in
    place, or at once when there was no place to keep.

    The adjustment says it has the room while the window is being laid
    out, and a value set then moves the scrollbar but not what the room
    shows, which GTK does not lay out again in the middle of laying it out:
    so the value is set just after, when GLib is idle."""
    adjustment = new.get_vadjustment()

    def place(wanted: float | None) -> bool:
        if wanted is not None:
            adjustment.set_value(max(adjustment.get_lower(), wanted))
        if then is not None:
            then()
        return False

    value = old.get_vadjustment().get_value()
    if value <= 0:
        GLib.idle_add(place, None)
        return
    was = top_of(old)
    handler = 0
    settled = False

    def wanted() -> float:
        return value + (top_of(new) - was)

    def settle(at: float) -> bool:
        nonlocal handler, settled
        if not settled:
            settled = True
            if handler:
                adjustment.disconnect(handler)
                handler = 0
            GLib.idle_add(place, at)
        return False

    def changed(adjustment) -> None:
        if adjustment.get_upper() - adjustment.get_page_size() >= wanted():
            settle(wanted())

    # A page drawn shorter than the place kept, a row gone from its end,
    # never has the room: once laid out, it takes the place it has, since
    # set_value clamps, instead of staying at the top.
    handler = adjustment.connect("changed", changed)
    GLib.timeout_add(SETTLE_MS, lambda: settle(wanted()))


def spinner_small() -> Gtk.Widget:
    widget = spinner()
    widget.set_size_request(24, 24)
    return widget


def spinner() -> Gtk.Widget:
    if hasattr(Adw, "Spinner"):
        widget = Adw.Spinner()
    else:
        widget = Gtk.Spinner(spinning=True)
    widget.set_size_request(72, 72)
    return widget


class View:
    """One window, redrawn whole for every screen."""

    def __init__(self, window: Gtk.Window, flow, *, lock: bool, on_exit) -> None:
        self._window = window
        self._flow = flow
        self._lock = lock
        self._on_exit = on_exit
        self._busy = False
        self._screen: Screen | None = None
        self._translations = i18n.translations("")
        self._timers: list[int] = []
        self._idle_timer = 0
        self._clock: Gtk.Label | None = None
        self._focus: Gtk.Widget | None = None
        self._children_pending = False
        #: What Back does on the screen on display, for the Escape key.
        self._back_action = None
        self._refocus: Gtk.Widget | None = None
        #: Whether what is out is a poll, and the tap that waits for it.
        self._poll_out = False
        self._pending: tuple | None = None
        #: Screens already reported as too tall or too wide, each way logged once.
        self._overflowed: set[tuple[str, str]] = set()
        #: The Modules page's scrolling room as last drawn, while it is the
        #: page shown, so that drawing it again keeps its place.
        self._modules_room = None
        #: What follows a running job's progress on the page on display, each
        #: given the job's state, so that the page is not drawn again for it.
        self._progress_followers: list = []
        #: A word to say in passing once the page is on display: how a job
        #: went (`_toast`).
        self._pending_toast: str | None = None
        self._toasts: Gtk.Overlay | None = None
        #: The module switch last flipped, (username, module id), which keeps
        #: the focus when the page is drawn again.
        self._flipped: tuple[str, str] | None = None
        #: The module whose Remove last asked, whose Remove has the focus
        #: again when the question is cancelled.
        self._asked_about: str | None = None
        #: Whether that Remove has the focus again on the page being drawn.
        self._focus_returned = False
        #: The corner (kidux.corner), top right over every screen, made
        #: again only when the language changes, and the language it has.
        self._corner: Corner | None = None
        self._corner_language: str | None = None

        window.add_css_class("kidux")
        keys, clicks = Gtk.EventControllerKey(), Gtk.GestureClick()
        keys.connect("key-pressed", self._key)
        clicks.connect("pressed", lambda *_args: self._touched())
        for controller in (keys, clicks):
            controller.set_propagation_phase(Gtk.PropagationPhase.CAPTURE)
            window.add_controller(controller)
        GLib.timeout_add_seconds(15, self._tick)

    # --- asking the flow -------------------------------------------------------

    def _target(self, owner: str | None):
        """Who answers: the state machine that owns the screen on display, or,
        with owner "", the sign-in or lock screen the program started as."""
        if owner is None:
            owner = self._screen.owner if self._screen is not None else ""
        return (getattr(self._flow, owner, None) if owner else None) or self._flow

    def run(self, method: str, *args, owner: str | None = None, poll: bool = False) -> None:
        """Ask the flow, off the main loop.

        greetd takes a few seconds to turn down a wrong password (PAM's own
        delay), and the screen must not freeze while it does. One question at
        a time: while one is out, the screen is insensitive and further taps
        are ignored. A `poll`, a page asking how a job goes, is no question
        of the adult's: the screen stays as it is while it is out, a tap
        that comes meanwhile is asked once it is answered, and a poll that
        comes while a question is out is left to the question's answer,
        which asks again.
        """
        if self._busy:
            if not poll and self._poll_out and self._pending is None:
                self._pending = (method, args, owner)
            return
        target = self._target(owner)
        self._busy = True
        self._poll_out = poll
        if not poll:
            # Making the screen insensitive takes the keyboard focus away, and
            # making it sensitive again does not give it back: remember it.
            self._refocus = self._window.get_focus()
            content = self._window.get_content()
            if content is not None:
                content.set_sensitive(False)

        def work():
            try:
                result = getattr(target, method)(*args)
            except Exception:  # noqa: BLE001 — anything at all, see main.py
                log.exception("the screen's %s failed", method)
                GLib.idle_add(self._answered, None, True)
                return
            GLib.idle_add(self._answered, result, False)

        threading.Thread(target=work, name=f"flow-{method}", daemon=True).start()

    def _answered(self, screen: Screen | None, failed: bool) -> bool:
        self._busy = False
        was_poll, self._poll_out = self._poll_out, False
        if failed:
            self.show_error()
        elif screen is not None:
            self.show(screen)
        # The page on display is sensitive again whether it was drawn afresh
        # or kept, as a poll keeps it.
        content = self._window.get_content()
        if content is not None and not content.get_sensitive():
            content.set_sensitive(True)
        if screen is None and not failed and not was_poll and self._refocus is not None:
            self._refocus.grab_focus()
        if getattr(self._flow, "exit_requested", False):
            self._on_exit()
        elif self._children_pending and not failed:
            self._children_pending = False
            self.children_changed()
        pending, self._pending = self._pending, None
        if pending is not None and not failed:
            self.run(pending[0], *pending[1], owner=pending[2])
        return GLib.SOURCE_REMOVE

    def attention(self) -> None:
        """The power button, with nobody signed in."""
        if not self._lock and not getattr(self._flow, "session_started", False):
            self.run("attention", owner="")

    def children_changed(self) -> None:
        if self._lock:
            return
        if self._busy or self._screen is None:
            # Asked again once the screen has its answer: a change is never lost.
            self._children_pending = True
            return
        self.run("children_changed", self._screen.name, owner="")

    # --- drawing ---------------------------------------------------------------

    def _(self, message: str) -> str:
        return self._translations.gettext(message)

    def show(self, screen: Screen) -> None:
        try:
            self._show(screen)
        except Exception:  # noqa: BLE001
            log.exception("could not draw the %s screen", screen.name)
            self.show_error()

    def _show(self, screen: Screen) -> None:
        if self._screen is not None and only_progress_differs(self._screen, screen):
            # A job's progress moved on and nothing else: the page keeps its
            # place, its bars and words follow, and it asks again.
            self._screen = screen
            update = screen.data.get("update") or {}
            for follow_progress in self._progress_followers:
                follow_progress(update)
            self._cancel_timers()
            self._schedule(screen)
            return
        log.info("showing %s", screen.name)
        if screen.name != "panel_modules":
            self._modules_room = None
            self._asked_about = None
        self._screen = screen
        self._progress_followers = []
        self._translations = i18n.translations(screen.language)
        self._cancel_timers()
        self._clock = None
        self._focus = None
        self._back_action = None

        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16)
        for side in ("top", "bottom", "start", "end"):
            getattr(page, f"set_margin_{side}")(32)
        middle = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                         valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER, vexpand=True)
        bottom = Gtk.CenterBox()

        getattr(self, f"_draw_{screen.name}")(screen, page, middle, bottom)
        # Every screen says what computer this is: the welcomes large, every
        # other screen small, in the bottom middle between the corner buttons.
        if screen.name not in WELCOMES and bottom.get_center_widget() is None:
            bottom.set_center_widget(self._logo(LOGO_SMALL))
        # Which Kidux this is, small, under the logo of the sign-in and lock
        # screens: what an adult reads to know an update arrived.
        if screen.name in ("choose", "locked") and screen.data.get("kidux_version"):
            said = Gtk.Label(label=self._(words.KIDUX_VERSION).format(
                version=screen.data["kidux_version"]))
            said.add_css_class("kidux-version")
            logo = bottom.get_center_widget()
            if logo is None:
                bottom.set_center_widget(said)
            else:
                bottom.set_center_widget(None)
                column = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2,
                                 halign=Gtk.Align.CENTER)
                column.append(logo)
                column.append(said)
                bottom.set_center_widget(column)
        if screen.notice:
            notice = Gtk.Label(label=self._(screen.notice), wrap=True, justify=Gtk.Justification.CENTER)
            notice.add_css_class("kidux-notice")
            notice.set_max_width_chars(60)
            middle.insert_child_after(notice, self._notice_after(middle))
        # Every screen is meant to fit 1280x800 whole. Where one does not, on a
        # smaller screen, at a larger scale or with more than it was drawn
        # for, its middle scrolls, down and sideways, and shows it (D63); its
        # bottom row stays in view, and focus moving by keyboard scrolls with
        # it.
        scroller = scroll.scroller(middle)
        scroll.watch(scroller, lambda way, needed, shown, name=screen.name:
                     self._check_fits(name, way, needed, shown))
        page.append(scroller)
        page.append(bottom)
        self._toasts = Gtk.Overlay(child=self._with_corner(page, screen.language))
        self._window.set_content(self._toasts)
        if self._pending_toast:
            self._toast(self._(self._pending_toast))
            self._pending_toast = None
        if self._focus is not None:
            self._focus.grab_focus()
        self._log_when_drawn(screen.name)
        self._schedule(screen)

    def _log_when_drawn(self, name: str) -> None:
        """Log `drawn <name>` once the screen has been painted. `showing` is
        logged before a screen is built, and building a page can take most
        of a second; the session tests wait for this line before they press
        a key on a screen or photograph it."""
        clock = self._window.get_frame_clock()
        if clock is None:
            return
        handler = 0

        def painted(_clock) -> None:
            clock.disconnect(handler)
            log.info("drawn %s", name)

        handler = clock.connect("after-paint", painted)

    def _check_fits(self, name: str, way: str, needed: int, shown: int) -> None:
        """Say so in the log, once, when a screen has to scroll, `way` "tall"
        or "wide": every screen but a page of settings that grows is meant to
        fit 1280x800 whole, and the session tests look for this line."""
        if self._screen is not None and self._screen.name == name \
                and name not in GROWS and (name, way) not in self._overflowed:
            self._overflowed.add((name, way))
            log.warning("the %s screen does not fit: %d pixels %s, %d shown",
                        name, needed, way, shown)

    def _toast(self, text: str) -> None:
        """A word in passing over the bottom of the page, gone by itself in
        a few seconds: how a job went, said without moving anything."""
        overlay = self._toasts
        if overlay is None:
            return
        log.info("toast: %s", text)
        said = Gtk.Label(label=text, halign=Gtk.Align.CENTER, valign=Gtk.Align.END,
                         margin_bottom=96, css_classes=["kidux-toast"])
        overlay.add_overlay(said)

        def gone() -> bool:
            if said.get_parent() is overlay:
                overlay.remove_overlay(said)
            return GLib.SOURCE_REMOVE

        GLib.timeout_add_seconds(TOAST_SECONDS, gone)

    def _notice_after(self, middle: Gtk.Box) -> Gtk.Widget | None:
        """The notice goes under the child's picture and name, when there are any."""
        child = middle.get_first_child()
        last_header = None
        while child is not None and child.has_css_class("kidux-header"):
            last_header = child
            child = child.get_next_sibling()
        return last_header

    def show_error(self) -> None:
        """What a child sees instead of a crash (docs/dev/greeter.md, section 6)."""
        self._cancel_timers()
        self._busy = False
        self._translations = i18n.translations(self._screen.language if self._screen else "")
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=32,
                      valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        label = Gtk.Label(label=self._(words.SOMETHING_WENT_WRONG), wrap=True,
                          justify=Gtk.Justification.CENTER)
        label.add_css_class("kidux-title")
        label.set_max_width_chars(30)
        box.append(label)
        box.append(self._row(
            self._button(vocabulary.TRY_AGAIN, lambda: self.run("start", owner=""), suggested=True),
            self._button(vocabulary.TURN_OFF, lambda: self.run("tap_power", owner="")),
        ))
        self._window.set_content(box)

    # --- pieces ------------------------------------------------------------------

    def _ask(self, method: str, *args):
        """A button's action: ask the flow `method(*args)`."""
        return lambda: self.run(method, *args)

    def _progress(self, update: dict, message: str) -> Gtk.Widget:
        """How far a job has got: a bar, and what it is doing under it."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, valign=Gtk.Align.CENTER)
        bar = Gtk.ProgressBar(fraction=float(update.get("fraction", 0.0)))
        bar.set_size_request(160, -1)
        box.append(bar)
        said = Gtk.Label(label=self._(message), css_classes=["kidux-field-label"])
        box.append(said)
        self._progress_followers.append(
            lambda moved: bar.set_fraction(float(moved.get("fraction", 0.0))))
        return box

    def _button(self, message: str, on_click, *, suggested=False, destructive=False,
                quiet=False, text: str | None = None) -> Gtk.Button:
        box = Gtk.Box(spacing=12, halign=Gtk.Align.CENTER)
        icon = ICONS.get(message)
        if icon:
            image = Gtk.Image.new_from_icon_name(icon)
            image.set_pixel_size(32)
            box.append(image)
        box.append(Gtk.Label(label=text if text is not None else self._(message)))
        button = Gtk.Button(child=box)
        if suggested:
            button.add_css_class("suggested-action")
        if destructive:
            button.add_css_class("destructive-action")
        if quiet:
            button.add_css_class("kidux-quiet")
        button.connect("clicked", lambda _button: on_click())
        return button

    def _row(self, *widgets: Gtk.Widget) -> Gtk.Box:
        row = Gtk.Box(spacing=16, halign=Gtk.Align.CENTER)
        for widget in widgets:
            row.append(widget)
        return row

    def _title(self, message: str) -> Gtk.Label:
        label = Gtk.Label(label=self._(message), wrap=True, justify=Gtk.Justification.CENTER)
        label.add_css_class("kidux-title")
        label.add_css_class("kidux-header")
        label.set_max_width_chars(30)
        return label

    def _avatar(self, child: dict, size: int = AVATAR_SIZE) -> Gtk.Image:
        name = avatars.resolve(child.get("avatar"))
        image = Gtk.Image.new_from_gicon(Gio.FileIcon.new(Gio.File.new_for_path(
            str(avatars.path_for(name)))))
        image.set_pixel_size(size)
        return image

    def _who(self, screen: Screen, middle: Gtk.Box, size: int = AVATAR_SIZE) -> None:
        """The child this screen is about: their picture and their name."""
        child = screen.data.get("child") or {}
        picture = self._avatar(child, size)
        picture.add_css_class("kidux-header")
        middle.append(picture)
        name = Gtk.Label(label=child.get("display_name") or child.get("username", ""))
        name.add_css_class("kidux-name")
        name.add_css_class("kidux-header")
        middle.append(name)

    def _password(self, placeholder: str, on_submit) -> Gtk.PasswordEntry:
        entry = Gtk.PasswordEntry(show_peek_icon=True, halign=Gtk.Align.CENTER)
        entry.set_property("placeholder-text", self._(placeholder))
        entry.connect("activate", lambda entry: on_submit(entry.get_text()))
        self._focus = entry
        return entry

    def _minutes(self, on_choice) -> Gtk.Box:
        """One button per choice of minutes; `on_choice(count)` when tapped."""
        row = Gtk.Box(spacing=16, halign=Gtk.Align.CENTER)
        for count in GRANT_CHOICES:
            row.append(self._button(
                vocabulary.HOW_LONG, lambda count=count: on_choice(count),
                text=vocabulary.minutes(self._translations, count)))
        return row

    # --- timers --------------------------------------------------------------------

    def _cancel_timers(self) -> None:
        for source in self._timers:
            GLib.source_remove(source)
        self._timers = []
        if self._idle_timer:
            GLib.source_remove(self._idle_timer)
            self._idle_timer = 0

    def _after(self, seconds: int, method: str, owner: str | None = "",
               poll: bool = False) -> None:
        """Ask `method` in `seconds`: of the sign-in or lock screen, or, with
        owner None, of whichever machine owns the screen then on display."""
        def fire():
            self._timers.remove(source)
            self.run(method, owner=owner, poll=poll)
            return GLib.SOURCE_REMOVE

        source = GLib.timeout_add_seconds(seconds, fire)
        self._timers.append(source)

    def _schedule(self, screen: Screen) -> None:
        if screen.name in FINAL:
            self._after(STUCK_SECONDS, "start")
        elif screen.name == "waiting":
            self._after(RETRY_SECONDS, "start")
        elif screen.owner == "panel" and screen.data.get("polling"):
            # A job is running: the page asks again every second.
            self._after(1, screen.data.get("poll", "poll_updates"), owner=None, poll=True)
        self._restart_idle()

    def _idle_method(self) -> tuple[str, int] | None:
        """What a stretch without a touch does on this screen, and how long a stretch is."""
        screen = self._screen
        if screen is None or screen.name in FINAL:
            return None
        if screen.owner == "panel":
            return "idle", int(screen.data.get("idle_seconds") or PANEL_IDLE_SECONDS)
        if screen.owner == "wizard":
            return None  # setting up a machine takes the time it takes
        if self._lock:
            return None if screen.name == "locked" else ("back", IDLE_SECONDS)
        if screen.name in ("choose", "waiting"):
            return None
        return "idle", IDLE_SECONDS

    def _restart_idle(self) -> None:
        if self._idle_timer:
            GLib.source_remove(self._idle_timer)
            self._idle_timer = 0
        idle = self._idle_method()
        if idle is None:
            return
        method, seconds = idle

        def fire():
            self._idle_timer = 0
            self.run(method)
            return GLib.SOURCE_REMOVE

        self._idle_timer = GLib.timeout_add_seconds(seconds, fire)

    def _touched(self) -> None:
        self._restart_idle()

    def _with_corner(self, page: Gtk.Widget, language: str) -> Gtk.Widget:
        """The page with the corner over its top right (D61): what a
        laptop has, as the child's screen shows it, taking no room from the
        page, so that every screen still fits 1280x800; compact on a narrow
        screen, so that it never reaches what is centred at the top. Nothing
        over it on a machine with nothing to show."""
        if self._corner is None or self._corner_language != language:
            if self._corner is not None:
                self._corner.close()
            width, _height = kidux_screen.logical_size(self._window.get_display())
            self._corner = Corner(self._, compact=kidux_screen.compact_corner(width))
            self._corner_language = language
        corner = self._corner.widget
        parent = corner.get_parent()
        if parent is not None:
            parent.remove_overlay(corner)
        if self._corner.empty:
            return page
        overlay = Gtk.Overlay(child=page)
        corner.set_halign(Gtk.Align.END)
        corner.set_valign(Gtk.Align.START)
        corner.set_margin_top(16)
        corner.set_margin_end(24)
        overlay.add_overlay(corner)
        return overlay

    def _key(self, _controller, keyval, _keycode, _state) -> bool:
        self._touched()
        # A laptop's keys for the screen, its keyboard's light and the sound:
        # cage binds none, so the screen answers them (D61, laptop.py).
        if laptop.press(keyval):
            if self._corner is not None:
                self._corner.refresh()
            return True
        # Escape is Back, wherever there is a Back: the whole of the screens
        # works from a keyboard without counting Tab presses.
        if keyval == Gdk.KEY_Escape and self._back_action is not None and not self._busy:
            self._back_action()
            return True
        return False

    def _tick(self) -> bool:
        if self._clock is not None:
            self._clock.set_label(GLib.DateTime.new_now_local().format("%H:%M"))
        return GLib.SOURCE_CONTINUE

    # --- the sign-in screen ------------------------------------------------------

    def _back(self, bottom: Gtk.CenterBox, message: str = vocabulary.BACK) -> Gtk.Button:
        """Back, always in the same corner, where Adult is on the first screen.

        The wizard and the panel are told which screen Back was pressed on,
        because their Back climbs one level from wherever that is."""
        screen = self._screen
        args = (screen.name,) if screen is not None and screen.owner else ()
        self._back_action = lambda: self.run("back", *args)
        back = self._button(message, self._back_action, quiet=True)
        bottom.set_start_widget(back)
        return back

    def _logo(self, height: int) -> Gtk.Widget:
        """Kidux's logo, `height` pixels tall; nothing if it is not installed."""
        return drawing(LOGO, height * 5 // 2, height)

    def _power_row(self, bottom: Gtk.CenterBox, *, adult: bool) -> None:
        if adult:
            bottom.set_start_widget(self._button(vocabulary.ADULT, self._ask("tap_adult"), quiet=True))
        bottom.set_end_widget(self._button(vocabulary.TURN_OFF,
                                           lambda: self.run("tap_power", owner=""), quiet=True))

    def _draw_choose(self, screen, page, middle, bottom):
        self._clock = Gtk.Label(label=GLib.DateTime.new_now_local().format("%H:%M"))
        self._clock.add_css_class("kidux-clock")
        page.append(self._clock)
        middle.append(self._logo(LOGO_LARGE))
        children = screen.data.get("children") or []
        if not children:
            middle.append(self._title(words.NOBODY_YET))
        else:
            middle.append(self._title(words.WHO_IS_USING))
            grid = keyboard_grid(Gtk.FlowBox(
                selection_mode=Gtk.SelectionMode.NONE, homogeneous=True,
                max_children_per_line=min(len(children), 4), min_children_per_line=1,
                column_spacing=16, row_spacing=16, halign=Gtk.Align.CENTER))
            for child in children:
                tile = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
                tile.append(self._avatar(child))
                name = Gtk.Label(label=child.get("display_name") or child.get("username", ""))
                name.add_css_class("kidux-name")
                tile.append(name)
                button = Gtk.Button(child=tile)
                button.add_css_class("kidux-child")
                button.add_css_class(f"avatar-{avatars.resolve(child.get('avatar'))}")
                button.connect("clicked", lambda _b, user=child["username"]: self.run("tap_child", user))
                grid.append(button)
                if self._focus is None:
                    self._focus = button
            middle.append(grid)
        self._power_row(bottom, adult=True)

    def _draw_waiting(self, screen, page, middle, bottom):
        middle.append(spinner())
        middle.append(self._row(self._button(vocabulary.TRY_AGAIN, self._ask("start"))))
        self._power_row(bottom, adult=False)

    def _draw_password(self, screen, page, middle, bottom):
        self._who(screen, middle)
        entry = self._password(vocabulary.CHILD_PASSWORD, lambda text: self.run("submit_password", text))
        middle.append(entry)
        sign_in = self._button(vocabulary.SIGN_IN, lambda: self.run("submit_password", entry.get_text()),
                               suggested=True)
        middle.append(self._row(sign_in))
        self._back(bottom)

    def _draw_needs_adult(self, screen, page, middle, bottom):
        self._who(screen, middle, AVATAR_SIZE_SMALL)
        choices = self._grant_row(lambda count: self.run("adult_grants", entry.get_text(), count))
        # Enter in the password field moves on to the choice of minutes.
        entry = self._password(vocabulary.ADULT_PASSWORD,
                               lambda _text: choices.get_first_child().grab_focus())
        middle.append(entry)
        middle.append(self._time_left(screen, vocabulary.HOW_LONG))
        middle.append(choices)
        self._back(bottom)

    def _draw_blocked(self, screen, page, middle, bottom):
        self._who(screen, middle)
        ask = self._button(vocabulary.ASK_ADULT_FOR_TIME, self._ask("ask_adult"), suggested=True)
        self._focus = ask
        middle.append(self._row(ask))
        self._back(bottom)

    def _draw_adult(self, screen, page, middle, bottom):
        middle.append(self._title(vocabulary.ADULT))
        self._adult_entry(middle, bottom, "submit_adult_password")

    def _adult_entry(self, middle: Gtk.Box, bottom: Gtk.CenterBox, method: str) -> None:
        entry = self._password(vocabulary.ADULT_PASSWORD, lambda text: self.run(method, text))
        middle.append(entry)
        go = self._button(vocabulary.CONTINUE, lambda: self.run(method, entry.get_text()),
                          suggested=True)
        middle.append(self._row(go))
        self._back(bottom)

    def _draw_power(self, screen, page, middle, bottom):
        middle.append(self._title(vocabulary.TURN_OFF_QUESTION))
        cancel = self._button(vocabulary.CANCEL, self._ask("power", "cancel"))
        self._focus = cancel
        buttons = [cancel]
        if not self._lock:
            buttons.append(self._button(vocabulary.RESTART, self._ask("power", "restart")))
        buttons.append(self._button(vocabulary.TURN_OFF, self._ask("power", "off"), destructive=True))
        middle.append(self._row(*buttons))

    def _draw_final(self, screen, page, middle, bottom):
        middle.append(spinner())

    _draw_starting = _draw_final
    _draw_turning_off = _draw_final
    _draw_unlocking = _draw_final
    _draw_ending = _draw_final
    _draw_restarting = _draw_final

    # --- the lock screen ---------------------------------------------------------

    def _draw_locked(self, screen, page, middle, bottom):
        self._who(screen, middle)
        if not screen.notice:
            locked = Gtk.Label(label=self._(words.LOCKED))
            locked.add_css_class("kidux-title")
            middle.append(locked)
        buttons = []
        if not screen.data.get("time_up"):
            buttons.append(self._button(vocabulary.CONTINUE, self._ask("tap_continue"), suggested=True))
        buttons.append(self._button(vocabulary.ADULT, self._ask("tap_adult")))
        buttons.append(self._button(vocabulary.LOG_OUT, self._ask("tap_log_out")))
        self._focus = buttons[0]
        middle.append(self._row(*buttons))
        self._power_row(bottom, adult=False)

    def _draw_child_password(self, screen, page, middle, bottom):
        self._who(screen, middle)
        entry = self._password(vocabulary.CHILD_PASSWORD,
                               lambda text: self.run("submit_child_password", text))
        middle.append(entry)
        label = vocabulary.LOG_OUT if screen.data.get("purpose") == "log_out" else vocabulary.CONTINUE
        go = self._button(label, lambda: self.run("submit_child_password", entry.get_text()),
                          suggested=True)
        middle.append(self._row(go))
        self._back(bottom)

    def _draw_adult_password(self, screen, page, middle, bottom):
        self._who(screen, middle, AVATAR_SIZE_SMALL)
        middle.append(self._title(vocabulary.ADULT))
        self._adult_entry(middle, bottom, "submit_adult_password")

    def _draw_adult_choice(self, screen, page, middle, bottom):
        self._who(screen, middle, AVATAR_SIZE_SMALL)
        middle.append(self._title(words.WHAT_NOW))
        middle.append(self._time_left(screen, vocabulary.GIVE_MORE_TIME))
        choices = self._grant_row(lambda count: self.run("adult_choice", "grant", count))
        self._focus = choices.get_first_child()
        middle.append(choices)
        middle.append(self._row(
            self._button(vocabulary.UNLOCK_TO_SAVE, self._ask("adult_choice", "save")),
            self._button(vocabulary.LOG_OUT, self._ask("adult_choice", "log_out")),
            self._button(words.ADULT_PANEL, self._ask("adult_choice", "panel")),
        ))
        self._back(bottom)

    # --- pieces the wizard and the panel share --------------------------------------

    def _small(self, button: Gtk.Button) -> Gtk.Button:
        button.add_css_class("kidux-small")
        return button

    def _heading(self, message: str) -> Gtk.Label:
        label = Gtk.Label(label=self._(message), wrap=True, justify=Gtk.Justification.CENTER)
        label.add_css_class("kidux-title")
        label.set_max_width_chars(36)
        return label

    def _text(self, message: str) -> Gtk.Label:
        label = Gtk.Label(label=self._(message), wrap=True, justify=Gtk.Justification.CENTER)
        label.set_max_width_chars(48)
        return label

    def _text_as_is(self, text: str) -> Gtk.Label:
        """A sentence that is already in the reader's language, or is not
        ours to translate: what apt said went wrong."""
        label = Gtk.Label(label=text, wrap=True, justify=Gtk.Justification.CENTER)
        label.set_max_width_chars(48)
        return label

    def _choices(self, pairs, method: str, *before, current=None) -> Gtk.Box:
        """One button per (value, label) pair; the current one stands out."""
        row = Gtk.Box(spacing=16, halign=Gtk.Align.CENTER)
        for value, label in pairs:
            button = self._button("", lambda value=value: self.run(method, *before, value),
                                  text=label, suggested=value == current)
            row.append(button)
            if self._focus is None:
                self._focus = button
        return row

    def _two_passwords(self, first: str, second: str, method: str,
                       before=lambda: ()) -> Gtk.Box:
        """A password typed twice: Enter in the first moves on to the second.

        `before()` gives any arguments that go ahead of the two passwords, read
        when the answer is sent, not when the screen is drawn."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=16, halign=Gtk.Align.CENTER)

        def send(*_args):
            self.run(method, *before(), one.get_text(), again.get_text())

        again = self._password(second, send)
        one = self._password(first, lambda _text: again.grab_focus())
        self._focus = one
        box.append(one)
        box.append(again)
        go = self._button(vocabulary.CONTINUE, send, suggested=True)
        box.append(self._row(go))
        return box

    # --- the adult's forms (D37) ----------------------------------------------------
    #
    # Smaller, denser, one screen per page: the adult sees everything a page is
    # about and changes it in place. Every control is a single stop for Tab, so
    # the forms work from a keyboard alone.

    def _adult(self, page: Gtk.Box) -> None:
        page.add_css_class("kidux-adult")

    def _form(self) -> Gtk.Grid:
        grid = Gtk.Grid(column_spacing=16, row_spacing=10, halign=Gtk.Align.CENTER)
        grid.kidux_rows = 0
        return grid

    def _field(self, grid: Gtk.Grid, message: str, control: Gtk.Widget,
               error: str | None = None, hint: str | None = None) -> None:
        label = Gtk.Label(label=self._(message), xalign=1.0)
        label.add_css_class("kidux-field-label")
        row = grid.kidux_rows
        grid.attach(label, 0, row, 1, 1)
        grid.attach(control, 1, row, 1, 1)
        grid.kidux_rows += 1
        if hint:
            note = Gtk.Label(label=self._(hint), xalign=0.0, wrap=True)
            note.set_max_width_chars(48)
            note.add_css_class("kidux-field-label")
            grid.attach(note, 1, grid.kidux_rows, 1, 1)
            grid.kidux_rows += 1
        if error:
            mark = Gtk.Label(label=self._(error), xalign=0.0, wrap=True)
            mark.set_max_width_chars(48)
            mark.add_css_class("kidux-field-error")
            grid.attach(mark, 1, grid.kidux_rows, 1, 1)
            grid.kidux_rows += 1

    def _entry(self, text: str = "", placeholder: str | None = None) -> Gtk.Entry:
        entry = Gtk.Entry(text=text)
        if placeholder:
            entry.set_property("placeholder-text", self._(placeholder))
        return entry

    def _secret(self, placeholder: str) -> Gtk.PasswordEntry:
        entry = Gtk.PasswordEntry(show_peek_icon=True)
        entry.set_property("placeholder-text", self._(placeholder))
        return entry

    def _dropdown(self, labels: list[str], selected: int) -> Gtk.DropDown:
        dropdown = Gtk.DropDown.new_from_strings(labels)
        dropdown.set_selected(max(0, selected))
        return dropdown

    def _picture_dropdown(self, names: list[str], current: str) -> Gtk.DropDown:
        """The avatars, as pictures only: their names are not words a child reads."""
        factory = Gtk.SignalListItemFactory()

        def setup(_factory, item):
            item.set_child(Gtk.Image(pixel_size=40))

        def bind(_factory, item):
            name = item.get_item().get_string()
            try:
                item.get_child().set_from_file(str(avatars.path_for(name)))
            except avatars.UnknownAvatarError:
                pass

        factory.connect("setup", setup)
        factory.connect("bind", bind)
        dropdown = Gtk.DropDown(model=Gtk.StringList.new(names), factory=factory)
        if current in names:
            dropdown.set_selected(names.index(current))
        return dropdown

    def _spin(self, value: int, most: int, on_activate, least: int = 1) -> Gtk.SpinButton:
        """A number of minutes, typed or stepped; Enter in it is `on_activate`."""
        spin = Gtk.SpinButton.new_with_range(least, most, 5)
        spin.set_value(value)
        spin.set_numeric(True)
        spin.connect("activate", lambda *_a: on_activate())
        return spin

    def _grant_row(self, on_choice) -> Gtk.Box:
        """The three usual amounts of time, and a number of the adult's own."""
        row = self._minutes(on_choice)
        spin = self._spin(15, 24 * 60, lambda: on_choice(int(spin.get_value())))
        row.append(spin)
        row.append(self._button(words.ADD, lambda: on_choice(int(spin.get_value()))))
        return row

    def _time_left(self, screen, message: str) -> Gtk.Label:
        """`message`, and how much time the child has left when the screen knows."""
        left = screen.data.get("left")
        parts = [self._(message)]
        if left is not None:
            parts.append(self._child_has_left(screen.data.get("child") or {}, left))
        return Gtk.Label(label=" · ".join(parts))

    def _child_has_left(self, child: dict, left: int) -> str:
        """How much time this child has left, said to the adult."""
        if left < 0:
            return self._(vocabulary.NO_TIME_LIMIT)
        return self._(vocabulary.TIME_CHILD_HAS_LEFT).format(
            name=child.get("display_name") or child.get("username", ""),
            minutes=vocabulary.minutes(self._translations, left // 60))

    def _access_control(self, current: tuple, errors: dict, grid: Gtk.Grid, *,
                        days: bool = False):
        """The three ways a child may use the computer, the minutes a day
        when it is the daily one, and, with `days`, the days of the week the
        time is for (D54), which manual mode does not ask. Returns a function
        reading what is set."""
        modes = list(MODES)
        labels = {"unlimited": vocabulary.ACCESS_UNLIMITED, "daily": vocabulary.ACCESS_DAILY,
                  "manual": vocabulary.ACCESS_MANUAL}
        mode, minutes, ticked = current
        chosen = self._dropdown([self._(labels[m]) for m in modes],
                                modes.index(mode) if mode in modes else 1)
        spin = self._spin(minutes or 60, 24 * 60, lambda: None)
        # The minutes on the same row as the mode they belong to: a child's
        # page has one row to spare at 1280x800, and Windows takes it.
        row = Gtk.Box(spacing=12)
        row.append(chosen)
        row.append(spin)
        row.append(Gtk.Label(label=self._(words.MINUTES_A_DAY)))
        self._field(grid, words.HOW_MAY_THEY_USE, row, errors.get("access"))
        boxes = []
        if days:
            week = Gtk.Box(spacing=8)
            for name, digit in zip(words.WEEKDAYS, ticked):
                box = Gtk.CheckButton(label=self._(name), active=digit == "1")
                boxes.append(box)
                week.append(box)
            self._field(grid, words.DAYS, week)

        def follow(*_args):
            index = chosen.get_selected()
            picked = modes[index] if 0 <= index < len(modes) else "daily"
            spin.set_sensitive(picked == "daily")
            for box in boxes:
                box.set_sensitive(picked != "manual")

        chosen.connect("notify::selected", follow)
        follow()

        def read() -> str:
            index = chosen.get_selected()
            picked = modes[index] if 0 <= index < len(modes) else "daily"
            week = "".join("1" if box.get_active() else "0" for box in boxes) if boxes \
                else ticked
            return f"{picked}:{int(spin.get_value())}:{week}"

        return read

    def _tab_bar(self, page: Gtk.Box, bottom: Gtk.CenterBox, current: str) -> None:
        """The panel's four pages across the top, *Close* in the corner of Back."""
        row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        for name, message in (("children", words.CHILDREN), ("modules", words.MODULES),
                              ("system", words.SYSTEM), ("network", words.NETWORK)):
            row.append(self._button(message, self._ask("tab", name), suggested=name == current))
        page.append(row)
        self._back_action = self._ask("close")
        bottom.set_start_widget(self._button(words.CLOSE, self._back_action, quiet=True))

    def _child_form(self, screen: Screen, box: Gtk.Box, *, new: bool, go_message: str,
                    go_method: str, remove: bool, panel: bool = False) -> None:
        """A child's form: the same in the wizard, for a new child in the panel,
        and for a child who exists, where it starts filled in. On the panel it
        has the days of the week and Windows, which the wizard does not ask:
        its first child has every day and no windows."""
        data = screen.data
        errors = data.get("errors") or {}
        defaults = data.get("defaults") or {}
        current = {} if new else (data.get("current") or {})
        draft = data.get("draft") or {}

        def value(key):
            return draft.get(key, current.get(key, defaults.get(key)))

        grid = self._form()
        # Nine rows on the panel, under the time and the children: a little
        # closer than other forms, so that the page fits 1280x800 whole.
        grid.set_row_spacing(8)
        name = self._entry(value("display_name") or "")
        self._field(grid, words.NAME, name, errors.get("display_name"))

        pictures = data.get("avatars") or []
        picture = self._picture_dropdown(pictures, value("avatar") or "")
        self._field(grid, words.PICTURE, picture, errors.get("avatar"))

        locales = data.get("languages") or []
        language = self._dropdown([label for _, label in locales],
                                  [code for code, _ in locales].index(value("language"))
                                  if value("language") in [code for code, _ in locales] else 0)
        self._field(grid, words.LANGUAGE, language, errors.get("language"))

        password = self._secret(words.PASSWORD)
        again = self._secret(words.TYPE_IT_AGAIN)
        self._field(grid, words.PASSWORD, password, errors.get("password"))
        self._field(grid, words.TYPE_IT_AGAIN, again,
                    hint=words.CHILD_PASSWORD_EXPLAINED if new else None)

        read_access = self._access_control(parse_access(value("access")), errors, grid,
                                           days=panel)
        # Windows (D46), on the panel only: the wizard does not ask. The
        # switch and what it does on one row, which the page has room for.
        in_windows = None
        if panel:
            in_windows = Gtk.Switch(active=bool(value("windows")), valign=Gtk.Align.CENTER)
            said = Gtk.Label(label=self._(words.WINDOWS_EXPLAINED), xalign=0.0, wrap=True)
            said.set_max_width_chars(60)
            said.add_css_class("kidux-field-label")
            row = Gtk.Box(spacing=12)
            row.append(in_windows)
            row.append(said)
            self._field(grid, words.WINDOWS, row, errors.get("windows"))
        box.append(grid)

        def fields() -> dict:
            chosen_picture = picture.get_selected()
            chosen_language = language.get_selected()
            return {
                "display_name": name.get_text(),
                "avatar": pictures[chosen_picture] if 0 <= chosen_picture < len(pictures) else "",
                "language": locales[chosen_language][0] if 0 <= chosen_language < len(locales) else "",
                "password": password.get_text(),
                "again": again.get_text(),
                "access": read_access(),
                **({"windows": in_windows.get_active()} if in_windows is not None else {}),
            }

        def go(*_args):
            self.run(go_method, fields())

        # Enter moves on through what a new child needs, and saves at the end;
        # for a child who exists, Enter in their name saves straight away.
        if new:
            name.connect("activate", lambda *_a: password.grab_focus())
        else:
            name.connect("activate", go)
        password.connect("activate", lambda *_a: again.grab_focus())
        again.connect("activate", go)
        self._focus = name

        buttons = [self._button(go_message, go, suggested=True, text=self._(go_message))]
        if remove and not data.get("confirm_remove"):
            buttons.append(self._button(words.REMOVE, self._ask("ask_remove"), destructive=True))
        box.append(self._row(*buttons))
        if remove and data.get("confirm_remove"):
            box.append(self._text(words.REMOVE_EXPLAINED))
            cancel = self._button(vocabulary.CANCEL, self._ask("select", data.get("selected")))
            self._focus = cancel
            box.append(self._row(
                cancel,
                self._button(words.REMOVE_KEEP_FILES, self._ask("remove", True)),
                self._button(words.REMOVE, self._ask("remove", False), destructive=True),
            ))

    # --- the first-run wizard -----------------------------------------------------

    def _draw_wiz_language(self, screen, page, middle, bottom):
        middle.append(self._logo(AVATAR_SIZE))
        middle.append(self._heading(words.WELCOME))
        middle.append(self._choices(screen.data["languages"], "choose_language"))
        self._power_row(bottom, adult=False)

    def _draw_wiz_keyboard(self, screen, page, middle, bottom):
        middle.append(self._heading(words.WHICH_KEYBOARD))
        middle.append(self._choices(
            [(layout, self._(label)) for layout, label in screen.data["keyboards"]],
            "choose_keyboard"))
        self._back(bottom)
        self._power_row(bottom, adult=False)

    def _draw_wiz_password(self, screen, page, middle, bottom):
        middle.append(self._heading(words.CHOOSE_ADULT_PASSWORD))
        middle.append(self._text(words.ADULT_PASSWORD_EXPLAINED))
        middle.append(self._two_passwords(vocabulary.ADULT_PASSWORD, words.TYPE_IT_AGAIN,
                                          "submit_adult_password"))
        middle.append(self._text(words.LONGER_IS_SAFER))
        self._power_row(bottom, adult=False)

    def _draw_wiz_statistics(self, screen, page, middle, bottom):
        middle.append(self._heading(words.SHARE_STATISTICS_HEADING))
        middle.append(self._text(words.SHARE_STATISTICS_EXPLAINED))
        shared = Gtk.Switch(active=bool(screen.data.get("shared", True)),
                            valign=Gtk.Align.CENTER)
        middle.append(self._row(Gtk.Label(label=self._(words.SHARE_STATISTICS)), shared))
        go = self._button(vocabulary.CONTINUE,
                          lambda: self.run("set_statistics", shared.get_active()), suggested=True)
        self._focus = go
        middle.append(self._row(go))
        self._power_row(bottom, adult=False)

    def _draw_wiz_unlock(self, screen, page, middle, bottom):
        middle.append(self._heading(words.UNLOCK_TO_FINISH))
        entry = self._password(vocabulary.ADULT_PASSWORD, lambda text: self.run("submit_unlock", text))
        middle.append(entry)
        middle.append(self._row(self._button(
            vocabulary.CONTINUE, lambda: self.run("submit_unlock", entry.get_text()), suggested=True)))
        self._power_row(bottom, adult=False)

    def _draw_wiz_child(self, screen, page, middle, bottom):
        self._adult(page)
        middle.append(self._heading(words.FIRST_CHILD))
        self._child_form(screen, middle, new=True, go_message=words.ADD, go_method="add_child",
                         remove=False)
        self._power_row(bottom, adult=False)

    def _draw_wiz_done(self, screen, page, middle, bottom):
        middle.append(self._heading(words.ALL_SET))
        middle.append(self._text(words.ALL_SET_EXPLAINED))
        go = self._button(vocabulary.CONTINUE, self._ask("finish"), suggested=True)
        self._focus = go
        middle.append(self._row(go))

    # --- the adult panel ------------------------------------------------------------

    def _draw_panel_children(self, screen, page, middle, bottom):
        self._adult(page)
        self._tab_bar(page, bottom, "children")
        data = screen.data
        selected = data.get("selected")

        row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        for child in data["children"]:
            tile = Gtk.Box(spacing=8)
            tile.append(self._avatar(child, 40))
            tile.append(Gtk.Label(label=child.get("display_name") or child["username"]))
            button = Gtk.Button(child=tile)
            button.add_css_class(f"avatar-{avatars.resolve(child.get('avatar'))}")
            if child["username"] == selected:
                button.add_css_class("kidux-selected")
            button.connect("clicked", lambda _b, user=child["username"]: self.run("select", user))
            row.append(button)
        add = self._button(words.ADD_CHILD, self._ask("new_child"), suggested=selected is None)
        row.append(add)
        middle.append(row)

        if selected is None:
            self._child_form(screen, middle, new=True, go_message=words.ADD, go_method="add_child",
                             remove=False, panel=True)
            return

        # Time first, as it is what an adult most often comes for; the focus
        # still starts in the form, so an Enter pressed out of habit gives
        # nobody time.
        # The number is what the child has left today, which Set sets, zero
        # included (D50); a child with no limit has nothing there to set.
        used, left = data.get("used", 0), data.get("left", -1)
        chosen = next((c for c in data["children"] if c["username"] == selected), {})
        facts = [f"{self._(words.USED_TODAY)}: "
                 f"{vocabulary.minutes(self._translations, used // 60)}"]
        if left < 0:
            facts.append(self._child_has_left(chosen, left))
        time_row = Gtk.Box(spacing=8, halign=Gtk.Align.CENTER)
        time_row.append(Gtk.Label(label=" · ".join(facts)))
        time_row.append(Gtk.Label(label=self._(vocabulary.GIVE_MORE_TIME) + ":"))
        for count in data.get("grant", GRANT_CHOICES):
            time_row.append(self._button("", self._ask("give_time", count),
                                         text=vocabulary.minutes(self._translations, count)))
        time_row.append(Gtk.Label(label=self._(words.LEFT_TODAY) + ":"))
        spin = self._spin(max(0, left) // 60, 24 * 60,
                          lambda: self.run("set_time_left", int(spin.get_value())), least=0)
        time_row.append(spin)
        time_row.append(self._button(words.SET,
                                     lambda: self.run("set_time_left", int(spin.get_value()))))
        middle.append(time_row)
        self._child_form(screen, middle, new=False, go_message=words.SAVE, go_method="save_child",
                         remove=True, panel=True)

    def _draw_panel_modules(self, screen, page, middle, bottom):
        """Two parts of one form. The installed modules down, the children
        across, a switch where they meet, saved as soon as it is flipped,
        and Remove at the end of each row. Under them, the modules the
        archive offers that are not installed, each with Install, and Look
        for modules. The two lists grow with every module there is, so they
        scroll in a room of their own, between the tabs and the bottom row,
        centred there while they fit: the page itself always fits."""
        self._adult(page)
        self._tab_bar(page, bottom, "modules")
        data = screen.data
        rows, kids = data.get("modules") or [], data.get("children") or []
        update = data.get("update") or {}
        lists = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20,
                        valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        job = update.get("job")
        # Both lists are by age, the test modules last (D73), and a box at
        # the top narrows them to the modules whose name or description
        # holds what is typed: every row that can be hidden registers
        # itself in `matchable` with its words. Narrowing hides rows in
        # place, without asking the panel, so the typing keeps its focus.
        matchable: list[tuple[str, list[Gtk.Widget]]] = []
        find = Gtk.SearchEntry(placeholder_text=self._(words.FIND_A_MODULE), width_chars=28,
                               halign=Gtk.Align.CENTER)
        find.connect("search-changed", lambda entry: self._narrow_modules(entry.get_text(),
                                                                          matchable))
        how = Gtk.Label(label=self._(words.MODULES_BY_AGE), wrap=True,
                        justify=Gtk.Justification.CENTER, max_width_chars=60,
                        css_classes=["kidux-field-label"])
        lists.append(self._row(find, how))

        if rows:
            lists.append(self._installed_modules(rows, kids, data.get("confirm_remove"),
                                                 matchable, update))
        else:
            lists.append(self._text(words.NO_MODULES_YET))

        if job == "checking":
            lists.append(self._row(spinner_small(),
                                    Gtk.Label(label=self._(words.LOOKING_FOR_MODULES))))
        if data.get("failure"):
            lists.append(self._text_as_is(data["failure"]))

        lists.append(self._heading(words.ADD_MODULES))
        offered = data.get("offered") or []
        if offered:
            grid = Gtk.Grid(column_spacing=24, row_spacing=12, halign=Gtk.Align.CENTER)
            for number, entry in enumerate(offered):
                about = self._about_module(entry["name"], entry.get("description", ""),
                                           self._suits(entry), self._first(entry),
                                           entry.get("offered_version", ""))
                grid.attach(about, 0, number, 1, 1)
                install = self._button(words.INSTALL, self._ask("install_module", entry["id"]))
                install.set_valign(Gtk.Align.CENTER)
                grid.attach(install, 1, number, 1, 1)
                matchable.append((f"{entry['name']} {entry.get('description', '')}",
                                  [about, install]))
                if self._focus is None:
                    self._focus = install
            lists.append(grid)
        else:
            lists.append(self._text(words.ALL_MODULES_INSTALLED if data.get("source")
                                     else words.NO_MODULE_SOURCE))
        look = self._button(words.LOOK_FOR_MODULES, self._ask("look_for_modules"))
        lists.append(self._row(look))
        if self._focus is None:
            self._focus = look
        room = scroll.scroller(lists, horizontal=False)
        room.set_propagate_natural_width(True)
        middle.set_valign(Gtk.Align.FILL)
        middle.append(room)
        # Drawn again while a job runs only when something but its progress
        # changes, and then it stays where the adult had scrolled it; while
        # Remove asks, its question, in its own row, which may be below the
        # fold, is brought into view with the focus on it, and so is that
        # Remove once the question is cancelled.
        show_focus = bool(data.get("confirm_remove")) or self._focus_returned
        self._focus_returned = False
        if not data.get("confirm_remove"):
            self._asked_about = None
        if self._modules_room is not None:
            keep_place(self._modules_room, room,
                       then=lambda: self._into_view(room, show_focus=show_focus))
        self._modules_room = room
        if data.get("toast"):
            self._pending_toast = data["toast"]

    def _into_view(self, room, show_focus: bool) -> None:
        """With `show_focus`, scroll `room` the least that shows what has the
        focus in it, and no more: Gtk.Viewport.scroll_to centres it, which
        moves a page the adult had placed. Then say where it is, for the
        session tests."""
        adjustment = room.get_vadjustment()
        viewport = room.get_child()
        content = viewport.get_child() if isinstance(viewport, Gtk.Viewport) else None
        focus = self._focus

        def where() -> tuple[float, float] | None:
            """The focus's top and bottom in the content, which scrolling
            does not move."""
            if content is None or focus is None or not focus.is_ancestor(content):
                return None
            found, bounds = focus.compute_bounds(content)
            return (bounds.get_y(), bounds.get_y() + bounds.get_height()) if found else None

        span = where()
        if show_focus and span is not None:
            top, bottom = span
            value, page = adjustment.get_value(), adjustment.get_page_size()
            if top < value:
                adjustment.set_value(max(adjustment.get_lower(), top - FOCUS_MARGIN))
            elif bottom > value + page:
                adjustment.set_value(bottom - page + FOCUS_MARGIN)
        clock = room.get_frame_clock()
        if clock is None:
            return
        handler = 0

        def painted(_clock) -> None:
            clock.disconnect(handler)
            value, page = adjustment.get_value(), adjustment.get_page_size()
            span = where()
            seen = span is not None and span[0] >= value and span[1] <= value + page
            log.info("modules room kept at %d of %d, the focus %s", value,
                     adjustment.get_upper() - page, "in view" if seen else "out of view")

        handler = clock.connect("after-paint", painted)

    def _draw_panel_module_settings(self, screen, page, middle, bottom):
        """A module's settings, as its manifest declares them (D90): each down
        the side with what it is for, every child across, and where they
        meet the child's value, in the control of its kind, saved as soon as
        it is changed. A secret is never shown, only said to be set."""
        self._adult(page)
        self._tab_bar(page, bottom, "modules")
        # Back, to the Modules page, in the corner where the panel's own pages
        # have Close, which moves to the other corner here.
        self._back(bottom)
        bottom.set_end_widget(self._button(words.CLOSE, self._ask("close"), quiet=True))
        data = screen.data
        module_id, kids = data["module"], data.get("children") or []
        values, secrets = data.get("values") or {}, data.get("secrets") or {}
        title = Gtk.Label(label=self._(words.MODULE_SETTINGS_TITLE).format(
            name=data.get("module_name", module_id)), wrap=True, justify=Gtk.Justification.CENTER,
            max_width_chars=36, css_classes=["kidux-title"])
        middle.append(title)
        middle.append(self._text(words.MODULE_SETTINGS_HOW))
        grid = Gtk.Grid(column_spacing=24, row_spacing=16, halign=Gtk.Align.CENTER)
        for column, child in enumerate(kids, start=1):
            who = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, halign=Gtk.Align.CENTER)
            who.append(self._avatar(child, 40))
            who.append(Gtk.Label(label=child.get("display_name") or child["username"]))
            grid.attach(who, column, 0, 1, 1)
        for number, setting in enumerate(data.get("settings") or [], start=1):
            about = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER)
            about.append(Gtk.Label(label=setting["label"], xalign=0, wrap=True,
                                   max_width_chars=36, css_classes=["kidux-module-name"]))
            if setting.get("description"):
                about.append(Gtk.Label(label=setting["description"], xalign=0, wrap=True,
                                       max_width_chars=36, css_classes=["kidux-field-label"]))
            grid.attach(about, 0, number, 1, 1)
            for column, child in enumerate(kids, start=1):
                username = child["username"]
                control = self._setting_control(module_id, username, setting,
                                                values.get(username, {}).get(setting["key"]),
                                                setting["key"] in secrets.get(username, []))
                grid.attach(control, column, number, 1, 1)
                if self._focus is None:
                    self._focus = control
        room = scroll.scroller(grid, horizontal=True)
        room.set_propagate_natural_width(True)
        middle.set_valign(Gtk.Align.FILL)
        middle.append(room)

    def _setting_control(self, module_id: str, username: str, setting: dict, value,
                         secret_set: bool) -> Gtk.Widget:
        """The control of a setting's kind for one child, which saves itself
        when it is changed: a switch when flipped, a number when it moves, a
        text or a secret when Enter is pressed or the focus leaves it."""
        key, kind = setting["key"], setting["kind"]

        def save(new_value) -> None:
            self.run("set_module_setting", module_id, username, key, new_value)

        if kind == "switch":
            switch = Gtk.Switch(active=bool(value), halign=Gtk.Align.CENTER,
                                valign=Gtk.Align.CENTER)
            switch.connect("notify::active", lambda widget, _spec: save(widget.get_active()))
            return switch
        if kind in ("integer", "number"):
            low = setting.get("minimum")
            high = setting.get("maximum")
            spin = Gtk.SpinButton.new_with_range(-1e6 if low is None else low,
                                                 1e6 if high is None else high,
                                                 1 if kind == "integer" else 0.1)
            spin.set_digits(0 if kind == "integer" else 2)
            spin.set_value(float(value or 0))
            spin.set_valign(Gtk.Align.CENTER)

            def moved(widget) -> None:
                number = widget.get_value()
                save(int(round(number)) if kind == "integer" else float(number))

            spin.connect("value-changed", moved)
            return spin
        entry = Gtk.PasswordEntry(show_peek_icon=True) if kind == "secret" else Gtk.Entry()
        entry.set_valign(Gtk.Align.CENTER)
        entry.set_size_request(220, -1)
        if kind == "secret":
            if secret_set:
                entry.set_property("placeholder-text", self._(words.SECRET_IS_SET))
        else:
            entry.set_text(str(value or ""))
        said = {"text": entry.get_text()}

        def done(*_args) -> None:
            text = entry.get_text()
            if text == said["text"] or (kind == "secret" and not text):
                return
            said["text"] = text
            save(text)

        entry.connect("activate", done)
        leaving = Gtk.EventControllerFocus()
        leaving.connect("leave", done)
        entry.add_controller(leaving)
        if kind == "secret" and secret_set:
            box = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
            box.append(entry)
            box.append(self._button(words.SECRET_FORGET, lambda: save(""), quiet=True))
            return box
        return entry

    @staticmethod
    def _narrow_modules(typed: str, matchable: list[tuple[str, list[Gtk.Widget]]]) -> None:
        """Show only the rows whose words hold every word typed, in any
        case; everything, when nothing is typed."""
        wanted = typed.casefold().split()
        for text, widgets in matchable:
            words_of = text.casefold()
            shown = all(word in words_of for word in wanted)
            for widget in widgets:
                widget.set_visible(shown)

    def _about_module(self, name: str, description: str, suits: str = "",
                      first: str = "", version: str = "") -> Gtk.Widget:
        """A module's name and, beside it, smaller, its ages; under them, as
        small, the modules recommended before it, when it names any; then
        its description. Wide rather than tall, so that the page stays
        whole at 1280x800 with a module installed and three on offer."""
        about = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=2, valign=Gtk.Align.CENTER)
        title = Gtk.Box(spacing=12)
        label = Gtk.Label(label=name, xalign=0.0, valign=Gtk.Align.BASELINE_FILL)
        label.add_css_class("kidux-module-name")
        title.append(label)
        for small in (suits, self._(words.MODULE_VERSION).format(version=version)
                      if version else ""):
            if small:
                title.append(Gtk.Label(label=small, xalign=0.0,
                                       valign=Gtk.Align.BASELINE_FILL,
                                       css_classes=["kidux-field-label", "kidux-module-suits"]))
        about.append(title)
        if first:
            about.append(Gtk.Label(label=first, xalign=0.0, wrap=True, max_width_chars=56,
                                   css_classes=["kidux-field-label", "kidux-module-suits"]))
        if description:
            about.append(Gtk.Label(label=description, xalign=0.0, wrap=True,
                                   max_width_chars=56, css_classes=["kidux-field-label"]))
        return about

    def _suits(self, entry: dict) -> str:
        """A module's ages (D55): *Ages 4 to 8*, or one bound; "" when it
        says none."""
        least, most = entry.get("min_age", 0), entry.get("max_age", 0)
        if least and most:
            return self._(words.AGES_FROM_TO).format(least=least, most=most)
        if least:
            return self._(words.AGES_FROM).format(least=least)
        if most:
            return self._(words.AGES_TO).format(most=most)
        return ""

    def _first(self, entry: dict) -> str:
        """The modules recommended before this one (D55), by name: *Recommended
        before: Hello*; "" when it names none."""
        if not entry.get("first"):
            return ""
        return self._(words.FIRST).format(modules=", ".join(entry["first"]))

    def _installed_modules(self, rows, kids, confirm_remove, matchable,
                           update=None) -> Gtk.Widget:
        """The grid of switches, with Settings and Remove at the end of each
        row. The row of a module being installed, or removed, shows how far
        that has got where its switches and buttons are; Remove tapped asks in its own row:
        the question, Cancel, which has the focus, and Remove. Nothing of it
        moves the page. The tab order of a row is its switches, then its
        buttons. Each row's widgets go into `matchable` with the module's
        words, for the box that narrows the lists."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        grid = Gtk.Grid(column_spacing=24, row_spacing=12, halign=Gtk.Align.CENTER)
        # The switches, then Settings when any module has them, then Remove:
        # a column with nothing in it would still be spaced when something
        # spans it, and the page would widen with it.
        last = len(kids) + (2 if any(row.get("settings") for row in rows) else 1)
        for column, child in enumerate(kids, start=1):
            who = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4, halign=Gtk.Align.CENTER)
            who.append(self._avatar(child, 40))
            who.append(Gtk.Label(label=child.get("display_name") or child["username"]))
            grid.attach(who, column, 0, 1, 1)

        def flip(switch, _spec, username, module_id):
            self._flipped = (username, module_id)
            self.run("set_module", username, module_id, switch.get_active())

        for number, row in enumerate(rows, start=1):
            description = row.get("description", "")
            if row.get("needs_windows"):
                description = " · ".join(filter(None, [description,
                                                       self._(words.NEEDS_WINDOWS)]))
            if not row.get("packaged", True):
                description = " · ".join(filter(None, [description,
                                                       self._(words.NOT_FROM_A_PACKAGE)]))
            about = self._about_module(row["name"], description, self._suits(row),
                                       self._first(row), row.get("version", ""))
            grid.attach(about, 0, number, 1, 1)
            in_row: list[Gtk.Widget] = [about]
            matchable.append((f"{row['name']} {description}", in_row))
            job = row.get("job")
            if job is not None or row["id"] == confirm_remove:
                # Not on the computer yet, on its way off it, or asked
                # about: how far that has got, that its turn is coming, or
                # the question, across the room its switches and buttons
                # take and no wider, so that nothing on the page moves.
                if job in ("to-install", "to-remove"):
                    instead = Gtk.Label(label=self._(words.WAITING), valign=Gtk.Align.CENTER,
                                        css_classes=["kidux-field-label"])
                elif job is not None:
                    instead = self._progress(update or {}, words.INSTALLING_MODULE
                                             if job == "installing" else words.REMOVING_MODULE)
                else:
                    instead = self._remove_question(row)
                grid.attach(instead, 1, number, last, 1)
                in_row.append(instead)
                continue
            for column, child in enumerate(kids, start=1):
                username = child["username"]
                if row.get("needs_windows") and not child.get("windows"):
                    # Off, and not to be switched on, for a child whose
                    # modules do not open in windows (D46).
                    off = Gtk.Switch(active=False, sensitive=False,
                                     halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER)
                    grid.attach(off, column, number, 1, 1)
                    in_row.append(off)
                    continue
                switch = Gtk.Switch(active=bool(row["enabled"].get(username)),
                                    halign=Gtk.Align.CENTER, valign=Gtk.Align.CENTER,
                                    tooltip_text=f"{row['name']} · "
                                                 f"{child.get('display_name') or username}")
                switch.connect("notify::active", flip, username, row["id"])
                grid.attach(switch, column, number, 1, 1)
                in_row.append(switch)
                # The switch just flipped keeps the focus, unless Remove's
                # question, or the Remove it goes back to, has it.
                if self._focus is None or (self._flipped == (username, row["id"])
                                           and confirm_remove is None
                                           and self._asked_about is None):
                    self._focus = switch
            if row.get("settings"):
                settings = self._button(words.MODULE_SETTINGS,
                                        self._ask("module_settings", row["id"]))
                settings.set_valign(Gtk.Align.CENTER)
                grid.attach(settings, len(kids) + 1, number, 1, 1)
                in_row.append(settings)
            remove = self._button(words.REMOVE, self._ask("ask_remove_module", row["id"]),
                                  destructive=True)
            remove.set_valign(Gtk.Align.CENTER)
            if row["id"] == self._asked_about and confirm_remove is None:
                self._focus = remove
                self._focus_returned = True
            grid.attach(remove, last, number, 1, 1)
            in_row.append(remove)
        box.append(grid)
        return box

    def _remove_question(self, row: dict) -> Gtk.Widget:
        """Whether to remove a module, in its row: the question in short
        lines, Cancel as a cross, which has the focus, and Remove."""
        asked = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=6,
                        valign=Gtk.Align.CENTER, halign=Gtk.Align.CENTER)
        question = (words.REMOVE_MODULE_QUESTION if row.get("packaged", True)
                    else words.REMOVE_FOLDER_QUESTION)
        asked.append(Gtk.Label(label=self._(question).format(name=row["name"]), wrap=True,
                               width_chars=14, max_width_chars=18,
                               justify=Gtk.Justification.CENTER,
                               css_classes=["kidux-field-label"]))
        cancel = Gtk.Button(icon_name="window-close-symbolic",
                            tooltip_text=self._(vocabulary.CANCEL), valign=Gtk.Align.CENTER)
        cancel.update_property([Gtk.AccessibleProperty.LABEL], [self._(vocabulary.CANCEL)])
        cancel.connect("clicked", lambda _b: self._ask("tab", "modules")())
        self._focus = cancel
        self._asked_about = row["id"]
        asked.append(self._row(cancel, self._button(
            words.REMOVE, self._ask("remove_module", row["id"]), destructive=True)))
        return asked

    def _updates_row(self, update: dict) -> Gtk.Widget:
        """What the update job is doing, and the one thing to do next."""
        row = Gtk.Box(spacing=12)
        job, outcome = update.get("job"), update.get("outcome")
        packages = update.get("packages") or []

        def say(message: str, detail: str = "", whole: str = "") -> Gtk.Label:
            # Two lines at most, the rest behind an ellipsis and in the
            # tooltip: the System page fits 1280x800 with little to spare,
            # and a long list of updates or apt's line must not push it over.
            text = self._(message) + (f" {detail}" if detail else "")
            said = Gtk.Label(label=text, xalign=0.0, wrap=True, max_width_chars=40,
                             lines=2, ellipsize=Pango.EllipsizeMode.END,
                             tooltip_text=whole or text)
            row.append(said)
            return said

        def act(message: str, method: str) -> None:
            row.append(self._button(message, self._ask(method), text=self._(message)))

        if job in ("checking", "away"):
            row.append(spinner_small())
            say(words.LOOKING_FOR_UPDATES if job == "checking" else words.INSTALLING)
        elif job in ("applying", "installing", "removing"):
            bar = Gtk.ProgressBar(fraction=float(update.get("fraction", 0.0)), valign=Gtk.Align.CENTER)
            bar.set_size_request(200, -1)
            row.append(bar)
            said = say(words.INSTALLING, update.get("package", ""))
            self._progress_followers.append(lambda moved: (
                bar.set_fraction(float(moved.get("fraction", 0.0))),
                said.set_label(f"{self._(words.INSTALLING)} {moved.get('package', '')}".strip())))
        elif outcome == "checked" and packages:
            count = len(packages)
            shown = ", ".join(packages[:4]) + (", …" if count > 4 else "")
            said = self._translations.ngettext("{count} update:", "{count} updates:", count) \
                .format(count=count)
            say(said, shown, f"{said} {', '.join(packages)}")
            act(words.INSTALL, "install_updates")
        elif outcome == "checked":
            say(words.UP_TO_DATE)
            act(words.LOOK_FOR_UPDATES, "look_for_updates")
        elif outcome in ("updated", "up-to-date"):
            say(words.UPDATED if outcome == "updated" else words.UP_TO_DATE)
            act(words.LOOK_FOR_UPDATES, "look_for_updates")
        elif outcome == "restart-needed":
            say(words.RESTART_TO_FINISH)
            act(words.RESTART_NOW, "restart_now")
        elif outcome == "failed":
            say(words.UPDATE_FAILED, update.get("detail", ""))
            act(vocabulary.TRY_AGAIN, "look_for_updates")
        else:
            act(words.LOOK_FOR_UPDATES, "look_for_updates")
        return row

    def _draw_panel_system(self, screen, page, middle, bottom):
        self._adult(page)
        self._tab_bar(page, bottom, "system")
        data = screen.data
        errors = data.get("errors") or {}
        grid = self._form()
        # Twelve rows, the parts' versions and the note on the sizes among
        # them: closer than other forms, so that the page fits 1280x800 whole.
        grid.set_row_spacing(6)

        # Kidux's version and the updates on one row, and under them, in the
        # small letters of the ages, each part's own version: the page has
        # no room for another row at 1280x800.
        version = Gtk.Box(spacing=24)
        version.append(Gtk.Label(label=data.get("version", ""), xalign=0.0))
        version.append(self._updates_row(data.get("update") or {}))
        self._field(grid, words.VERSION, version)
        if data.get("parts"):
            grid.attach(Gtk.Label(
                label=" · ".join(f"{self._(message)} {number}"
                                 for message, number in data["parts"]),
                xalign=0.0, wrap=True, max_width_chars=90,
                css_classes=["kidux-field-label", "kidux-module-suits"]),
                1, grid.kidux_rows, 1, 1)
            grid.kidux_rows += 1

        recovery = data.get("recovery")
        if recovery is None:
            shown = self._button(words.SHOW, self._ask("show_recovery"))
            shown.set_halign(Gtk.Align.START)
        else:
            shown = Gtk.Label(label=recovery, selectable=True, xalign=0.0)
            shown.add_css_class("kidux-name")
        self._field(grid, words.RECOVERY_PASSWORD, shown)
        explained = Gtk.Label(label=self._(words.RECOVERY_EXPLAINED), xalign=0.0, wrap=True)
        explained.set_max_width_chars(56)
        grid.attach(explained, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1

        current = self._secret(words.CURRENT_ADULT_PASSWORD)
        new = self._secret(words.NEW_ADULT_PASSWORD)
        again = self._secret(words.TYPE_IT_AGAIN)

        def save_password(*_args):
            self.run("save_adult_password", current.get_text(), new.get_text(), again.get_text())

        current.connect("activate", lambda *_a: new.grab_focus())
        new.connect("activate", lambda *_a: again.grab_focus())
        again.connect("activate", save_password)
        self._field(grid, words.CURRENT_ADULT_PASSWORD, current, errors.get("current_password"))
        self._field(grid, words.NEW_ADULT_PASSWORD, new, errors.get("adult_password"))
        self._field(grid, words.TYPE_IT_AGAIN, again)
        save = self._button(words.SAVE, save_password, text=self._(words.SAVE))
        save.set_halign(Gtk.Align.START)
        grid.attach(save, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1

        locales = data.get("languages") or []
        codes = [code for code, _ in locales]
        language = self._dropdown([label for _, label in locales],
                                  codes.index(data["language"]) if data.get("language") in codes else 0)
        keyboards = data.get("keyboards") or []
        layouts = [layout for layout, _ in keyboards]
        keyboard = self._dropdown([self._(label) for _, label in keyboards],
                                  layouts.index(data["keyboard"]) if data.get("keyboard") in layouts else 0)
        # The language and the keyboard on one row, so that the page, with
        # the row for a computer left alone, fits 1280x800 whole.
        language_keyboard = Gtk.Box(spacing=12)
        language_keyboard.append(language)
        language_keyboard.append(Gtk.Label(label=self._(words.KEYBOARD),
                                           css_classes=["kidux-field-label"]))
        language_keyboard.append(keyboard)
        self._field(grid, words.LANGUAGE, language_keyboard)

        def language_changed(*_args):
            chosen = language.get_selected()
            if 0 <= chosen < len(codes) and codes[chosen] != data.get("language"):
                self.run("set_language_keyboard", codes[chosen], "")

        def keyboard_changed(*_args):
            chosen = keyboard.get_selected()
            if 0 <= chosen < len(layouts) and layouts[chosen] != data.get("keyboard"):
                self.run("set_language_keyboard", data.get("language"), layouts[chosen])

        language.connect("notify::selected", language_changed)
        keyboard.connect("notify::selected", keyboard_changed)

        scales = list(data.get("scales") or ())
        automatic = data.get("automatic")
        if automatic is None:
            automatic = kidux_screen.automatic_scale(
                *kidux_screen.physical_size(self._window.get_display()))
        mark = self._(words.NOT_PREFERRED_MARK)
        scale = self._dropdown([self._(words.AUTOMATIC).format(size=size_label(automatic, mark))
                                if not s else size_label(s, mark) for s in scales],
                               scales.index(data["scale"]) if data.get("scale") in scales else 0)

        def scale_changed(*_args):
            chosen = scale.get_selected()
            if 0 <= chosen < len(scales) and scales[chosen] != data.get("scale"):
                self.run("set_scale", scales[chosen])

        scale.connect("notify::selected", scale_changed)
        self._field(grid, words.SCREEN_SIZE, scale)
        note = Gtk.Label(label=self._(words.SCALE_NOTE), xalign=0.0, wrap=True,
                         max_width_chars=90, css_classes=["kidux-field-label"])
        grid.attach(note, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1

        # A computer left alone (D67): the minutes before a child's session
        # locks, which the panel's own are too, and before the screen goes
        # off; one row, since the page has room for no more at 1280x800.
        def set_idle(*_args):
            self.run("set_idle", int(lock.get_value()), int(off.get_value()))

        least, most = IDLE_LOCK_RANGE
        lock = self._spin(int(data.get("idle_lock", IDLE_LOCK_MINUTES)), most, set_idle,
                          least=least)
        least, most = SCREEN_OFF_RANGE
        off = self._spin(int(data.get("screen_off", SCREEN_OFF_MINUTES)), most, set_idle,
                         least=least)
        left_alone = Gtk.Box(spacing=8)
        for part in (Gtk.Label(label=self._(words.LOCK_AFTER)), lock,
                     Gtk.Label(label=self._(words.MINUTES_SHORT)),
                     Gtk.Label(label="·"), Gtk.Label(label=self._(words.SCREEN_OFF_AFTER)), off,
                     Gtk.Label(label=self._(words.MINUTES_SHORT)),
                     self._button(words.SET, set_idle, text=self._(words.SET))):
            left_alone.append(part)
        self._field(grid, words.LEFT_ALONE, left_alone)
        # Two pages of their own, the System page having no room left at
        # 1280x800: the hardware's settings, and sleep and the lid (D119).
        advanced = Gtk.Box(spacing=8, halign=Gtk.Align.START)
        advanced.append(self._button(words.ADVANCED_OPEN, self._ask("advanced"),
                                     text=self._(words.ADVANCED_OPEN)))
        advanced.append(self._button(words.POWER_OPEN, self._ask("power"),
                                     text=self._(words.POWER_OPEN)))
        self._field(grid, words.ADVANCED, advanced)
        middle.append(grid)
        self._focus = current

    def _draw_panel_network(self, screen, page, middle, bottom):
        """The machine's network (D62): each connection on a line, the
        router's answer, Look again; and, when NetworkManager manages a
        Wi-Fi, the networks in reach, each with Connect, or its password
        asked for in place, and Forget for one this computer knows."""
        self._adult(page)
        self._tab_bar(page, bottom, "network")
        data = screen.data
        summary = data.get("summary") or {}
        job = summary.get("job", "idle")
        busy = job != "idle"
        grid = self._form()
        grid.set_row_spacing(8)

        lines = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        kinds = {"wifi": words.WIFI, "ethernet": words.CABLE}
        connected = False
        for interface in data.get("interfaces") or []:
            parts = [self._(kinds.get(interface.get("kind"), words.OTHER_CONNECTION))]
            if interface.get("network"):
                parts.append(interface["network"])
            if interface.get("signal", -1) >= 0 and interface.get("kind") == "wifi":
                parts.append(f"{interface['signal']} %")
            if interface.get("address"):
                parts.append(interface["address"])
                connected = True
            else:
                parts.append(self._(words.NOT_CONNECTED))
            lines.append(Gtk.Label(label=" · ".join(parts), xalign=0.0))
        if not connected:
            lines.append(Gtk.Label(label=self._(words.NOT_CONNECTED), xalign=0.0))
        self._field(grid, words.CONNECTION, lines)

        router = Gtk.Box(spacing=12)
        if not summary.get("gateway"):
            said = words.NO_ROUTER
        elif job == "checking" and not summary.get("router"):
            router.append(spinner_small())
            said = words.ROUTER_CHECKING
        else:
            said = {"answers": words.ROUTER_ANSWERS, "silent": words.ROUTER_SILENT}.get(
                summary.get("router"), words.ROUTER_CHECKING)
        router.append(Gtk.Label(label=self._(said), xalign=0.0, wrap=True, max_width_chars=48))
        self._field(grid, words.ROUTER, router)
        look = self._button(words.LOOK_AGAIN, self._ask("refresh_network"),
                            text=self._(words.LOOK_AGAIN))
        look.set_halign(Gtk.Align.START)
        look.set_sensitive(not busy)
        grid.attach(look, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1
        middle.append(grid)

        if summary.get("wifi") and not summary.get("wifi_changeable"):
            middle.append(self._text(words.WIFI_SET_AT_INSTALL))
        if summary.get("wifi_changeable"):
            middle.append(self._heading(words.WIFI_NETWORKS))
            middle.append(self._wifi_networks(data, busy))
            middle.append(self._text(words.NETWORK_CHANGE_NOTE))
        if job == "connecting":
            middle.append(self._row(spinner_small(), Gtk.Label(label=self._(words.CONNECTING))))
        if data.get("failure"):
            middle.append(self._text_as_is(data["failure"]))
        if self._focus is None:
            self._focus = look

    def _wifi_networks(self, data: dict, busy: bool) -> Gtk.Widget:
        """The networks in reach, the one in use first: its name, its signal,
        a padlock when it has a password, and what can be done with it. The
        one whose password is asked for gets the field and Connect in place;
        Forget asks once, under the list."""
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8, halign=Gtk.Align.CENTER)
        networks = data.get("networks") or []
        if not networks:
            box.append(self._text(words.NO_WIFI_IN_REACH))
            return box
        errors = data.get("errors") or {}
        grid = Gtk.Grid(column_spacing=16, row_spacing=8, halign=Gtk.Align.CENTER)
        asked = None
        for number, network in enumerate(networks):
            ssid = network["ssid"]
            name = Gtk.Box(spacing=8, valign=Gtk.Align.CENTER)
            if network.get("secured"):
                name.append(Gtk.Image.new_from_icon_name("changes-prevent-symbolic"))
            label = Gtk.Label(label=ssid, xalign=0.0)
            if network.get("active"):
                label.add_css_class("kidux-module-name")
            name.append(label)
            grid.attach(name, 0, number, 1, 1)
            grid.attach(Gtk.Label(label=f"{network.get('signal', 0)} %", xalign=1.0,
                                  css_classes=["kidux-field-label"]), 1, number, 1, 1)
            actions = Gtk.Box(spacing=8)
            if network.get("active"):
                actions.append(Gtk.Label(label=self._(words.CONNECTED),
                                         css_classes=["kidux-field-label"]))
            elif network.get("security") == "unsupported":
                actions.append(Gtk.Label(label=self._(words.WIFI_UNSUPPORTED),
                                         css_classes=["kidux-field-label"]))
            elif data.get("asking") == ssid:
                entry = Gtk.PasswordEntry(show_peek_icon=True)
                entry.set_property("placeholder-text", self._(words.WIFI_PASSWORD))
                entry.set_size_request(240, -1)

                def send(*_args, ssid=ssid, entry=entry):
                    self.run("connect_wifi", ssid, entry.get_text())

                entry.connect("activate", send)
                actions.append(entry)
                go = self._button(words.CONNECT, send, suggested=True, text=self._(words.CONNECT))
                go.set_sensitive(not busy)
                actions.append(go)
                self._focus = entry
            elif network.get("secured") and not network.get("known"):
                ask = self._button(words.CONNECT, self._ask("ask_wifi_password", ssid),
                                   text=self._(words.CONNECT))
                ask.set_sensitive(not busy)
                actions.append(ask)
            else:
                join = self._button(words.CONNECT, self._ask("connect_wifi", ssid, ""),
                                    text=self._(words.CONNECT))
                join.set_sensitive(not busy)
                actions.append(join)
            if network.get("known"):
                forget = self._button(words.FORGET, self._ask("ask_forget_wifi", ssid),
                                      text=self._(words.FORGET))
                forget.set_sensitive(not busy)
                actions.append(forget)
            if data.get("confirm_forget") == ssid:
                asked = network
            grid.attach(actions, 2, number, 1, 1)
        box.append(grid)
        if errors.get("password"):
            mark = Gtk.Label(label=self._(errors["password"]), wrap=True, max_width_chars=48)
            mark.add_css_class("kidux-field-error")
            box.append(mark)
        if asked is not None:
            box.append(self._text_as_is(
                self._(words.FORGET_WIFI_QUESTION).format(name=asked["ssid"])))
            cancel = self._button(vocabulary.CANCEL, self._ask("tab", "network"))
            self._focus = cancel
            box.append(self._row(cancel, self._button(
                words.FORGET, self._ask("forget_wifi", asked["ssid"]), destructive=True,
                text=self._(words.FORGET))))
        return box

    def _draw_panel_power(self, screen, page, middle, bottom):
        """Sleep and the lid (D119), reached from the System page: what
        closing the lid does, saved when it is chosen; what a computer still
        left alone does and after how many minutes, and Set; only what this
        computer can do, and, when it cannot turn off saving, why."""
        self._adult(page)
        self._tab_bar(page, bottom, "system")
        data = screen.data
        middle.append(self._title(words.POWER))
        middle.append(Gtk.Label(label=self._(words.POWER_EXPLAINED), wrap=True,
                                max_width_chars=70, justify=Gtk.Justification.CENTER))
        grid = self._form()
        labels = {"sleep_then_hibernate": words.POWER_SLEEP_THEN_HIBERNATE,
                  "sleep": words.POWER_SLEEP, "nothing": words.POWER_NOTHING,
                  "screen_off_only": words.POWER_SCREEN_OFF_ONLY}

        lids = list(data.get("lids") or [])
        lid = self._dropdown([self._(labels[action]) for action in lids],
                             lids.index(data["lid"]) if data.get("lid") in lids else 0)
        lid.set_halign(Gtk.Align.START)

        def lid_changed(*_args):
            chosen = lid.get_selected()
            if 0 <= chosen < len(lids) and lids[chosen] != data.get("lid"):
                self.run("set_lid", lids[chosen])

        lid.connect("notify::selected", lid_changed)
        self._field(grid, words.LID_CLOSES, lid, hint=words.LID_HINT)

        idles = list(data.get("idles") or [])
        idle = self._dropdown([self._(labels[action]) for action in idles],
                              idles.index(data["idle"]) if data.get("idle") in idles else 0)

        def set_idle_sleep(*_args):
            chosen = idle.get_selected()
            if 0 <= chosen < len(idles):
                self.run("set_idle_sleep", idles[chosen], int(minutes.get_value()))

        least, most = IDLE_SLEEP_RANGE
        minutes = self._spin(int(data.get("idle_minutes", IDLE_SLEEP_MINUTES)), most,
                             set_idle_sleep, least=least)
        still = Gtk.Box(spacing=8)
        for part in (idle, Gtk.Label(label=self._(words.AFTER)), minutes,
                     Gtk.Label(label=self._(words.MINUTES_SHORT)),
                     self._button(words.SET, set_idle_sleep, text=self._(words.SET))):
            still.append(part)
        self._field(grid, words.STILL_LEFT_ALONE, still)
        hint = Gtk.Label(label=self._(words.LEFT_ALONE_HINT).format(
                             minutes=int(data.get("screen_off", SCREEN_OFF_MINUTES))),
                         xalign=0.0, wrap=True, max_width_chars=60,
                         css_classes=["kidux-field-label"])
        grid.attach(hint, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1
        for message in (words.POWER_WORDS, data.get("reason")):
            if message:
                note = Gtk.Label(label=self._(message), xalign=0.0, wrap=True,
                                 max_width_chars=60, css_classes=["kidux-field-label"])
                grid.attach(note, 1, grid.kidux_rows, 1, 1)
                grid.kidux_rows += 1
        middle.append(grid)
        self._focus = lid

    def _draw_panel_advanced(self, screen, page, middle, bottom):
        """The settings that depend on the machine's hardware (D52), reached
        from the System page: the pointer's speed and the touchpad's scroll,
        each saved when it is chosen, and Chromium's options, one a line,
        and Save."""
        self._adult(page)
        self._tab_bar(page, bottom, "system")
        middle.append(self._title(words.ADVANCED))
        middle.append(Gtk.Label(label=self._(words.ADVANCED_EXPLAINED)))
        grid = self._form()
        steps = [self._(label) for label in words.SPEED_STEPS]
        first = None
        for key, message in (("pointer_speed", words.POINTER_SPEED),
                             ("scroll_speed", words.TWO_FINGER_SCROLL)):
            now = int(screen.data.get(key) or 0)
            # The steps -2 to 2 are the list's places 0 to 4.
            chosen = self._dropdown(steps, now + 2)
            chosen.set_halign(Gtk.Align.START)

            def changed(dropdown, _param, key=key, now=now):
                step = dropdown.get_selected() - 2
                if -2 <= step <= 2 and step != now:
                    self.run("set_pointer", key, step)

            chosen.connect("notify::selected", changed)
            self._field(grid, message, chosen,
                        hint=words.POINTER_EXPLAINED if key == "scroll_speed" else None)
            first = first or chosen
        # Whether the archive's logs count this machine as one machine (D109).
        shared = Gtk.Switch(active=bool(screen.data.get("statistics", True)),
                            halign=Gtk.Align.START, valign=Gtk.Align.CENTER)
        shared.connect("notify::active",
                       lambda widget, _spec: self.run("set_statistics", widget.get_active()))
        self._field(grid, words.SHARE_STATISTICS, shared, hint=words.SHARE_STATISTICS_HINT)
        text = Gtk.TextView(monospace=True, wrap_mode=Gtk.WrapMode.NONE, accepts_tab=False,
                            top_margin=8, bottom_margin=8, left_margin=8, right_margin=8)
        text.get_buffer().set_text(screen.data.get("chromium_flags") or "")
        text.add_css_class("kidux-options")
        # Three lines tall whatever it holds: more lines, or a longer one,
        # scroll inside the box, which shows it (D63).
        frame = Gtk.Frame(child=scroll.scroller(text, expand=False))
        frame.set_size_request(560, 80)
        self._field(grid, words.CHROMIUM_OPTIONS, frame, hint=words.CHROMIUM_OPTIONS_EXPLAINED)
        def save(*_args):
            buffer = text.get_buffer()
            self.run("save_chromium_flags",
                     buffer.get_text(buffer.get_start_iter(), buffer.get_end_iter(), False))

        button = self._button(words.SAVE, save, suggested=True, text=self._(words.SAVE))
        button.set_halign(Gtk.Align.START)
        grid.attach(button, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1
        # The options worth trying, as a list under Save: each in the letters
        # it is typed in, selectable with the pointer to copy it into the
        # box, and what it does beside it. Out of the keyboard's way: Tab goes
        # from the box to Save.
        options = Gtk.Grid(column_spacing=16, row_spacing=6)
        for row, (flag, meaning) in enumerate(words.CHROMIUM_OPTION_LIST):
            typed = Gtk.Label(label=flag, xalign=0.0, yalign=0.0, selectable=True,
                              focusable=False)
            typed.add_css_class("kidux-option")
            options.attach(typed, 0, row, 1, 1)
            options.attach(Gtk.Label(label=self._(meaning), xalign=0.0, yalign=0.0, wrap=True,
                                     max_width_chars=36, css_classes=["kidux-field-label"]),
                           1, row, 1, 1)
        grid.attach(options, 1, grid.kidux_rows, 1, 1)
        grid.kidux_rows += 1
        middle.append(grid)
        self._focus = first
