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
j/k or arrows move   space pick   a all   n none   c sign in
i install   d dry run   r replace   e export   q quit
```

Want the desktop window instead? Anything after `sh -s --` is passed straight to the app:

```bash
curl -LsSf https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.sh | sh -s -- --gui
```

On WSL that opens a normal Windows window, courtesy of WSLg — see below.

### Which front end you get

| where | default | override with |
|---|---|---|
| Windows | the desktop window (tkinter) | `--cli` |
| macOS | the desktop window (tkinter) | `--tui`, `--cli` |
| Linux, WSL, SSH — in a terminal | the console UI (curses) | `--gui`, `--cli` |
| no terminal and no display | plain linear output | — |

`--tui` is not offered on Windows: CPython there ships the `curses` package without the `_curses`
extension behind it, so there is no console UI to run. Asking for it anyway prints a one-line reason
and exits `2`, rather than a traceback.

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

## עברית — המדריך המלא

הכלי מדבר ישירות מול ה-API של Stremio (`api.strem.io`) וכותב ל**חשבון**, לא להתקנה מקומית. לכן אין צורך
להתקין תוספים ידנית אחד־אחד — ואין צורך בכלל ש-Stremio יהיה מותקן על המחשב שמריץ את זה.

### הזרימה, בשתי פקודות

**אתה, פעם אחת** — מייצא את התוספים מהחשבון שלך לתוך הריפו, ודוחף:

```bash
uv run stremio-fast-add --export
git add -A && git commit -m "my stremio addons" && git push
```

**החבר, פעם אחת** — מדביק שורה אחת ב-PowerShell:

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.ps1 | iex"
```

בלי אדמין, בלי Python, בלי git, ובלי לפתוח טרמינל חדש. ב-WSL, לינוקס או מק — אותו דבר:

```bash
curl -LsSf https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.sh | sh
```

### מה קורה כשלוחצים Install

Stremio מקבל רק כתיבה של **כל** אוסף התוספים בבת אחת — אין API להוספת תוסף בודד. לכן לפני הכתיבה הכלי
מוריד את ה-`manifest.json` של כל תוסף במקביל (8 threads). זה מה שהופך קריאה אחת גורפת לסטטוס נפרד לכל תוסף,
ותוך כדי גם מרענן כל manifest לגרסה העדכנית.

אחר כך הוא ממזג: התוספים הקיימים אצל החבר **לא נמחקים**, החדשים רק מתווספים, והזיהוי לפי `transportUrl`
מנורמל — אז אפשר להריץ שוב ושוב בלי לייצר כפילויות. התוספים המוגנים של Stremio (Cinemeta, קבצים מקומיים)
אף פעם לא נופלים, גם במצב Replace.

| צבע | מה זה אומר |
|---|---|
| ירוק ✔ | הותקן עכשיו |
| סגול ↺ | כבר היה בחשבון |
| אדום ✘ | נכשל — עם הסיבה המדויקת בעמודת details |
| אפור – | לא נבחר |

### איזה ממשק תקבל

| איפה | ברירת מחדל | לשנות עם |
|---|---|---|
| ווינדוס | חלון (tkinter) | `--cli` |
| מק | חלון (tkinter) | `--tui`, `--cli` |
| לינוקס, WSL, SSH — בטרמינל | ממשק קונסולה (curses) | `--gui`, `--cli` |
| בלי טרמינל ובלי מסך | פלט טקסט רגיל | — |

`--tui` לא זמין בווינדוס: ה-CPython שם מגיע עם תיקיית `curses` בלי הרחבת ה-C שמאחוריה, אז אין ממשק קונסולה
להריץ. בקשה כזו תדפיס שורת הסבר ותצא בקוד 2, בלי traceback.

כדי לקבל חלון במקום קונסולה, כל מה שאחרי `sh -s --` עובר לאפליקציה:

```bash
curl -LsSf https://raw.githubusercontent.com/TopSpeed0/Uv-Stremeio-Fast-ADD/main/fast/install.sh | sh -s -- --gui
```

ב-WSL זה ייפתח כחלון ווינדוס רגיל — WSLg כבר מספק את המסך, בלי שרת X, בלי VNC, בלי xrdp ובלי סביבת שולחן
עבודה להתקין.

### מקשים בממשק הקונסולה

