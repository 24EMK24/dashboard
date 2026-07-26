# AGENTS.md
Context file for any AI assistant working on this project.
Read this before writing or modifying any code.

## What This Project Is

A personal dashboard for Eli. A Python script fetches things he checks regularly
(weather, stocks, YouTube uploads, news) and writes a single static `dashboard.html`
file to disk. He opens that file in a browser. No accounts, no server, no database in v1.

Eli is early in learning to code. Two rules override normal AI defaults on this project:
1. **Explainability over cleverness.** Prefer the simplest version that works, even if
   longer. Comment every non-obvious line in plain language. When asked to explain, keep
   it narrow and concrete.
2. **No silent scope creep.** There is a strict build order and a deferred list (see the
   design doc). Do not build a later panel early, and do not pull in a framework, database,
   or server before the roadmap calls for it. Raise out-of-order changes as a decision first.

Source of truth for *what* to build: `Docs/dashboard-design.md`.

## Off-Limits — Never Modify

| Path | Why |
| --- | --- |
| `Docs/` | Source-of-truth design documents. Do not rewrite; discuss changes first. |
| `.venv/` | Local virtual environment. Recreate from `requirements.txt`, never edit or commit. |
| `dashboard.html` | Generated output — built by the script, not hand-edited (gitignored). Edit `template.html` (the shell) or the panels instead. |
| `cache/` | Cached API responses — local scratch, not source (gitignored). |
| `.env`, `codes` | Credentials. Never commit; never hardcode secrets elsewhere. |

If you need to modify anything listed here, discuss it first. Never alter generated files
or credentials without explicit instruction.

## Safety

- **Credentials never committed.** `.env` and `codes` are already gitignored. Store any
  secret there; document how to load it here.
- **Fail soft, per panel.** Each panel fetches and renders its own chunk of HTML inside a
  try/except. One dead API shows a short "unavailable" message; it must never blank the
  whole page or stop the other panels from rendering.
- **Respect the roadmap.** Deferred items (price alerts, phone hosting, auto-refresh,
  frameworks, databases) are not built early. See the design doc's deferred list.

## Credentials

- **v1 Weather: none needed.** Open-Meteo is keyless and accountless.
- **v1 Stocks: none needed.** Source chosen is `yfinance`, which is keyless (scrapes Yahoo).
  If it proves unreliable and we switch to Alpha Vantage / Finnhub, that source needs a key —
  put it in a gitignored `.env`, load into the shell env, and verify free-tier limits first.

## Running Things

- Activate the virtual environment (PowerShell): `.\.venv\Scripts\Activate.ps1`
- Install/refresh dependencies: `pip install -r requirements.txt`
- Run a script: `python <script>.py` (e.g. `python weather_test.py`)
- **Build the dashboard:** `python main.py` **from the project root** (the panels use
  relative paths like `config.json` and `cache/`). Writes `dashboard.html`. Direct call
  without activating the venv: `.\.venv\Scripts\python.exe main.py`.
- **Open `dashboard.html` in a real browser (Chrome/Edge), NOT VS Code's Simple Browser** —
  the Simple Browser has no DevTools console and doesn't persist `localStorage`, so
  delete/Watch-Later won't stick. `Start-Process dashboard.html` opens the OS default browser.
  Eli can bookmark the `file://` address; stocks + New Today only refresh on a `python main.py`
  re-run, weather refreshes live via its button, and localStorage state persists per-browser.
- `seed-watchlater.js` (project root, if present) is a THROWAWAY console helper for testing
  Watch Later when the New-Today feed is empty — not part of the build; safe to delete.

## Architecture & Key Modules

Split into a **`panels/` package** (done at panel three, 2026-07-22). Layout:
- **`main.py`** — slim entry point. Imports each `build_<panel>_panel()`, builds the panel
  HTML, reads `template.html`, swaps its `__TOKENS__` for real values with `.replace()`
  (not `.format()` — the CSS/JS are full of `{ }`), and writes `dashboard.html`.
