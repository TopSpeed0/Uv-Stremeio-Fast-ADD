"""Minimal Stremio API client. Standard library only, so `uvx` starts instantly."""

from __future__ import annotations

import json
import re
import ssl
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

API_BASE = "https://api.strem.io/api"
OFFICIAL_COLLECTION_URL = "https://api.strem.io/addonscollection.json"
USER_AGENT = "stremio-fast-add/1.0 (+https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD)"

_SSL_CONTEXT = ssl.create_default_context()
_CONFIG_BLOB = re.compile(r"(?=.{24,}$)(?=.*[A-Za-z])(?=.*\d)[A-Za-z0-9_%~=+-]+")

Addon = dict[str, Any]


class StremioError(RuntimeError):
    """Any failure while talking to Stremio (network, HTTP or API-level)."""


def _request(url: str, payload: dict | None = None, timeout: float = 25.0) -> Any:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    headers = {"User-Agent": USER_AGENT, "Accept": "application/json"}
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=_SSL_CONTEXT) as resp:
            raw = resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        raise StremioError(f"HTTP {exc.code} {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise StremioError(f"network error: {exc.reason}") from exc
    except TimeoutError as exc:
        raise StremioError(f"timed out after {timeout:.0f}s") from exc
    except OSError as exc:
        raise StremioError(f"network error: {exc}") from exc
    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise StremioError("server did not return JSON") from exc


def _api(path: str, payload: dict, timeout: float = 25.0) -> Any:
    body = _request(f"{API_BASE}/{path}", payload, timeout)
    if isinstance(body, dict) and body.get("error"):
        err = body["error"]
        message = err.get("message") if isinstance(err, dict) else str(err)
        raise StremioError(message or "unknown Stremio API error")
    if isinstance(body, dict) and "result" in body:
        return body["result"]
    return body


# --- account -------------------------------------------------------------


def login(email: str, password: str) -> str:
    """Return an authKey for the account. Credentials are never stored on disk."""
    result = _api("login", {"type": "Login", "email": email, "password": password, "facebook": False})
    auth_key = (result or {}).get("authKey")
    if not auth_key:
        raise StremioError("login succeeded but no authKey was returned")
    return auth_key


def whoami(auth_key: str) -> str:
    """Validate an authKey and return the account's email."""
    result = _api("getUser", {"type": "GetUser", "authKey": auth_key})
    return (result or {}).get("email") or "(unknown account)"


# --- addon collection ----------------------------------------------------


def get_addons(auth_key: str) -> list[Addon]:
    result = _api("addonCollectionGet", {"type": "AddonCollectionGet", "authKey": auth_key, "update": True})
    addons = (result or {}).get("addons")
    if not isinstance(addons, list):
        raise StremioError("unexpected response: no addon list")
    return addons


def set_addons(auth_key: str, addons: list[Addon]) -> None:
    _api("addonCollectionSet", {"type": "AddonCollectionSet", "authKey": auth_key, "addons": addons})


def fetch_manifest(transport_url: str, timeout: float = 20.0) -> dict:
    """Download an addon manifest - this is what proves an addon is actually alive."""
    manifest = _request(transport_url, None, timeout)
    if not isinstance(manifest, dict) or not manifest.get("id"):
        raise StremioError("not a valid Stremio manifest")
    return manifest


# --- helpers -------------------------------------------------------------


def addon_key(addon: Addon) -> str:
    """Stable identity for de-duplication across accounts."""
    url = str(addon.get("transportUrl") or "").strip()
    if not url:
        return str(addon.get("manifest", {}).get("id") or id(addon))
    parts = urllib.parse.urlsplit(url)
    return urllib.parse.urlunsplit(
        (parts.scheme.lower(), parts.netloc.lower(), parts.path.rstrip("/"), parts.query, "")
    )


def addon_name(addon: Addon) -> str:
    manifest = addon.get("manifest") or {}
    return str(manifest.get("name") or addon.get("transportUrl") or "unnamed addon")


def addon_kinds(addon: Addon) -> str:
    manifest = addon.get("manifest") or {}
    kinds: list[str] = []
    if manifest.get("catalogs"):
        kinds.append("catalog")
    for resource in manifest.get("resources") or []:
        name = resource.get("name") if isinstance(resource, dict) else resource
        if name in ("stream", "meta", "subtitles") and name not in kinds:
            kinds.append(str(name))
    return ", ".join(kinds) or "-"


def has_embedded_config(addon: Addon) -> bool:
    """True when the transport URL carries per-user configuration.

    Configured addons encode their settings in the URL - Trakt access tokens, debrid API keys,
    TMDB keys. Those must never be shared with a friend as-is.
    """
    url = str(addon.get("transportUrl") or "")
    parts = urllib.parse.urlsplit(url)
    if parts.query:
        return True
    segments = [s for s in parts.path.split("/") if s and s != "manifest.json"]
    # A long opaque blob (base64 config, hex key, %7B-encoded JSON) - but not a dotted
    # reverse-DNS addon id, which is long and harmless.
    return any(_CONFIG_BLOB.fullmatch(s) for s in segments)


def is_protected(addon: Addon) -> bool:
    """Stremio refuses a collection that drops its protected addons (Cinemeta, Local Files...)."""
    return bool((addon.get("flags") or {}).get("protected"))


def is_official(addon: Addon) -> bool:
    return bool((addon.get("flags") or {}).get("official"))


def normalize(addon: Addon) -> Addon:
    """Fill in the fields Stremio expects before an AddonCollectionSet."""
    out = dict(addon)
    out.setdefault("transportName", "http")
    out.setdefault("flags", {})
    return out
