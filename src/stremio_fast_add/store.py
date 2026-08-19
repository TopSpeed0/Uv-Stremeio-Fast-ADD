"""Loading and saving addon profiles (the shareable `addons.json`)."""

from __future__ import annotations

import datetime as _dt
import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from . import api

BUNDLED_PROFILE = Path(__file__).resolve().parent / "profiles" / "default.json"
ENV_SOURCE = "STREMIO_ADDONS_URL"


@dataclass
class Profile:
    addons: list[api.Addon] = field(default_factory=list)
    name: str = "Stremio addons"
    exported_at: str = ""
    origin: str = "(empty)"

    def __len__(self) -> int:
        return len(self.addons)


def _parse(raw: str, origin: str) -> Profile:
    data = json.loads(raw)
    if isinstance(data, list):
        return Profile(addons=data, origin=origin)
    if isinstance(data, dict) and isinstance(data.get("addons"), list):
        return Profile(
            addons=data["addons"],
            name=str(data.get("name") or "Stremio addons"),
            exported_at=str(data.get("exported_at") or ""),
            origin=origin,
        )
    raise ValueError("profile must be a JSON list of addons or an object with an 'addons' list")


def load(source: str | None = None) -> Profile:
    """Load a profile from an explicit path/URL, or fall back through the default chain."""
    candidates: list[str] = []
    if source:
        candidates.append(source)
    else:
        if os.environ.get(ENV_SOURCE):
            candidates.append(os.environ[ENV_SOURCE])
        candidates.append(str(Path.cwd() / "addons.json"))
        candidates.append(str(BUNDLED_PROFILE))

    errors: list[str] = []
    for candidate in candidates:
        try:
            if candidate.startswith(("http://", "https://")):
                raw = json.dumps(api._request(candidate, None, 25.0))
                return _parse(raw, candidate)
            path = Path(candidate).expanduser()
            if not path.is_file():
                continue
            return _parse(path.read_text(encoding="utf-8"), str(path))
        except Exception as exc:  # noqa: BLE001 - report and try the next source
            errors.append(f"{candidate}: {exc}")

    if errors:
        raise FileNotFoundError("could not load an addon profile -> " + " | ".join(errors))
    if source:  # an explicit source that never resolved is a mistake, not an empty profile
        raise FileNotFoundError(f"no addon profile at {source}")
    return Profile(origin="(no profile found - export one first)")


def default_save_path() -> Path:
    """Write into the git checkout when running from source, otherwise the current folder."""
    repo_root = Path(__file__).resolve().parents[2]
    if (repo_root / "pyproject.toml").is_file() and os.access(BUNDLED_PROFILE.parent, os.W_OK):
        return BUNDLED_PROFILE
    return Path.cwd() / "addons.json"


def save(addons: list[api.Addon], path: Path | str | None = None, name: str = "Stremio addons") -> Path:
    target = Path(path) if path else default_save_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "exported_at": _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0).isoformat(),
        "count": len(addons),
        "addons": addons,
    }
    target.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    return target