- **`template.html`** — the page shell: all CSS and all browser JavaScript. Tokens it
  expects: `__LOCATION_NAME__`, `__LAT__`, `__LON__`, `__WEATHER_BODY__`, `__STOCKS__`,
  `__YOUTUBE__`, `__NEWS__`. Edit this (not `dashboard.html`) to change styling or client
  behaviour. It **self-reloads two ways** (2026-07-23) so an open tab picks up each rebuild:
  a 30-min `setTimeout`, PLUS a `visibilitychange` handler that reloads when the tab returns
  to view IF the page is ≥`RELOAD_MINUTES` old — the timer alone fails because browsers
  freeze it for backgrounded/asleep tabs, which is why a tab left open for hours showed
  stale "As of" stamps even though the disk build was current.
- **`panels/common.py`** — shared helpers: `load_config()` and the constants it fills
  (`LOCATION_NAME`/`LATITUDE`/`LONGITUDE`/`TICKERS`/`YOUTUBE_CHANNELS`), plus the
  cache-to-disk helpers `get_cached()` and `cached_time_label()`. Fail-soft to built-in
  Seattle defaults if `config.json` is missing/invalid.
- **`panels/weather.py`** — `build_weather_panel()` (Open-Meteo, Pacific). Its `weather_label`
  / `to_ampm` are MIRRORED by JS in `template.html`; keep the two in sync.
