"""Entry point. Picks a front end - window, console UI, or plain output - and runs it."""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from . import __version__, api, core, store

EPILOG = """\
front end:
  a desktop window on Windows and macOS, a console UI in any Linux/WSL/SSH
  terminal, plain output when there is neither. --gui/--tui/--cli override.

examples:
  uvx --from https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD/archive/refs/heads/main.zip stremio-fast-add
  uv run stremio-fast-add --export
  uv run stremio-fast-add --tui
  uv run stremio-fast-add --cli --dry-run
"""


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="stremio-fast-add",
        description="Clone a whole Stremio addon setup into another account.",
        epilog=EPILOG,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--version", action="version", version=f"stremio-fast-add {__version__}")
    parser.add_argument("--addons", metavar="SRC", help="addon profile: path or URL (default: bundled profile)")
    parser.add_argument("--cli", action="store_true", help="plain linear output, no interactive screen")
    parser.add_argument("--tui", action="store_true", help="force the console UI (curses)")
    parser.add_argument("--gui", action="store_true", help="force the desktop window (tkinter)")
    parser.add_argument("--export", nargs="?", const="", metavar="PATH",
                        help="save the signed-in account's addons to a profile and exit")
    parser.add_argument("--email", help="account email (or STREMIO_EMAIL)")
    parser.add_argument("--password", help="account password (or STREMIO_PASSWORD; prompted if omitted)")
    parser.add_argument("--auth-key", help="use an existing authKey instead of email+password (or STREMIO_AUTHKEY)")
    parser.add_argument("--replace", action="store_true",
                        help="drop the account's current addons first (protected ones are kept)")
    parser.add_argument("--dry-run", action="store_true", help="check every addon but write nothing")
    parser.add_argument("--name", help="label for the exported profile (default: no account details)")
    return parser


def _connect(args) -> tuple[str, str]:
    auth_key = args.auth_key or os.environ.get("STREMIO_AUTHKEY")
    if auth_key:
        return auth_key, api.whoami(auth_key)
    email = args.email or os.environ.get("STREMIO_EMAIL") or input("Stremio email: ").strip()
    password = args.password or os.environ.get("STREMIO_PASSWORD") or getpass.getpass("Stremio password: ")
    return api.login(email, password), email


def _run_cli(args) -> int:
    badge = core.console_badges()
    auth_key, who = _connect(args)
    print(f"[v] signed in as {who}")

    if args.export is not None:
        addons = api.get_addons(auth_key)
        path = store.save(addons, args.export or None, name=args.name or "Stremio addons")
        print(f"[v] exported {len(addons)} addons -> {path}")
        private = [api.addon_name(a) for a in addons if api.has_embedded_config(a)]
        if private:
            print(f"[!] {len(private)} addons keep personal config (tokens, API keys) inside their URL:")
            for name in private:
                print(f"      - {name}")
            print("    Review them before pushing this profile anywhere public.")
        return 0

    profile = store.load(args.addons)
    results = core.make_results(profile.addons)
    print(f"[i] {len(results)} addons from {profile.origin}")
    if not results:
        print("[x] nothing to install")
        return 1

    existing = api.get_addons(auth_key)
    existing_keys = {api.addon_key(a) for a in existing}
    print(f"[i] account currently has {len(existing)} addons\n")

    def report(result: core.AddonResult) -> None:
        if result.status in (core.OK, core.ALREADY, core.FAILED, core.SKIPPED):
            print(f"  {badge[result.status]}  {result.name:<38.38} {result.message}")

    core.check_all(results, existing_keys, on_update=report)
    summary = core.summarize(results)

    if args.dry_run:
        print("\n[i] dry run - nothing written")
    else:
        collection = core.merge(existing, results, replace=args.replace)
        core.push(auth_key, collection)
        summary.total_after = len(collection)
        print(f"\n[v] account now has {summary.total_after} addons - restart Stremio to see them")

    print(
        f"    {badge[core.OK]} {summary.installed} installed   "
        f"{badge[core.ALREADY]} {summary.already} already there   "
        f"{badge[core.FAILED]} {summary.failed} failed"
    )
    return 1 if summary.failed else 0


def _has(module: str) -> bool:
    import importlib.util

    return importlib.util.find_spec(module) is not None


def _pick_frontend(args) -> str:
    """Desktop window on Windows and macOS, console UI on Linux and WSL, --flags win."""
    if args.export is not None or args.cli:
        return "cli"
    if args.tui:
        return "tui"
    if args.gui:
        return "gui"
    if sys.platform in ("win32", "darwin") and _has("tkinter"):
        return "gui"
    # `curses` is a package dir on Windows too - only the `_curses` extension tells the truth.
    if _has("_curses") and sys.stdout.isatty():
        return "tui"
    # Headless Linux: only reach for a window if there is actually a display to put it on.
    if _has("tkinter") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        return "gui"
    return "cli"


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    frontend = _pick_frontend(args)
    try:
        if frontend == "cli":
            return _run_cli(args)
        if frontend == "tui":
            from . import tui

            return tui.run(args.addons)
        from . import gui

        return gui.run(args.addons)
    except api.StremioError as exc:
        print(f"[x] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except ImportError as exc:  # tkinter or curses missing on a stripped-down Python
        print(f"[x] no {frontend} front end available ({exc}). Re-run with --cli.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
