# Uv-Stremeio-Fast-ADD

**Clone a whole Stremio addon setup into someone else's account — one `uv` command, one GUI, per-addon success/failure.**

You export your Stremio addons once, push the JSON to this repo, and your friend runs a single command.
A dark little window opens, they sign in, hit **Install**, and watch every addon turn green or red.

## One-prompt install

Paste this into PowerShell on a Windows box with nothing on it. It installs `uv`, fetches the app, and
opens the window — no admin, no Python, no git, no second step.

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.ps1 | iex"
```

That runs [`fast/install.ps1`](fast/install.ps1) — a comment and one command, nothing hidden. Read it
before you paste it; that goes for any `irm | iex` line anyone sends you.

<details>
<summary>Rather not pipe a script? Same thing, spelled out inline.</summary>

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"; $env:Path = "$env:USERPROFILE\.local\bin;$env:Path"; uvx --refresh --from https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD/archive/refs/heads/main.zip stremio-fast-add
```

</details>

### WSL, Linux, macOS

```bash
curl -LsSf https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.sh | sh
```

Same idea, and here you get a **console UI** instead of a window — the same table, the same per-addon
statuses and colours, driven from the keyboard. No X server, no WSLg, nothing extra to install: `curses`
is in Python's standard library, so the dependency count stays at zero. It works over plain SSH too.

```
space toggle   a all   n none   c sign in   i install   d dry run   r replace   e export   q quit
```

Want the desktop window instead? Anything after `sh -s --` is passed straight to the app:

```bash
curl -LsSf https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.sh | sh -s -- --gui
```

On WSL that opens a normal Windows window, courtesy of WSLg — see below.

### Which front end you get

| where | default | override with |
|---|---|---|
| Windows, macOS | the desktop window (tkinter) | `--tui`, `--cli` |
| Linux, WSL, SSH — in a terminal | the console UI (curses) | `--gui`, `--cli` |
| no terminal and no display | plain linear output | — |

A Linux desktop session still defaults to the console UI, since that is what a terminal implies; pass
`--gui` for the window.

**On WSL, `--gui` gives you the real desktop window** — WSLg already provides the display, so the Tk
window opens on the Windows desktop like any other app. No X server, no VNC, no xrdp, no desktop
environment to install. Verified on WSL2 Ubuntu: `/mnt/wslg` mounted, `WAYLAND_DISPLAY=wayland-0`, and Tk
reporting the host's own 3840x1080 screen.

### Already have `uv`?

Then it's just the one command, on any OS:

```bash
uvx --refresh --from https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD/archive/refs/heads/main.zip stremio-fast-add
```

No clone, no `pip install`, no virtualenv, no dependencies, **not even git** — the whole thing is
standard-library Python (`tkinter` for the window, `curses` for the console UI, `urllib` for the API),
so `uv` downloads it and runs it in a couple of seconds.

### Stremio doesn't have to be installed either

This writes to the Stremio **account**, not to a local install. The addons land server-side, so they show
up everywhere that account signs in — the desktop app, the web player, a phone, an Android TV — including
devices that were never near the machine you ran this on.

Which means you can run it anywhere: a throwaway Windows Sandbox, a work laptop, someone else's PC. Wipe
the box a minute later; the account keeps the addons. Tested exactly that way — fresh Sandbox, one paste,
nothing installed, account loaded.

---

## עברית — איך זה עובד

הכלי מדבר ישירות מול ה־API של Stremio (`api.strem.io`), אז אין צורך להתקין תוספים ידנית אחד־אחד:

1. **אתה** מריץ פעם אחת `--export` — כל התוספים מהחשבון שלך נשמרים לקובץ `default.json` בתוך הריפו.
2. אתה עושה `git push`.
3. **החבר** מדביק שורה אחת ב-PowerShell — היא מתקינה uv, מסדרת PATH, ופותחת את הכלי:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.ps1 | iex"
```

   **בלי אדמין, בלי Python, בלי git.** נפתח GUI, הוא מתחבר לחשבון Stremio שלו, לוחץ Install —
   וכל תוסף מקבל סטטוס משלו: ירוק = הותקן, סגול = כבר היה שם, אדום = נכשל (עם הסיבה).

   ב-WSL, לינוקס או מק — אותו דבר, רק שמקבלים **ממשק קונסולה** במקום חלון:

```bash
curl -LsSf https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.sh | sh
```

התוספים הקיימים אצל החבר **לא נמחקים** — הם רק מתווספים, בלי כפילויות.

> 💡 **לא צריך ש-Stremio יהיה מותקן על המחשב שמריץ את זה.** הכלי כותב ל**חשבון** של Stremio, לא להתקנה
> מקומית — אז התוספים נשמרים בשרת ומופיעים בכל מקום שהחשבון מחובר בו: אפליקציית הדסקטופ, הדפדפן, טלפון,
> Android TV. אפשר להריץ מ-Windows Sandbox זמני, ממחשב של מישהו אחר, מכל ווינדוס. מוחקים את המכונה
> אחרי דקה — והחשבון נשאר עם כל התוספים.

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

Send them the [one-prompt install](#one-prompt-install) line. If they already have `uv`:

```bash
uvx --refresh --from https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD/archive/refs/heads/main.zip stremio-fast-add
```

That's the whole handoff. Everything ships inside the package, including the addon list.

`--refresh` is there for the *second* run: uv caches the zip by URL, so without it a friend who already
ran the command once would quietly reinstall yesterday's addon list. With it, every run picks up whatever
you last pushed.

If they have git and want the repo form instead, `--from git+https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD`
does the same thing. The zip is the default here because a bare Windows box has no git.

---

## The GUI

The console UI mirrors this screen for screen — same rows, same statuses, same switches.

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

So you can leave this repo's own profile alone and point at a raw gist instead:

```bash
uvx --from https://github.com/TopSpeed0/Uv-Stremeio-Fast-ADD/archive/refs/heads/main.zip stremio-fast-add \
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

`uv`, and that's it — it brings its own Python. Windows, macOS and Linux.

The window needs `tkinter` and the console UI needs `curses`; both are standard library, and uv's managed
Python ships tkinter on every platform. If you land on a stripped-down distro Python with neither, `--cli`
always works.

Install uv on Windows:

```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

Astral's official installer, no admin needed — it installs into your own user profile. **Don't run it
elevated:** as admin it lands in the administrator's profile and `uv` won't be on your PATH afterwards.

The PATH change only reaches a *new* terminal, so either open one, or patch the running session and keep
going in the same paste:

```powershell
$env:Path = "$env:USERPROFILE\.local\bin;$env:Path"
```

`winget install --id=astral-sh.uv -e` works too, where winget exists — Windows Sandbox, for one, has neither
winget nor git, which is why the script above and the zip URL are the defaults here.

On macOS and Linux:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Local development

```bash
uv run stremio-fast-add
```