| מקש | פעולה |
|---|---|
| `j` / `k` או חיצים | תנועה בין השורות (`PgUp` / `PgDn` לדילוג) |
| `space` | בחירה/ביטול של השורה |
| `a` / `n` | לבחור הכל / כלום |
| `c` | התחברות (או התנתקות) |
| `i` | להתקין |
| `d` | Dry run — בודק הכל, לא כותב כלום |
| `r` | Replace — מוחק את האוסף הקיים ומתקין במקומו (מוגנים נשמרים) |
| `e` | ייצוא התוספים של החשבון המחובר |
| `q` | יציאה |

### דגלים

| דגל | מה הוא עושה |
|---|---|
| `--addons SRC` | לטעון פרופיל מנתיב או URL במקום זה המובנה |
| `--gui` / `--tui` / `--cli` | לכפות ממשק במקום לתת לו לבחור |
| `--export [PATH]` | לשמור את התוספים של החשבון לקובץ ולצאת |
| `--name NAME` | תווית לייצוא. ברירת המחדל בכוונה לא כוללת פרטי חשבון |
| `--email` / `--password` | פרטי התחברות, או `STREMIO_EMAIL` / `STREMIO_PASSWORD` |
| `--auth-key KEY` | התחברות עם authKey במקום סיסמה, או `STREMIO_AUTHKEY` |
| `--replace` | למחוק את האוסף הקיים לפני ההתקנה (מוגנים נשמרים) |
| `--dry-run` | לבדוק הכל, לא לכתוב כלום |

קודי יציאה: `0` הכל תקין, `1` משהו נכשל בהתקנה, `2` הכלי לא הצליח לרוץ בכלל.

### מאיפה נטענת רשימת התוספים

הראשון שנמצא מנצח: `--addons`, אחר כך `$STREMIO_ADDONS_URL`, אחר כך `addons.json` בתיקייה הנוכחית, ולבסוף
הפרופיל המובנה בחבילה. אז אפשר גם לוותר על הריפו לגמרי ולשתף gist.

### שתי אזהרות

> ⚠️ **פרטיות.** תוספים מוגדרים (Trakt, RealDebrid, MDBList וכו') שומרים את הטוקן או המפתח שלך *בתוך ה-URL*.
> הכלי מזהה אותם ומזהיר בזמן הייצוא, וגם מסמן אותם בטבלה. תבדוק אותם לפני שאתה דוחף לריפו ציבורי — אחרת
> אתה משתף מפתחות אישיים. פרטי ההתחברות עצמם אף פעם לא נכתבים לדיסק; ה-authKey חי בזיכרון עד שסוגרים.

> 🔄 **`--refresh` חשוב בהרצה השנייה.** uv מקאשש את ה-zip לפי ה-URL, אז חבר שכבר הריץ פעם אחת היה מקבל
> בשקט את הרשימה של אתמול. שני סקריפטי ההתקנה כוללים את הדגל, אז זה כבר מסודר.

### למה זה עובד מכל מקום

התוספים נשמרים בשרת של Stremio, לא במחשב. לכן הם מופיעים בכל מקום שהחשבון מחובר בו — אפליקציית הדסקטופ,
הדפדפן, טלפון, Android TV — גם במכשירים שמעולם לא היו ליד המחשב שהרצת עליו. אפשר להריץ מ-Windows Sandbox
זמני, ממחשב של מישהו אחר, מ-WSL. מוחקים את המכונה אחרי דקה, והחשבון נשאר עם כל התוספים.

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

The console UI mirrors this screen for screen — same rows, same statuses, same switches, driven by
`j`/`k` or the arrows, `space`, `a`, `n`, `c`, `i`, `d`, `r`, `e`, `q` instead of the mouse.

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

Every flag:

| flag | what it does |
|---|---|
| `--addons SRC` | load the profile from a path or URL instead of the bundled one |
| `--gui` / `--tui` / `--cli` | force a front end instead of letting it pick |
| `--export [PATH]` | save the account's addons to a profile and exit |
| `--name NAME` | label that export; the default deliberately carries no account details |
| `--email` / `--password` | credentials, or `STREMIO_EMAIL` / `STREMIO_PASSWORD`; prompted if omitted |
| `--auth-key KEY` | sign in with an authKey instead, or `STREMIO_AUTHKEY` |
| `--replace` | drop the account's current addons first (protected ones are kept) |
| `--dry-run` | check every addon, write nothing |
| `--version` / `--help` | the usual |

Exit codes: `0` all good, `1` something failed to install, `2` could not run at all.

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
