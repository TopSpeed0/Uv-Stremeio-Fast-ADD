# Uv-Stremeio-Fast-ADD

**Clone a whole Stremio addon setup into someone else's account — one `uv` command, one GUI, per-addon success/failure.**

You export your Stremio addons once, push the JSON to this repo, and your friend runs a single command.
A dark little window opens, they sign in, hit **Install**, and watch every addon turn green or red.

```bash
uvx --from git+https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD stremio-fast-add
```

No clone, no `pip install`, no virtualenv, no dependencies — the whole thing is standard-library Python
plus tkinter, so `uv` downloads it and runs it in a couple of seconds.

---

## עברית — איך זה עובד

הכלי מדבר ישירות מול ה־API של Stremio (`api.strem.io`), אז אין צורך להתקין תוספים ידנית אחד־אחד:

1. **אתה** מריץ פעם אחת `--export` — כל התוספים מהחשבון שלך נשמרים לקובץ `default.json` בתוך הריפו.
2. אתה עושה `git push`.
3. **החבר** מריץ פקודת `uvx` אחת. נפתח GUI, הוא מתחבר לחשבון Stremio שלו, לוחץ Install —
   וכל תוסף מקבל סטטוס משלו: ירוק = הותקן, סגול = כבר היה שם, אדום = נכשל (עם הסיבה).

התוספים הקיימים אצל החבר **לא נמחקים** — הם רק מתווספים, בלי כפילויות.

> ⚠️ **שים לב לפרטיות:** תוספים מוגדרים (Trakt, RealDebrid, MDBList וכו') שומרים את הטוקן/מפתח שלך
> *בתוך ה־URL*. הכלי מזהה אותם ומזהיר אותך בזמן הייצוא — תמחק אותם מה־JSON לפני שאתה דוחף לריפו ציבורי,
> אחרת אתה משתף את המפתחות האישיים שלך.

---

## The two commands

### 1. Export your setup (you, once)

```bash
uv run stremio-fast-add --export
```

Signs into your account, writes every addon into `src/stremio_fast_add/profiles/default.json`, and warns
about any addon carrying personal tokens in its URL. Then:

```bash
git add -A && git commit -m "my stremio addons" && git push
```

You can also do it from the GUI: connect, then **Export my addons**.

### 2. Install it (your friend, once)

```bash
uvx --from git+https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD stremio-fast-add
```

That's the whole handoff. Everything ships inside the package, including the addon list.

---

## The GUI

| | |
|---|---|
| **1 · Sign in** | email + password, or paste an **auth key** if they'd rather not type a password. `Copy auth key` grabs it for next time. |
| **2 · Addons** | one row per addon — click a row to include/exclude it. `All` / `None` / load a different profile `From file` or `From URL`. |
| **Install** | fetches every manifest in parallel, then writes the merged collection in a single API call. |
| **Status** | ✔ installed · ↺ already there · ✘ failed (with the actual reason) · – skipped, plus a live counter and progress bar. |

Two switches next to the install button:

- **Replace existing collection** — wipe what the account has first (Stremio's protected addons are always kept).
- **Dry run** — check every addon, write nothing. Good for testing a profile.

---

## Terminal mode

No window, same engine:

```bash
uv run stremio-fast-add --cli
```

```
[v] signed in as friend@example.com
[i] 8 addons from .../profiles/default.json
[i] account currently has 4 addons

  +  The Movie Database Addon         ready (v3.1.7)
  +  IMDB Catalogs                    ready (v0.0.5)
  =  Anime Kitsu                      already installed (v0.0.10)
  !  Some Dead Addon                  network error: timed out after 20s

[v] account now has 11 addons - restart Stremio to see them
    + 6 installed   = 1 already there   ! 1 failed
```

Useful flags: `--addons <path|URL>`, `--replace`, `--dry-run`, `--auth-key`, `--email` / `--password`
(or the env vars `STREMIO_EMAIL`, `STREMIO_PASSWORD`, `STREMIO_AUTHKEY`). Exit code is `1` if anything failed.

---

## Where the addon list comes from

First hit wins:

1. `--addons <path or URL>`
2. `$STREMIO_ADDONS_URL`
3. `./addons.json` in the current folder
4. the bundled `src/stremio_fast_add/profiles/default.json`

So you can also skip git entirely and share a raw gist:

```bash
uvx --from git+https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD stremio-fast-add \
    --addons https://gist.githubusercontent.com/.../addons.json
```

---

## How it works

- `api.py` — the Stremio API: `login`, `getUser`, `addonCollectionGet`, `addonCollectionSet`. Stdlib `urllib`, nothing else.
- `core.py` — per-addon status. Stremio only accepts the *whole* collection in one write, so before writing,
  every addon's `manifest.json` is fetched in parallel (8 threads). That's what turns one bulk call into a
  per-addon ✔/✘, and it refreshes each manifest to the current version on the way through.
- Merging is keyed on a normalized `transportUrl`, so re-running is safe: nothing duplicates, and protected
  addons (Cinemeta, Local Files) are never dropped.
- Credentials are never written to disk. The auth key lives in memory for the session only.

## Requirements

`uv`, and that's it — it brings its own Python. Windows, macOS and Linux; the GUI needs tkinter, which uv's
Python ships with (on a distro Python without it, use `--cli`).

Install uv:

```bash
winget install --id=astral-sh.uv -e
```

## Local development

```bash
uv run stremio-fast-add
```
