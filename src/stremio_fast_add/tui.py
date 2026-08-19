"""Curses TUI - the console twin of the tkinter window, for WSL and any headless shell.

Same engine, same per-addon status, no display server and still no dependencies:
`curses` is in the standard library everywhere except Windows, which gets the GUI instead.
"""

from __future__ import annotations

import curses
import locale
import queue
import threading

from . import __version__, api, core, store

HELP = "j/k or arrows move  space pick  a all  n none  c sign in  i install  d dry-run  r replace  e export  q quit"
STATUS_TEXT = {
    core.PENDING: "waiting",
    core.CHECKING: "checking",
    core.OK: "installed",
    core.ALREADY: "already there",
    core.FAILED: "failed",
    core.SKIPPED: "skipped",
}

C_NORMAL, C_ACCENT, C_MUTED, C_OK, C_WARN, C_ERR, C_BAR = range(1, 8)
STATUS_COLOR = {
    core.PENDING: C_MUTED,
    core.CHECKING: C_WARN,
    core.OK: C_OK,
    core.ALREADY: C_ACCENT,
    core.FAILED: C_ERR,
    core.SKIPPED: C_MUTED,
}


class Tui:
    def __init__(self, stdscr, source: str | None = None) -> None:
        self.scr = stdscr
        self.source = source
        self.auth_key: str | None = None
        self.account_email = ""
        self.account_addons: list[api.Addon] = []
        self.results: list[core.AddonResult] = []
        self.origin = "(loading)"
        self.cursor = 0
        self.top = 0
        self.busy = False
        self.replace = False
        self.dry_run = False
        self.message = "sign in to the target account to begin"
        self.message_color = C_MUTED
        self.events: queue.Queue = queue.Queue()

    # ------------------------------------------------------------- plumbing

    def say(self, text: str, color: int = C_MUTED) -> None:
        self.message, self.message_color = text, color

    def _in_thread(self, work, done=None) -> None:
        if self.busy:
            return
        self.busy = True

        def runner() -> None:
            try:
                self.events.put(("done", (done, work(), None)))
            except Exception as exc:  # noqa: BLE001 - shown in the status line, never a crash
                self.events.put(("done", (done, None, exc)))

        threading.Thread(target=runner, daemon=True).start()

    def _drain(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "say":
                    self.say(*payload)
                elif kind == "done":
                    callback, value, error = payload
                    self.busy = False
                    if error is not None:
                        self.say(str(error), C_ERR)
                    elif callback is not None:
                        callback(value)
        except queue.Empty:
            pass

    # ---------------------------------------------------------------- input

    def prompt(self, label: str, mask: bool = False) -> str:
        """A one-line editor drawn on the last row. Esc aborts."""
        height, width = self.scr.getmaxyx()
        buffer = ""
        curses.curs_set(1)
        try:
            while True:
                shown = "*" * len(buffer) if mask else buffer
                line = f"{label}{shown}"[: width - 2]
                self.scr.move(height - 1, 0)
                self.scr.clrtoeol()
                self.scr.addstr(height - 1, 0, line, curses.color_pair(C_ACCENT))
                self.scr.refresh()
                key = self.scr.getch()
                if key in (curses.KEY_ENTER, 10, 13):
                    return buffer
                if key == 27:  # Esc
                    return ""
                if key in (curses.KEY_BACKSPACE, 127, 8):
                    buffer = buffer[:-1]
                elif 32 <= key < 127:
                    buffer += chr(key)
        finally:
            curses.curs_set(0)
            self.scr.move(height - 1, 0)
            self.scr.clrtoeol()

    # ----------------------------------------------------------------- draw

    def _put(self, row: int, col: int, text: str, color: int = C_NORMAL, bold: bool = False) -> None:
        height, width = self.scr.getmaxyx()
        if not (0 <= row < height) or col >= width:
            return
        attr = curses.color_pair(color) | (curses.A_BOLD if bold else 0)
        try:
            self.scr.addstr(row, col, text[: width - col - 1], attr)
        except curses.error:  # bottom-right corner writes always raise
            pass

    def draw(self) -> None:
        self.scr.erase()
        height, width = self.scr.getmaxyx()

        self._put(0, 0, "Stremio Fast Add", C_ACCENT, bold=True)
        self._put(0, 17, f"v{__version__}  clone a whole addon setup into any account", C_MUTED)

        if self.auth_key:
            self._put(2, 0, "account", C_MUTED)
            self._put(2, 10, f"{self.account_email}", C_OK)
            self._put(2, 10 + len(self.account_email) + 2,
                      f"- {len(self.account_addons)} addons in this account", C_MUTED)
        else:
            self._put(2, 0, "account", C_MUTED)
            self._put(2, 10, "not connected  -  press c to sign in", C_WARN)

        self._put(3, 0, "profile", C_MUTED)
        self._put(3, 10, f"{len(self.results)} addons from {self.origin}"[: width - 12], C_NORMAL)

        modes = []
        if self.dry_run:
            modes.append("DRY RUN")
        if self.replace:
            modes.append("REPLACE")
        if modes:
            self._put(3, width - len(" ".join(modes)) - 2, " ".join(modes), C_WARN, bold=True)

        # table
        head_row = 5
        self._put(head_row, 0, "   addon", C_MUTED, bold=True)
        self._put(head_row, 36, "provides", C_MUTED, bold=True)
        self._put(head_row, 52, "status", C_MUTED, bold=True)
        self._put(head_row, 68, "details", C_MUTED, bold=True)

        first = head_row + 1
        rows = max(1, height - first - 4)
        if self.cursor < self.top:
            self.top = self.cursor
        elif self.cursor >= self.top + rows:
            self.top = self.cursor - rows + 1

        for offset in range(rows):
            index = self.top + offset
            if index >= len(self.results):
                break
            result = self.results[index]
            row = first + offset
            selected = index == self.cursor
            if selected:
                self._put(row, 0, " " * (width - 1), C_BAR)
            base = C_BAR if selected else C_NORMAL
            self._put(row, 0, " >" if selected else "  ", C_ACCENT if not selected else C_BAR)
            self._put(row, 3, "[x]" if result.selected else "[ ]", base)
            self._put(row, 7, result.name[:28], base)
            self._put(row, 36, result.kinds[:15], C_MUTED if not selected else C_BAR)
            self._put(row, 52, STATUS_TEXT[result.status],
                      STATUS_COLOR[result.status] if not selected else C_BAR)
            self._put(row, 68, result.message[: max(0, width - 69)],
                      C_MUTED if not selected else C_BAR)

        # footer
        summary = core.summarize(self.results)
        chosen = sum(1 for r in self.results if r.selected)
        self._put(height - 3, 0, f"{chosen} selected", C_MUTED)
        self._put(height - 3, 14, f"+ {summary.installed} installed", C_OK)
        self._put(height - 3, 32, f"= {summary.already} already", C_ACCENT)
        self._put(height - 3, 48, f"! {summary.failed} failed", C_ERR)
        self._put(height - 3, 62, f"- {summary.skipped} skipped", C_MUTED)
        self._put(height - 2, 0, self.message[: width - 1], self.message_color)
        self._put(height - 1, 0, HELP[: width - 1], C_MUTED)
        self.scr.refresh()

    # -------------------------------------------------------------- actions

    def load_profile(self) -> None:
        try:
            profile = store.load(self.source)
        except Exception as exc:  # noqa: BLE001
            self.origin = "(none)"
            self.say(f"could not load a profile: {exc}", C_ERR)
            return
        self.results = core.make_results(profile.addons)
        self.origin = profile.origin
        self._mark_existing()
        self.say(f"loaded {len(self.results)} addons", C_MUTED)

    def _mark_existing(self) -> None:
        existing = {api.addon_key(a) for a in self.account_addons}
        for result in self.results:
            if result.status != core.PENDING:
                continue
            if result.key in existing:
                result.status, result.message = core.ALREADY, "already in this account"
            elif api.has_embedded_config(result.addon):
                result.message = "carries personal config in its URL"

    def connect(self) -> None:
        if self.auth_key:
            self.auth_key = None
            self.account_addons = []
            self.account_email = ""
            for result in self.results:
                result.status, result.message = core.PENDING, ""
            self._mark_existing()
            self.say("signed out", C_MUTED)
            return

        use_key = self.prompt("auth key (leave empty to use email+password): ", mask=True)
        if use_key:
            def work():
                return use_key, api.get_addons(use_key), api.whoami(use_key)
        else:
            email = self.prompt("email: ")
            if not email:
                self.say("cancelled", C_MUTED)
                return
            password = self.prompt("password: ", mask=True)
            if not password:
                self.say("cancelled", C_MUTED)
                return

            def work():
                key = api.login(email, password)
                return key, api.get_addons(key), email

        self.say("connecting to Stremio...", C_WARN)
        self._in_thread(work, self._connected)

    def _connected(self, value) -> None:
        self.auth_key, self.account_addons, self.account_email = value
        self._mark_existing()
        self.say(f"connected as {self.account_email}", C_OK)

    def install(self) -> None:
        if not self.auth_key:
            self.say("sign in first - press c", C_WARN)
            return
        if not any(r.selected for r in self.results):
            self.say("nothing selected", C_WARN)
            return

        auth_key, replace, dry = self.auth_key, self.replace, self.dry_run
        results = self.results
        for result in results:
            result.status = core.PENDING if result.selected else core.SKIPPED
            result.message = "" if result.selected else "not selected"

        def work():
            existing = api.get_addons(auth_key)
            core.check_all(results, {api.addon_key(a) for a in existing},
                           on_update=lambda _r: None)
            summary = core.summarize(results)
            if dry:
                return summary, len(existing), True
            if not any(r.status == core.OK for r in results) and not replace:
                return summary, len(existing), False
            collection = core.merge(existing, results, replace=replace)
            core.push(auth_key, collection)
            return summary, len(collection), False

        self.say("checking every addon, then writing the collection...", C_WARN)
        self._in_thread(work, self._installed)

    def _installed(self, value) -> None:
        summary, total, was_dry = value
        head = "dry run - nothing written" if was_dry else f"account now has {total} addons"
        detail = (f"{head}  |  {summary.installed} installed, {summary.already} already there, "
                  f"{summary.failed} failed")
        self.say(detail, C_ERR if summary.failed else C_OK)
        self.account_addons = []

    def export(self) -> None:
        if not self.auth_key:
            self.say("sign in first - press c", C_WARN)
            return
        default = store.default_save_path()
        target = self.prompt(f"save to [{default}]: ") or str(default)
        auth_key = self.auth_key

        def work():
            addons = api.get_addons(auth_key)
            path = store.save(addons, target, name="Stremio addons")
            private = [api.addon_name(a) for a in addons if api.has_embedded_config(a)]
            return path, len(addons), private

        self._in_thread(work, self._exported)

    def _exported(self, value) -> None:
        path, count, private = value
        if private:
            self.say(f"exported {count} addons -> {path}  |  personal config in: "
                     + ", ".join(private), C_WARN)
        else:
            self.say(f"exported {count} addons -> {path}", C_OK)
        self.source = str(path)
        self.load_profile()

    # ----------------------------------------------------------------- loop

    def run(self) -> None:
        curses.curs_set(0)
        self.scr.timeout(120)
        self.load_profile()
        while True:
            self._drain()
            self.draw()
            key = self.scr.getch()
            if key == -1:
                continue
            if self.busy and key not in (ord("q"),):
                continue
            if key in (ord("q"), ord("Q")):
                return
            if key in (curses.KEY_DOWN, ord("j")):
                self.cursor = min(self.cursor + 1, max(0, len(self.results) - 1))
            elif key in (curses.KEY_UP, ord("k")):
                self.cursor = max(self.cursor - 1, 0)
            elif key == curses.KEY_NPAGE:
                self.cursor = min(self.cursor + 10, max(0, len(self.results) - 1))
            elif key == curses.KEY_PPAGE:
                self.cursor = max(self.cursor - 10, 0)
            elif key == ord(" ") and self.results:
                target = self.results[self.cursor]
                target.selected = not target.selected
            elif key in (ord("a"), ord("A")):
                for result in self.results:
                    result.selected = True
            elif key in (ord("n"), ord("N")):
                for result in self.results:
                    result.selected = False
            elif key in (ord("c"), ord("C")):
                self.connect()
            elif key in (ord("i"), ord("I")):
                self.install()
            elif key in (ord("e"), ord("E")):
                self.export()
            elif key in (ord("d"), ord("D")):
                self.dry_run = not self.dry_run
                self.say(f"dry run {'on' if self.dry_run else 'off'}", C_MUTED)
            elif key in (ord("r"), ord("R")):
                self.replace = not self.replace
                self.say(f"replace {'on - protected addons are kept' if self.replace else 'off'}",
                         C_WARN if self.replace else C_MUTED)


def _boot(stdscr, source: str | None) -> None:
    curses.start_color()
    curses.use_default_colors()
    for pair, fg in (
        (C_NORMAL, curses.COLOR_WHITE),
        (C_ACCENT, curses.COLOR_MAGENTA),
        (C_MUTED, curses.COLOR_CYAN),
        (C_OK, curses.COLOR_GREEN),
        (C_WARN, curses.COLOR_YELLOW),
        (C_ERR, curses.COLOR_RED),
    ):
        curses.init_pair(pair, fg, -1)
    curses.init_pair(C_BAR, curses.COLOR_BLACK, curses.COLOR_MAGENTA)
    Tui(stdscr, source).run()


def run(source: str | None = None) -> int:
    locale.setlocale(locale.LC_ALL, "")
    curses.wrapper(_boot, source)
    return 0