- **`panels/stocks.py`** — `build_stocks_panel()` (yfinance, cached, sparklines).
- **`panels/youtube.py`** — `build_youtube_panel()` (**25** channel RSS feeds, today-only in
  Pacific, cached via `get_cached("youtube", …)`). **Live/rerun filter (2026-07-24):** Eli
  doesn't want live streams/reruns/VODs, and YouTube's RSS feed has NO live flag (verified —
  the XML lacks `isLive`/`liveBroadcast`/`premiere`), so `is_live_or_rerun(title)` filters on
  title keywords only (`LIVE_MARKERS`), applied at render time next to the today-filter.
  Conservative to avoid false positives (won't catch a rerun titled like a normal video —
  that needs the Data API). Edit `LIVE_MARKERS` to tune. Feeds are fetched by `fetch_one_feed()`
  using **`requests` + a browser User-Agent + retry/backoff + a gap between channels**
  (`CHANNEL_GAP_SECONDS = 2.5`), then parsed with `feedparser` — NOT feedparser's own
  downloader, which YouTube throttles (it silently dropped ~15 of 23 feeds). Reuse this
  fetch pattern for the news panel. **Throttle resilience (2026-07-23):** `fetch_youtube_data`
  does a first pass over all channels, then a **second pass retrying ONLY the ones that
  returned nothing**, after a `RETRY_PASS_PAUSE` (10s) cool-off; any channel STILL empty
  keeps its **last-known videos carried forward** from the previous `cache/youtube.json`
  (`load_previous_by_channel()`), so a video that showed earlier today doesn't vanish when
  a later run is throttled (the render step's today-filter still drops genuinely old ones
  at midnight). `entry_to_video()` builds each video dict for both passes. `fetch_one_feed`
  does NOT sleep after its final failed attempt (keeps heavy-throttle runs from dragging).
  **Adding a channel:** resolve the `UC…` id from the channel page's `<link rel="canonical">`,
  verify the feed returns entries, then add `{name, channel_id}` to `config.json`. Be aware the
  900 s cache TTL means a rebuild within ~15 minutes of the last fetch serves the OLD cached
  blob and the new channel **silently will not appear** — wait for the cache to expire rather
  than deleting `cache/` (off-limits, and it holds other channels' carry-forward data).
  Renders "New Today" cards with `data-*` attributes; the ✕ delete, the daily clean-slate
  reset, and the whole "Watch Later" widget are handled by JS + `localStorage` in
  `template.html` (a static file has no server to persist those choices). Titles are
  HTML-escaped before insertion. Channel IDs (`UC…`) are resolved via each channel's
  `<link rel="canonical">` — the plain `"channelId"` in page HTML grabs *featured* channels.
- **`panels/news.py`** — `build_news_panel()`. **Google News per-subject corroboration**
  panel (reframed from design §4's plain RSS+keyword idea, since Eli uses Google News). One
  Google News RSS feed per subject (search feed, or the top-stories feed when the query is
  empty), fetched with the SAME `requests`+User-Agent+retry `fetch_one_feed` and cached via
  `get_cached("news", …, 900)` as YouTube. **Throttle resilience (2026-07-24, session 4):**
  news now mirrors YouTube's `fetch_youtube_data` — a first pass over all subjects, a
  **second pass retrying only the ones that returned nothing** after a `RETRY_PASS_PAUSE`
  (10s) cool-off with a `SUBJECT_GAP_SECONDS` (2.5s) gap, and **carry-forward** of a
  subject's last-known items from the previous `cache/news.json`
  (`load_previous_by_subject()`) when it's still empty, so one throttled Google run no longer
  blanks the widget. `entry_to_item()` builds each item dict for both passes. (Before this it
  used the pre-session-3 fragile fetch: one try, 1s gap, no retry, no carry-forward.)
  **Today-only (Pacific)**, like "New Today". At
  render time it **clusters headlines into "stories"** by crude shared-word overlap
  (`significant_words`/`same_story`/`cluster_stories`) — IMPORTANT: it ignores each subject's
  OWN words (name+query) when matching, else every "Half-Life 3" headline merges into one
  blob — and shows each story with a **✓ N sources** badge (distinct outlets),
  most-corroborated first. Each story has a ✕ delete handled by JS + `localStorage`
  (`news_dismissed_v1`, date-keyed, clean slate each day) in `template.html`, mirroring the
  YouTube deletions. Honest limits (stated to Eli + on the widget): corroboration ≠ truth,
  and crude matching can over/under-merge. Low-volume subjects (Half-Life 3, Sly Cooper 5)
  usually show "Nothing today" — an accepted trade-off of strict today-only.

Every `build_<panel>_panel()` wraps its work in try/except and returns an "unavailable"
message on failure (fail-soft), so one dead source never blanks the page.

Personal choices live in **`config.json`** (design §6): `location`, `tickers`,
`youtube_channels` (each `{name, channel_id}`, IDs are the `UC…` form from each channel's
RSS feed), and `news_subjects` (each `{name, query}` — the `query` is what we search Google
News for; an **empty query means the general top-stories feed**).

`weather_test.py` is a throwaway learning script (prints temps to the terminal), not part of
the real pipeline — safe to delete anytime.

**Keeping the dashboard fresh (auto-updater, added 2026-07-23 — LAPTOP-ONLY stopgap):**
`main.py` must re-run to refresh stocks/YouTube/news. Three helpers exist (all optional):
- `run_forever.ps1` — double-click keep-alive loop; re-runs `main.py` every 30 min while
  its window stays open.
- `register-updater.ps1` / `unregister-updater.ps1` — install/remove a **Windows Scheduled
  Task** `EliDashboardUpdate` that runs `pythonw.exe main.py` every 30 min at logon, no
  window, no admin/password. **Currently installed on Eli's laptop.**
These are stopgaps to be **retired once v2 cloud hosting (GitHub Actions + Pages) is live**;
the cloud will do the scheduled rebuild instead. Auto-refresh was originally a deferred v3
item — added early with Eli's approval.

**THE BIG LIMITATION OF THE LOCAL UPDATER (proven 2026-07-25):** `EliDashboardUpdate` runs
only while the laptop is **awake and logged on**. While it sleeps, the task fires **zero
times**, and sleep also **kills a build already in progress** (`LastTaskResult 267014` =
`SCHED_S_TASK_TERMINATED`). A 28-hour sleep (7/24 5:20 PM → 7/25 9:48 PM) left Eli looking at
a day-old page — the reported symptom was "YouTube didn't update", which looks exactly like
the throttling of sessions 3–4 but is a completely different cause.

**How to diagnose a stale page — check these in order, do NOT assume throttling:**
1. `Get-Item dashboard.html | Select LastWriteTime` — is the build on disk actually old? If
   it is current, the problem is browser-side (see `template.html`'s reload handlers).
2. Kernel-Power **event 42** (entering sleep) and Power-Troubleshooter **event 1** (wake) in
   the System log — was the machine even awake to run the task?
3. Only then look at feed coverage / throttling.

**`NumberOfMissedRuns = 0` is NOT proof the task is healthy** — Windows does not count runs
it never fired while asleep. Session 4 read that counter as a clean bill of health; it isn't
one. A clean unthrottled 25-channel build takes **~108 seconds** (measured 2026-07-25); the
multi-minute runs seen in sessions 3–5 were wall clock inflated by throttling back-offs or a
sleep suspension, not normal cost. There is still a short stale window right after waking.

## Key Commands / Endpoints

TBD — will be filled in as commands, routes, or user-facing operations are implemented.

## Shared Utilities & Patterns

- **Comment-every-non-obvious-line** is the house style here (see rule 1 above).
- **One concept at a time** — don't introduce a new library, pattern, and API in the same
  step if it can be avoided; define new terms the first time they appear in real code.
- **Cache-to-disk** pattern (live since Panel 2): `get_cached(name, fetch_fn, max_age)` in
  `panels/common.py` saves a fetch to `cache/<name>.json` and reuses it while fresh. Stocks
  and YouTube both fetch through it (~15 min). Use it for every new fetching panel.
- **Persistent browser state via `localStorage`** (since Panel 3): anything the user changes
  in the browser between runs (YouTube deletions, the Watch-Later list) is stored in
  `localStorage` in `template.html`'s JS, because a static file has no server. State is
  per-browser and won't follow to the phone (that's the v2 hosting concern).

## Roadmap

| Milestone | What it adds |
| --- | --- |
| **v1** | Weather + stocks + YouTube + news panels, generated as a local `dashboard.html` opened on the laptop. **COMPLETE as of 2026-07-23.** |
| **v2** | Reachable from Eli's phone — the script runs on a free host on a schedule and produces a page his phone can load. A separable deployment step; do it only after v1 works. **NEXT UP: GitHub Actions (cron rebuild) + GitHub Pages (public URL). Gated on Eli making a free GitHub account; page is public on the free tier.** |
| **v3** | Price-drop alerts, and/or auto-refresh and notifications. The genuinely hard, optional tier. |

## Session Protocol

### Open
Read these files in full before doing anything:
  C:\Users\24EMK24\Documents\Projects\Practice\.planning\next-session.md
  C:\Users\24EMK24\Documents\Projects\Practice\.planning\STATE.md
  C:\Users\24EMK24\Documents\Projects\Practice\AGENTS.md

Then tell me: what is the specific next task, any constraints that affect it,
and your proposed first action. Do not write any code until I confirm.

### During
Whenever a decision is made mid-session, update
C:\Users\24EMK24\Documents\Projects\Practice\.planning\STATE.md immediately.
Do not wait until close — decisions not recorded are lost if the context resets.

### Close
Eli triggers this by typing **`/close`** (the `.claude/commands/close.md` slash command),
or by saying "close the session" / "wrap up". Steps:
1. Update C:\Users\24EMK24\Documents\Projects\Practice\.planning\STATE.md
   — decisions made this session, current active work, open questions
2. Overwrite C:\Users\24EMK24\Documents\Projects\Practice\.planning\next-session.md
   with a fresh handoff: specific task, what was done, exact next steps,
   files modified, blockers
3. Update C:\Users\24EMK24\Documents\Projects\Practice\AGENTS.md if any project facts
   changed (new scripts, architecture changes, stack decisions confirmed)
4. Finish with a one-sentence summary of what changed this session.

Note: `/close` must be run **while the session is still active** (before quitting) — hooks
run shell commands, not the AI, so there's no way to auto-generate this summary on quit.
