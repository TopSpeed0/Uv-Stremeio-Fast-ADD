"""Entry point. Opens the GUI by default; --cli and --export run headless."""

from __future__ import annotations

import argparse
import getpass
import os
import sys

from . import __version__, api, core, store

EPILOG = """\
examples:
  uvx --from git+https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD stremio-fast-add
  uv run stremio-fast-add --export
  uv run stremio-fast-add --cli --addons addons.json
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
    parser.add_argument("--cli", action="store_true", help="install from the terminal, no GUI")
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


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.cli or args.export is not None:
            return _run_cli(args)
        from . import gui

        return gui.run(args.addons)
    except api.StremioError as exc:
        print(f"[x] {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except ImportError as exc:  # tkinter missing on a stripped-down Python
        print(f"[x] no GUI available ({exc}). Re-run with --cli.", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
