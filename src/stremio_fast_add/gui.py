"""Tkinter GUI: sign in, pick addons, install, and see exactly what worked."""

from __future__ import annotations

import queue
import threading
from pathlib import Path
from urllib.parse import urlsplit
from tkinter import Tk, StringVar, BooleanVar, IntVar, Text, END, DISABLED, NORMAL, filedialog, messagebox
from tkinter import ttk

from . import __version__, api, core, store

BG = "#0f1116"
PANEL = "#181c26"
PANEL_2 = "#1f2432"
FG = "#e7eaf3"
MUTED = "#8b93a7"
ACCENT = "#8c5cff"
ACCENT_HI = "#a37bff"
OK_C = "#3ddc97"
WARN_C = "#ffc857"
ERR_C = "#ff5c72"

CHECKED = "■"
UNCHECKED = "□"

STATUS_COLOR = {
    core.PENDING: MUTED,
    core.CHECKING: WARN_C,
    core.OK: OK_C,
    core.ALREADY: ACCENT_HI,
    core.FAILED: ERR_C,
    core.SKIPPED: MUTED,
}
STATUS_TEXT = {
    core.PENDING: "waiting",
    core.CHECKING: "checking",
    core.OK: "installed",
    core.ALREADY: "already there",
    core.FAILED: "failed",
    core.SKIPPED: "skipped",
}


def _enable_dpi_awareness() -> None:
    try:  # Windows: keeps the window crisp on scaled displays
        import ctypes

        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:  # noqa: BLE001 - purely cosmetic
        pass


