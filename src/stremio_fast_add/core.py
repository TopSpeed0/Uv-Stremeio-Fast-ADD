"""The install engine: check every addon, merge safely, push once."""

from __future__ import annotations

import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Callable, Iterable

from . import api

PENDING = "pending"
CHECKING = "checking"
OK = "ok"
ALREADY = "already"
FAILED = "failed"
SKIPPED = "skipped"

BADGE = {
    PENDING: "\u2022",     # bullet
    CHECKING: "\u22ef",    # midline ellipsis
    OK: "\u2714",          # check
    ALREADY: "\u21ba",     # already there
    FAILED: "\u2718",      # cross
    SKIPPED: "\u2013",     # dash
}
ASCII_BADGE = {PENDING: ".", CHECKING: "~", OK: "+", ALREADY: "=", FAILED: "!", SKIPPED: "-"}


def console_badges(stream=None) -> dict[str, str]:
    """Legacy Windows consoles are cp1252 and blow up on the pretty glyphs."""
    import sys

    stream = stream or sys.stdout
    encoding = getattr(stream, "encoding", None) or "ascii"
    try:
        "".join(BADGE.values()).encode(encoding)
    except (UnicodeEncodeError, LookupError):
        return dict(ASCII_BADGE)
    return dict(BADGE)


@dataclass
class AddonResult:
    addon: api.Addon
    key: str = ""
    name: str = ""
    status: str = PENDING
    message: str = ""
    elapsed: float = 0.0
    selected: bool = True

    def __post_init__(self) -> None:
        self.key = self.key or api.addon_key(self.addon)
        self.name = self.name or api.addon_name(self.addon)

    @property
    def url(self) -> str:
        return str(self.addon.get("transportUrl") or "")

    @property
    def kinds(self) -> str:
        return api.addon_kinds(self.addon)

    @property
    def succeeded(self) -> bool:
        return self.status in (OK, ALREADY)


def make_results(addons: Iterable[api.Addon]) -> list[AddonResult]:
    seen: set[str] = set()
    results: list[AddonResult] = []
    for addon in addons:
        result = AddonResult(addon=addon)
        if result.key in seen:
            continue
        seen.add(result.key)
        results.append(result)
    return results


def check_all(
    results: list[AddonResult],
    existing_keys: set[str] | None = None,
    on_update: Callable[[AddonResult], None] | None = None,
    workers: int = 8,
    timeout: float = 20.0,
) -> list[AddonResult]:
    """Fetch each manifest in parallel. This is what turns one bulk API call into per-addon status."""
    existing_keys = existing_keys or set()
    notify = on_update or (lambda _r: None)

    def run(result: AddonResult) -> AddonResult:
        if not result.selected:
            result.status, result.message = SKIPPED, "not selected"
            notify(result)
            return result
        result.status, result.message = CHECKING, "contacting addon..."
        notify(result)
        started = time.monotonic()
        try:
            manifest = api.fetch_manifest(result.url, timeout=timeout)
        except api.StremioError as exc:
            result.status, result.message = FAILED, str(exc)
        except Exception as exc:  # noqa: BLE001 - never let one addon kill the run
            result.status, result.message = FAILED, f"{type(exc).__name__}: {exc}"
        else:
            # Keep the freshly downloaded manifest so the friend gets the current version.
            result.addon = dict(result.addon, manifest=manifest)
            version = manifest.get("version")
            if result.key in existing_keys:
                result.status = ALREADY
                result.message = f"already installed (v{version})" if version else "already installed"
            else:
                result.status = OK
                result.message = f"ready (v{version})" if version else "ready"
        result.elapsed = time.monotonic() - started
        notify(result)
        return result

    if not results:
        return results
    with ThreadPoolExecutor(max_workers=max(1, min(workers, len(results)))) as pool:
        list(pool.map(run, results))
    return results


def merge(existing: list[api.Addon], results: list[AddonResult], replace: bool = False) -> list[api.Addon]:
    """Build the collection to upload.

    merge   - keep everything the account already has, append the new ones.
    replace - keep only Stremio's protected addons, then apply the profile.
    """
    base = [a for a in existing if api.is_protected(a)] if replace else list(existing)
    collection: list[api.Addon] = [api.normalize(a) for a in base]
    keys = {api.addon_key(a) for a in collection}
    for result in results:
        if not result.succeeded:
            continue
        if result.key in keys:
            continue
        collection.append(api.normalize(result.addon))
        keys.add(result.key)
    return collection


def push(auth_key: str, collection: list[api.Addon]) -> None:
    api.set_addons(auth_key, collection)


@dataclass
class Summary:
    installed: int = 0
    already: int = 0
    failed: int = 0
    skipped: int = 0
    total_after: int = 0
    failures: list[AddonResult] = field(default_factory=list)


def summarize(results: list[AddonResult], total_after: int = 0) -> Summary:
    summary = Summary(total_after=total_after)
    for result in results:
        if result.status == OK:
            summary.installed += 1
        elif result.status == ALREADY:
            summary.already += 1
        elif result.status == FAILED:
            summary.failed += 1
            summary.failures.append(result)
        elif result.status == SKIPPED:
            summary.skipped += 1
    return summary