class App(Tk):
    def __init__(self, source: str | None = None) -> None:
        super().__init__()
        self.title("Stremio Fast Add  v" + __version__)
        self.geometry("980x760")
        self.minsize(880, 660)
        self.configure(bg=BG)

        self.source = source
        self.auth_key: str | None = None
        self.account_email: str = ""
        self.account_addons: list[api.Addon] = []
        self.results: list[core.AddonResult] = []
        self.row_of: dict[str, core.AddonResult] = {}
        self.iid_of: dict[str, str] = {}
        self.busy = False
        self.events: queue.Queue = queue.Queue()

        self._build_style()
        self._build_ui()
        self.after(60, self._drain_events)
        self.after(120, lambda: self._load_profile(self.source))

    # ---------------------------------------------------------------- style

    def _build_style(self) -> None:
        style = ttk.Style(self)
        style.theme_use("clam")
        base = ("Segoe UI", 10)
        style.configure(".", background=BG, foreground=FG, font=base)
        style.configure("TFrame", background=BG)
        style.configure("Card.TFrame", background=PANEL)
        style.configure("TLabel", background=PANEL, foreground=FG)
        style.configure("Muted.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("MutedBg.TLabel", background=BG, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Title.TLabel", background=BG, foreground=FG, font=("Segoe UI Semibold", 20))
        style.configure("Step.TLabel", background=PANEL, foreground=ACCENT_HI, font=("Segoe UI Semibold", 11))
        style.configure("Head.TLabel", background=PANEL, foreground=FG, font=("Segoe UI Semibold", 11))
        style.configure("TCheckbutton", background=PANEL, foreground=FG)
        style.configure("TRadiobutton", background=PANEL, foreground=FG)
        style.map("TCheckbutton", background=[("active", PANEL)])
        style.map("TRadiobutton", background=[("active", PANEL)])
        style.configure("TEntry", fieldbackground=PANEL_2, foreground=FG, insertcolor=FG, borderwidth=0)
        style.configure("TButton", background=PANEL_2, foreground=FG, borderwidth=0, padding=(12, 7))
        style.map(
            "TButton",
            background=[("active", "#2b3245"), ("disabled", "#171b24")],
            foreground=[("disabled", MUTED)],
        )
        style.configure(
            "Accent.TButton", background=ACCENT, foreground="#ffffff",
            font=("Segoe UI Semibold", 11), padding=(18, 10),
        )
        style.map(
            "Accent.TButton",
            background=[("active", ACCENT_HI), ("disabled", "#3a3350")],
            foreground=[("disabled", "#9b93b5")],
        )
        style.configure(
            "Treeview", background=PANEL_2, fieldbackground=PANEL_2, foreground=FG,
            rowheight=27, borderwidth=0,
        )
        style.configure(
            "Treeview.Heading", background=PANEL, foreground=MUTED,
            font=("Segoe UI Semibold", 9), borderwidth=0, padding=(6, 6),
        )
        style.map("Treeview", background=[("selected", "#2f2a45")], foreground=[("selected", FG)])
        style.map("Treeview.Heading", background=[("active", PANEL)])
        style.configure("TProgressbar", background=ACCENT, troughcolor=PANEL_2, borderwidth=0, thickness=8)

    # ------------------------------------------------------------------- ui

    def _card(self, parent, step: str, title: str) -> ttk.Frame:
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        head = ttk.Frame(card, style="Card.TFrame")
        head.pack(fill="x")
        ttk.Label(head, text=step, style="Step.TLabel").pack(side="left")
        ttk.Label(head, text=title, style="Head.TLabel").pack(side="left", padx=(8, 0))
        return card

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=(18, 14))
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 12))
        ttk.Label(header, text="Stremio Fast Add", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="clone a whole addon setup into any account", style="MutedBg.TLabel").pack(
            side="left", padx=(12, 0), pady=(9, 0)
        )

        self._build_account(root)
        self._build_addons(root)
        self._build_actions(root)
        self._build_log(root)

    def _build_account(self, parent) -> None:
        card = self._card(parent, "1", "Sign in to the target Stremio account")
        card.pack(fill="x", pady=(0, 10))

        self.mode = StringVar(value="password")
        modes = ttk.Frame(card, style="Card.TFrame")
        modes.pack(fill="x", pady=(10, 6))
        ttk.Radiobutton(
            modes, text="Email + password", value="password", variable=self.mode, command=self._sync_mode
        ).pack(side="left")
        ttk.Radiobutton(
            modes, text="Auth key", value="authkey", variable=self.mode, command=self._sync_mode
        ).pack(side="left", padx=(16, 0))

        self.form = ttk.Frame(card, style="Card.TFrame")
        self.form.pack(fill="x")
        self.email = StringVar()
        self.password = StringVar()
        self.authkey_in = StringVar()

        self.pw_row = ttk.Frame(self.form, style="Card.TFrame")
        ttk.Label(self.pw_row, text="Email").pack(side="left")
        ttk.Entry(self.pw_row, textvariable=self.email, width=30).pack(side="left", padx=(8, 16))
        ttk.Label(self.pw_row, text="Password").pack(side="left")
        pw = ttk.Entry(self.pw_row, textvariable=self.password, show="•", width=24)
        pw.pack(side="left", padx=(8, 0))
        pw.bind("<Return>", lambda _e: self.connect())

        self.key_row = ttk.Frame(self.form, style="Card.TFrame")
        ttk.Label(self.key_row, text="Auth key").pack(side="left")
        key_entry = ttk.Entry(self.key_row, textvariable=self.authkey_in, width=58, show="•")
        key_entry.pack(side="left", padx=(8, 0))
        key_entry.bind("<Return>", lambda _e: self.connect())

        actions = ttk.Frame(card, style="Card.TFrame")
        actions.pack(fill="x", pady=(12, 0))
        self.connect_btn = ttk.Button(actions, text="Connect", command=self.connect)
        self.connect_btn.pack(side="left")
        self.copy_key_btn = ttk.Button(actions, text="Copy auth key", command=self._copy_auth_key, state=DISABLED)
        self.copy_key_btn.pack(side="left", padx=(8, 0))
        self.account_lbl = ttk.Label(actions, text="●  not connected", style="Muted.TLabel")
        self.account_lbl.pack(side="left", padx=(14, 0))
        self._sync_mode()

    def _build_addons(self, parent) -> None:
        card = self._card(parent, "2", "Addons to install")
        card.pack(fill="both", expand=True, pady=(0, 10))

        bar = ttk.Frame(card, style="Card.TFrame")
        bar.pack(fill="x", pady=(10, 8))
        self.source_lbl = ttk.Label(bar, text="loading profile...", style="Muted.TLabel")
        self.source_lbl.pack(side="left")
        ttk.Button(bar, text="From URL", command=self._load_from_url).pack(side="right")
        ttk.Button(bar, text="From file", command=self._load_from_file).pack(side="right", padx=(0, 6))
        ttk.Button(bar, text="None", command=lambda: self._select_all(False)).pack(side="right", padx=(0, 6))
        ttk.Button(bar, text="All", command=lambda: self._select_all(True)).pack(side="right", padx=(0, 6))

        holder = ttk.Frame(card, style="Card.TFrame")
        holder.pack(fill="both", expand=True)
        columns = ("kind", "state", "detail")
        self.tree = ttk.Treeview(holder, columns=columns, show="tree headings", selectmode="browse")
        self.tree.heading("#0", text="  addon")
        self.tree.heading("kind", text="provides")
        self.tree.heading("state", text="status")
        self.tree.heading("detail", text="details")
        self.tree.column("#0", width=330, minwidth=200, stretch=True)
        self.tree.column("kind", width=140, minwidth=90, stretch=False)
        self.tree.column("state", width=120, minwidth=90, stretch=False, anchor="w")
        self.tree.column("detail", width=300, minwidth=140, stretch=True)
        scroll = ttk.Scrollbar(holder, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        for status, color in STATUS_COLOR.items():
            self.tree.tag_configure(status, foreground=color)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<space>", lambda _e: self._toggle(self.tree.focus()))
        self.tree.bind("<Double-1>", lambda _e: "break")

    def _build_actions(self, parent) -> None:
        card = ttk.Frame(parent, style="Card.TFrame", padding=14)
        card.pack(fill="x", pady=(0, 10))

        row = ttk.Frame(card, style="Card.TFrame")
        row.pack(fill="x")
        self.install_btn = ttk.Button(
            row, text="Install selected addons", style="Accent.TButton", command=self.install
        )
        self.install_btn.pack(side="left")
        ttk.Button(row, text="Export my addons", command=self.export).pack(side="left", padx=(10, 0))

        self.replace = BooleanVar(value=False)
        self.dry_run = BooleanVar(value=False)
        ttk.Checkbutton(row, text="Replace existing collection", variable=self.replace).pack(
            side="right", padx=(12, 0)
        )
        ttk.Checkbutton(row, text="Dry run (check only)", variable=self.dry_run).pack(side="right")

        prog = ttk.Frame(card, style="Card.TFrame")
        prog.pack(fill="x", pady=(12, 0))
        self.progress_val = IntVar(value=0)
        self.progress = ttk.Progressbar(prog, variable=self.progress_val, maximum=100)
        self.progress.pack(fill="x")
        self.counts = ttk.Label(prog, text="ready", style="Muted.TLabel")
        self.counts.pack(anchor="w", pady=(6, 0))

    def _build_log(self, parent) -> None:
        frame = ttk.Frame(parent)
        frame.pack(fill="x")
        self.log_box = Text(
            frame, height=7, bg=PANEL_2, fg=MUTED, insertbackground=FG, relief="flat",
            font=("Consolas", 9), wrap="word", padx=10, pady=8,
        )
        self.log_box.pack(fill="x")
        self.log_box.tag_configure("ok", foreground=OK_C)
        self.log_box.tag_configure("err", foreground=ERR_C)
        self.log_box.tag_configure("info", foreground=FG)
        self.log_box.configure(state=DISABLED)
        self.log("Stremio Fast Add ready. Sign in, then hit Install.", "info")

    # -------------------------------------------------------------- helpers

    def log(self, message: str, tag: str = "") -> None:
        self.log_box.configure(state=NORMAL)
        self.log_box.insert(END, message.rstrip() + "\n", tag)
        self.log_box.see(END)
        self.log_box.configure(state=DISABLED)

    def _sync_mode(self) -> None:
        self.pw_row.pack_forget()
        self.key_row.pack_forget()
        (self.pw_row if self.mode.get() == "password" else self.key_row).pack(fill="x")

    def _set_busy(self, busy: bool) -> None:
        self.busy = busy
        state = DISABLED if busy else NORMAL
        self.install_btn.configure(state=state)
        self.connect_btn.configure(state=state)
        self.configure(cursor="watch" if busy else "")

    def _in_thread(self, work, done=None) -> None:
        """Run network work off the UI thread; results come back through the event queue."""
        if self.busy:
            return
        self._set_busy(True)

        def runner() -> None:
            try:
                value = work()
                self.events.put(("done", (done, value, None)))
            except Exception as exc:  # noqa: BLE001 - surfaced in the log, never a crash
                self.events.put(("done", (done, None, exc)))

        threading.Thread(target=runner, daemon=True).start()

    def _drain_events(self) -> None:
        try:
            while True:
                kind, payload = self.events.get_nowait()
                if kind == "row":
                    self._paint_row(payload)
                elif kind == "log":
                    self.log(*payload)
                elif kind == "done":
                    callback, value, error = payload
                    self._set_busy(False)
                    if error is not None:
                        self.log("[x] " + str(error), "err")
                        if not isinstance(error, api.StremioError):
                            self.log("    " + type(error).__name__, "err")
                        messagebox.showerror("Stremio Fast Add", str(error))
                    elif callback is not None:
                        callback(value)
        except queue.Empty:
            pass
        self.after(60, self._drain_events)

    # ------------------------------------------------------------- profiles

    def _load_profile(self, source: str | None) -> None:
        try:
            profile = store.load(source)
        except Exception as exc:  # noqa: BLE001
            self.source_lbl.configure(text="no profile loaded")
            self.log("[x] could not load an addon profile: " + str(exc), "err")
            self.log("    Use 'From file' / 'From URL', or export from the account you want to clone.")
            return
        self._apply_profile(profile)

    def _load_from_file(self) -> None:
        path = filedialog.askopenfilename(
            title="Pick an addon profile", filetypes=[("JSON", "*.json"), ("All files", "*.*")]
        )
        if path:
            self.source = path
            self._load_profile(path)

    def _load_from_url(self) -> None:
        from tkinter.simpledialog import askstring

        url = askstring("Load from URL", "Raw URL of an addons.json:", parent=self)
        if url:
            self.source = url.strip()
            self._in_thread(lambda: store.load(self.source), self._apply_profile)

    def _apply_profile(self, profile: store.Profile) -> None:
        self.results = core.make_results(profile.addons)
        origin = profile.origin
        if len(origin) > 72:
            origin = "..." + origin[-69:]
        stamp = "  -  exported " + profile.exported_at[:10] if profile.exported_at else ""
        self.source_lbl.configure(text=f"{len(self.results)} addons from {origin}{stamp}")
        self._refill_tree()
        self.log(f"loaded {len(self.results)} addons from {profile.origin}", "info")

    # ----------------------------------------------------------------- tree

    def _refill_tree(self) -> None:
        self.tree.delete(*self.tree.get_children())
        self.row_of.clear()
        self.iid_of.clear()
        existing = {api.addon_key(a) for a in self.account_addons}
        for result in self.results:
            if result.key in existing and result.status == core.PENDING:
                result.status, result.message = core.ALREADY, "already in this account"
            elif result.status == core.PENDING and api.has_embedded_config(result.addon):
                result.message = "carries personal config in its URL"
            elif result.status == core.PENDING and not result.message:
                result.message = urlsplit(result.url).netloc
            iid = self.tree.insert(
                "", "end",
                text=f" {CHECKED if result.selected else UNCHECKED}  {result.name}",
                values=(result.kinds, STATUS_TEXT[result.status], result.message),
                tags=(result.status,),
            )
            self.row_of[iid] = result
            self.iid_of[result.key] = iid
        self._paint_progress()

    def _paint_row(self, result: core.AddonResult) -> None:
        iid = self.iid_of.get(result.key)
        if not iid or not self.tree.exists(iid):
            return
        self.tree.item(
            iid,
            text=f" {CHECKED if result.selected else UNCHECKED}  {result.name}",
            values=(result.kinds, STATUS_TEXT[result.status], result.message),
            tags=(result.status,),
        )
        self._paint_progress()

    def _paint_progress(self) -> None:
        summary = core.summarize(self.results)
        total = len(self.results)
        done = summary.installed + summary.already + summary.failed + summary.skipped
        self.progress_val.set(int(100 * done / total) if total else 0)
        selected = sum(1 for r in self.results if r.selected)
        self.counts.configure(
            text=(
                f"{selected} selected   |   {core.BADGE[core.OK]} {summary.installed} installed   "
                f"{core.BADGE[core.ALREADY]} {summary.already} already there   "
                f"{core.BADGE[core.FAILED]} {summary.failed} failed   "
                f"{core.BADGE[core.SKIPPED]} {summary.skipped} skipped"
            )
        )

    def _on_tree_click(self, event) -> None:
        if self.tree.identify_region(event.x, event.y) != "tree":
            return
        self._toggle(self.tree.identify_row(event.y))

    def _toggle(self, iid: str) -> None:
        result = self.row_of.get(iid)
        if not result or self.busy:
            return
        result.selected = not result.selected
        self._paint_row(result)

    def _select_all(self, value: bool) -> None:
        if self.busy:
            return
        for result in self.results:
            result.selected = value
            self._paint_row(result)

    # -------------------------------------------------------------- account

    def connect(self) -> None:
        if self.auth_key:  # the button doubles as sign-out once connected
            self.auth_key = None
            self.account_addons = []
            self.account_email = ""
            self.connect_btn.configure(text="Connect")
            self.copy_key_btn.configure(state=DISABLED)
            self.account_lbl.configure(text="●  not connected")
            self.log("signed out", "info")
            self._refill_tree()
            return

        if self.mode.get() == "password":
            email, password = self.email.get().strip(), self.password.get()
            if not email or not password:
                messagebox.showwarning("Stremio Fast Add", "Enter the account email and password.")
                return

            def work():
                key = api.login(email, password)
                return key, api.get_addons(key), email

        else:
            key_in = self.authkey_in.get().strip()
            if not key_in:
                messagebox.showwarning("Stremio Fast Add", "Paste an auth key first.")
                return

            def work():
                who = api.whoami(key_in)
                return key_in, api.get_addons(key_in), who

        self.log("connecting to Stremio...", "info")
        self._in_thread(work, self._on_connected)

    def _on_connected(self, value) -> None:
        self.auth_key, self.account_addons, self.account_email = value
        self.connect_btn.configure(text="Sign out")
        self.copy_key_btn.configure(state=NORMAL)
        self.account_lbl.configure(
            text=f"●  {self.account_email}  -  {len(self.account_addons)} addons in this account"
        )
        self.log(f"[v] connected as {self.account_email} ({len(self.account_addons)} addons)", "ok")
        self._refill_tree()

    def _copy_auth_key(self) -> None:
        if not self.auth_key:
            return
        self.clipboard_clear()
        self.clipboard_append(self.auth_key)
        self.log("auth key copied to clipboard - it works instead of a password", "info")

    # -------------------------------------------------------------- actions

    def install(self) -> None:
        if not self.auth_key:
            messagebox.showwarning("Stremio Fast Add", "Sign in to the target account first.")
            return
        chosen = [r for r in self.results if r.selected]
        if not chosen:
            messagebox.showwarning("Stremio Fast Add", "Nothing is selected.")
            return
        if self.replace.get() and not messagebox.askyesno(
            "Replace collection?",
            f"This drops the addons currently on {self.account_email} "
            "(Stremio's protected ones are kept) and installs the selected ones instead.\n\nContinue?",
        ):
            return

        auth_key = self.auth_key
        replace = self.replace.get()
        dry = self.dry_run.get()
        results = self.results
        for result in results:
            result.status = core.PENDING if result.selected else core.SKIPPED
            result.message = "" if result.selected else "not selected"
            self.events.put(("row", result))

        def work():
            existing = api.get_addons(auth_key)
            existing_keys = {api.addon_key(a) for a in existing}
            core.check_all(results, existing_keys, on_update=lambda r: self.events.put(("row", r)))
            summary = core.summarize(results)
            if dry:
                self.events.put(("log", ("dry run - nothing was written to the account", "info")))
                return summary, len(existing)
            ready = [r for r in results if r.status == core.OK]
            if not ready and not replace:
                self.events.put(("log", ("nothing new to install", "info")))
                return summary, len(existing)
            collection = core.merge(existing, results, replace=replace)
            core.push(auth_key, collection)
            summary.total_after = len(collection)
            return summary, len(collection)

        self.log(f"installing {len(chosen)} addons into {self.account_email}...", "info")
        self._in_thread(work, self._on_installed)

    def _on_installed(self, value) -> None:
        summary, total = value
        for result in self.results:
            self._paint_row(result)
        self.log(
            f"{core.BADGE[core.OK]} {summary.installed} installed   "
            f"{core.BADGE[core.ALREADY]} {summary.already} already there   "
            f"{core.BADGE[core.FAILED]} {summary.failed} failed   "
            f"{core.BADGE[core.SKIPPED]} {summary.skipped} skipped   ->  {total} addons in the account",
            "err" if summary.failed else "ok",
        )
        for failure in summary.failures:
            self.log(f"    [x] {failure.name}: {failure.message}", "err")
        if summary.failed:
            self.log("    failed addons are usually offline, or need their own configured URL.", "err")
        if not self.dry_run.get():
            self.log("    restart Stremio (or reload the web app) to see them.", "info")
        messagebox.showinfo(
            "Stremio Fast Add",
            f"Installed: {summary.installed}\nAlready there: {summary.already}\n"
            f"Failed: {summary.failed}\nSkipped: {summary.skipped}\n\n"
            f"The account now has {total} addons.",
        )

    def export(self) -> None:
        if not self.auth_key:
            messagebox.showwarning("Stremio Fast Add", "Sign in to the account you want to export first.")
            return
        default = store.default_save_path()
        path = filedialog.asksaveasfilename(
            title="Save addon profile",
            initialdir=str(default.parent),
            initialfile=default.name,
            defaultextension=".json",
            filetypes=[("JSON", "*.json")],
        )
        if not path:
            return
        auth_key, email = self.auth_key, self.account_email

        def work():
            addons = api.get_addons(auth_key)
            saved = store.save(addons, path, name="Stremio addons")
            return saved, addons

        self._in_thread(work, self._on_exported)

    def _on_exported(self, value) -> None:
        path, addons = value
        count = len(addons)
        self.log(f"[v] exported {count} addons -> {path}", "ok")
        private = [api.addon_name(a) for a in addons if api.has_embedded_config(a)]
        if private:
            self.log(f"[!] {len(private)} addons carry personal config in their URL:", "err")
            for name in private:
                self.log("    - " + name, "err")
            messagebox.showwarning(
                "Personal config inside these addons",
                "These addons store your own settings in their URL - Trakt tokens, debrid or API "
                "keys, private lists:\n\n  "
                + "\n  ".join(private)
                + "\n\nSharing this profile publicly shares those keys. Remove them from the JSON "
                "(or let your friend configure their own) before you push it anywhere.",
            )
        if Path(path).name == "default.json":
            self.log("    commit and push it - 'uvx --from git+<repo> stremio-fast-add' then ships it to friends.")
        self.source = str(path)
        self._load_profile(str(path))


def run(source: str | None = None) -> int:
    _enable_dpi_awareness()
    App(source).mainloop()
    return 0
