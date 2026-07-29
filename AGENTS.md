# AGENTS.md
Context file for any AI assistant working on this project.
Read this before writing or modifying any code.

## What This Project Is

A personal dashboard for Eli. A Python script fetches things he checks regularly
(weather, stocks, YouTube uploads, news) and writes a single static `dashboard.html`
file. Still no server and no database — but **as of 2026-07-26 it no longer runs on Eli's
laptop.** GitHub Actions rebuilds it in the cloud on a schedule and publishes it to
GitHub Pages:

### 🔗 LIVE AT https://24emk24.github.io/dashboard/
Repo: `https://github.com/24EMK24/dashboard` (public — free Pages requires it).

The laptop is no longer involved in producing the page at all. **The old local
`file:///…/dashboard.html` is frozen at the 2026-07-26 4:28 PM build and will never update
again** — if Eli ever says the dashboard is stale, find out which of the two he is looking at
*before* debugging anything else.

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
  secret there; document how to load it here. For the cloud build use GitHub repo secrets.
- **The repo is PUBLIC** (free Pages requires it), so treat everything committed as
  world-readable. `.gitignore` therefore also excludes **`.planning/`** (private session
  notes) and **`.claude/`** (local tooling, contains hardcoded user paths) at Eli's request —
  do not add them back. `config.json` (channels, news subjects) and `Docs/` **are** public by
  Eli's explicit choice; he does not mind those. Private repos are not an option: Pages does
  not publish from one on the free plan, and even paid the published page stays public.
- **Fail soft, per panel.** Each panel fetches and renders its own chunk of HTML inside a
  try/except. One dead API shows a short "unavailable" message; it must never blank the
  whole page or stop the other panels from rendering.
- **Respect the roadmap.** Deferred items (price alerts, phone hosting, auto-refresh,
  frameworks, databases) are not built early. See the design doc's deferred list.

## Credentials

- **v1 Weather: none needed.** Open-Meteo is keyless and accountless.
- **v1 Stocks: none needed.** Source chosen is `yfinance`, which is keyless (scrapes Yahoo).
- **If a keyed API is ever added** (e.g. Alpha Vantage / Finnhub if yfinance breaks): the key
  goes in **GitHub repo secrets** (repo → Settings → Secrets and variables → Actions) and is
  injected as an env var by `.github/workflows/build.yml`. A local gitignored `.env` is still
  fine for running on the laptop, but **the cloud build cannot see `.env`** — it only has what
  is committed plus what is in secrets. Verify free-tier limits before adopting one.
- **Git identity is set repo-locally** to `24EMK24` /
  `98726549+24EMK24@users.noreply.github.com` so Eli's real email never lands in the public
  commit history. Do not change it to a personal address.
- **Claude cannot `git push`** — this shell has prompts disabled
  (`fatal: Cannot prompt because user interactivity has been disabled`). Git Credential
  Manager is installed system-wide, so **ask Eli to run `git push` in his own terminal.**

## Running Things

- Activate the virtual environment (PowerShell): `.\.venv\Scripts\Activate.ps1`
- Install/refresh dependencies: `pip install -r requirements.txt`
- Run a script: `python <script>.py` (e.g. `python weather_test.py`)
- **Build the dashboard locally:** `python main.py` **from the project root** (the panels use
  relative paths like `config.json` and `cache/`). Writes `dashboard.html`. Direct call
  without activating the venv: `.\.venv\Scripts\python.exe main.py`. This is now only for
  **testing a change before pushing** — it no longer produces the page Eli actually looks at.
- **Publish a change (the real workflow now):** edit → commit → **`git push`** (Eli runs it).
  The `push` trigger rebuilds and republishes within a couple of minutes. **Editing
  `config.json` or a panel locally changes nothing anyone sees until it is pushed.**
- **Force a rebuild without a code change:** repo → **Actions** tab → "Build dashboard" →
  **Run workflow** (the `workflow_dispatch` trigger). Works from a phone. Tick
  **`force_refresh`** to also ignore the 15-minute cache and re-fetch the feeds for real —
  leave it unticked otherwise, since a plain rebuild inside that window republishes the same
  data, and back-to-back re-fetches of 25 YouTube + 10 news feeds are what gets us throttled.
  The freshness strip on the page shows when forcing is actually worth it.
- **Check whether the cloud build is healthy:** the Actions tab shows every run. The public
  API also works without auth, e.g.
  `https://api.github.com/repos/24EMK24/dashboard/actions/runs?per_page=5`.
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
- **`.github/workflows/build.yml`** — the cloud build (added 2026-07-26). Triggers:
  `schedule` (**`3,13,23,33,43,53 * * * *`**), `workflow_dispatch` (manual button, with a
  **`force_refresh`** checkbox), and `push` to `main`.
  **Do not "simplify" that cron back to `*/30`.** Measured 2026-07-27: `*/30` produced **12
  runs in 24.5 hours instead of 48** (all successful — GitHub *drops* scheduled runs on free
  public repos under load, silently), with gaps up to **241 minutes**, so the page was
  effectively rebuilding every ~2 hours. Six odd-minute slots dodge the `:00`/`:30` congestion
  peak and give six chances to fire instead of two. It is not more load on YouTube — panels
  only re-fetch when the 15-min cache is stale. **Do not raise it past 6/hour either:** GitHub
  Pages has a soft limit of ~10 builds per hour.
  The `force_refresh` input is passed to the build step as **`env: FORCE_REFRESH`** and read by
  `force_refresh_requested()` in `panels/common.py`, which makes `get_cached()` ignore the
  15-minute cache. Without it a manual run inside that window republishes identical data.
  Steps: checkout → `setup-python` 3.12 (pip cached) → `pip install -r requirements.txt` →
  **restore `cache/`** → `python main.py` → **save `cache/`** → copy `dashboard.html` to
  `_site/index.html` → `upload-pages-artifact` → `deploy-pages`. `timeout-minutes: 20`,
  `concurrency: pages`. **The `actions/cache` steps are not optional decoration:** every run
  gets a brand-new empty runner, and the throttle carry-forward in `youtube.py`/`news.py`
  works by reading the PREVIOUS `cache/*.json` — without restore/save that protection would
  silently not exist. `cache/` stays gitignored (committing it would mean ~48 junk commits a
  day). GitHub Pages **must** be configured with Source = "GitHub Actions", not
  "Deploy from a branch". **A workflow with no `push:` trigger does not build on push** —
  that mistake made the very first push publish nothing.
- **`template.html`** — the page shell: all CSS and all browser JavaScript. Tokens it
  expects: `__LOCATION_NAME__`, `__LAT__`, `__LON__`, `__WEATHER_BODY__`, `__STOCKS__`,
  `__YOUTUBE__`, `__NEWS__`, `__FRESHNESS__`, `__SCORES__`. Edit this (not `dashboard.html`) to change styling or client
  behaviour. Its `<head>` carries a **`viewport` meta** (without it phones render a shrunken
  ~980px desktop layout — required for the page to be usable on Eli's phone at all) and a
  **`robots` noindex** (keeps the public page out of search engines; this is obscurity, NOT
  privacy — the page is public and free-tier Pages cannot make it otherwise).
  **`__LAT__`/`__LON__` are printed into the published page as JS constants** for the weather
  Refresh button, so on a public page the coordinates are readable by anyone and cannot be
  hidden by repo secrets or any other trick — **never store Eli's exact address**; use a
  town/neighbourhood centre or lat/lon rounded to 2 decimals (~1 km). The quality cost is nil:
  forecast models compute on multi-kilometre grids. It **self-reloads two ways** (2026-07-23) so an open tab picks up each rebuild:
  a 30-min `setTimeout`, PLUS a `visibilitychange` handler that reloads when the tab returns
  to view IF the page is ≥`RELOAD_MINUTES` old — the timer alone fails because browsers
  freeze it for backgrounded/asleep tabs, which is why a tab left open for hours showed
  stale "As of" stamps even though the disk build was current.
- **`panels/common.py`** — shared helpers: `load_config()` and the constants it fills
  (`LOCATION_NAME`/`LATITUDE`/`LONGITUDE`/`TICKERS`/`YOUTUBE_CHANNELS`), plus the
  cache-to-disk helpers `get_cached()`, `cached_time_label()` and `cache_status()`. Fail-soft
  to built-in Seattle defaults if `config.json` is missing/invalid.
  **`CACHE_MAX_AGE = 900`** (15 min) is the single source of truth for cache lifetime — every
  cached panel AND the freshness countdown use it, so use the constant, never a bare `900`,
  or the countdown will eventually contradict the panels.
  **`force_refresh_requested()`** reads the `FORCE_REFRESH` env var (set by the workflow's
  `force_refresh` checkbox) and makes `get_cached()` skip its freshness shortcut. It
  deliberately does **not** delete `cache/*.json` — the throttle carry-forward in
  `youtube.py`/`news.py` reads the previous file, so the cache is overwritten in place.
- **`panels/freshness.py`** — `build_freshness_strip()`, filling the **`__FRESHNESS__`** token
  under the page title (added 2026-07-27). Shows when each cached source was last really
  fetched, a **live JS countdown** to when a plain rebuild would fetch again, and a link to the
  Actions page so Eli can start a rebuild from his phone. Python emits the times as epoch
  **milliseconds** in a `data-sources` attribute; the ticking happens in `template.html`
  (a time baked into a static file starts ageing the moment it is written). Must be built
  **after** the panels in `main.py`, since it reports on the cache files they write.
  **An in-page "rebuild now" button is not possible** — the page is static, and calling
  GitHub's API needs a token that anyone could read out of the public page source.
- **`panels/scores.py`** — `build_scores_panel()`, filling the **`__SCORES__`** token between
  the freshness strip and the widget grid (added 2026-07-28 at Eli's request). One compact card
  per team in `config.json`'s **`sports_teams`** (Mariners, Seahawks): a **live score** when a
  game is in progress, otherwise the last final, plus the next scheduled game. Source is
  **ESPN's public `site.api.espn.com` endpoint** — no key, no account, matching every other
  source on this project — at
  `/apis/site/v2/sports/<sport>/<league>/teams/<team>/schedule`. One request per team returns
  the whole season, so finals and fixtures come from a single fetch (~0.5 s for both teams;
  the MLB payload is ~2.4 MB, which is why only the parsed handful of facts is cached, never
  the raw response). **It is an undocumented API** — the one ESPN's own site calls — so expect
  it to break someday; the fail-soft wrapper and the per-team `try` handle that, and one
  team failing still renders the other.
  **CONFIRMED 2026-07-28: ESPN does not throttle GitHub's runner IP** — cloud run #25 fetched
  both teams from an empty cache and rendered correctly. That was a genuine risk worth
  retesting if scores ever go blank in the cloud but work locally, since YouTube and Google
  have both throttled shared IPs on this project before.
  **`SCORES_MAX_AGE = 300` (5 min) deliberately differs from `CACHE_MAX_AGE`** — a 15-minute-old
  score is several innings behind, and the 15-minute rule exists to avoid YouTube/Google
  throttling, which does not apply to two small ESPN requests.
  **Scores are deliberately NOT in `panels/freshness.py`'s `SOURCES`:** that countdown reports
  the soonest-expiring cache, so a 5-minute source would peg it to "Ready" permanently and
  destroy its signal about YouTube and news. The card carries its own "As of" stamp instead.
  Read the ESPN `status.type.state` field as `pre` / `in` / `post`. The record is shown **only
  once the season has games played** (`show_record`) — out of season ESPN still reports LAST
  season's record, and the Seahawks reading "14-3" beside a September fixture looks like this
  year's result. Game start times are cached as epoch **seconds** and turned into
  "Today 7:10 PM" / "Tomorrow" at RENDER time, so a cached label cannot be left saying "Today"
  after midnight.
- **`panels/weather.py`** — `build_weather_panel()` (Open-Meteo, Pacific). Its `weather_label`
  / `to_ampm` are MIRRORED by JS in `template.html`; keep the two in sync.
- **`panels/stocks.py`** — `build_stocks_panel()` (yfinance, cached, sparklines).
- **`panels/youtube.py`** — `build_youtube_panel()` (**25** channel RSS feeds, today-only in
  Pacific, cached via `get_cached("youtube", …)`). **The live/rerun filter was REMOVED
  2026-07-27** at Eli's request — nothing is hidden by title any more. Do not re-add it without
  him asking: measured on a real 375-video cache it hid **1** video, and when he reported
  missing videos the actual cause was the ~2-hour rebuild gap (see the workflow note above),
  not the filter. YouTube's RSS carries no live flag at all, so any such filter can only guess
  from the title. Feeds are fetched by `fetch_one_feed()`
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
News for; an **empty query means the general top-stories feed**), and **`sports_teams`**
(each `{name, sport, league, team}` — the last three are the words ESPN's address needs, e.g.
`baseball`/`mlb`/`sea`; `name` is just the label shown on the card).

`weather_test.py` is a throwaway learning script (prints temps to the terminal), not part of
the real pipeline — safe to delete anytime.

**Keeping the dashboard fresh — THE CLOUD DOES THIS NOW (since 2026-07-26).**
`.github/workflows/build.yml` re-runs `main.py` on GitHub's machines and republishes the page.
Nothing on Eli's laptop is involved. **The schedule asks for six rebuilds an hour but you must
not assume you get them:** GitHub drops scheduled runs on free public repos whenever it is busy,
silently, and measured on 2026-07-27 it was delivering only about one rebuild every two hours.
Treat the cadence as best-effort, and diagnose it by the gaps between runs (see below).

**The old laptop stopgaps are RETIRED.** The Windows Scheduled Task `EliDashboardUpdate` was
removed on 2026-07-26 (`unregister-updater.ps1`, verified gone). `register-updater.ps1`,
`unregister-updater.ps1` and `run_forever.ps1` still exist in the repo as history and as an
emergency fallback — **do not re-install the task** without a specific reason; it would
duplicate the cloud build, overwrite the local `dashboard.html`, and re-add load on Eli's home
IP (a known throttle driver).

**WHY THE LAPTOP UPDATER HAD TO GO (proven 2026-07-25):** it ran only while the laptop was
**awake and logged on**. While asleep the task fired **zero times**, and sleep also **killed
builds in progress** (`LastTaskResult 267014` = `SCHED_S_TASK_TERMINATED`). A 28-hour sleep
(7/24 5:20 PM → 7/25 9:48 PM) left Eli looking at a day-old page. Also: `NumberOfMissedRuns = 0`
is **NOT** proof of health — Windows does not count runs it never fired while asleep (session 4
misread it as a clean bill of health). This whole class of failure is now structurally
impossible; kept here so the symptom is recognised if it ever resurfaces in another form.

**How to diagnose a stale page — check these in order:**
1. **Which page is he looking at?** The old `file:///…/dashboard.html` is **frozen forever** at
   the 2026-07-26 4:28 PM build. It is not a bug; he should be using
   `https://24emk24.github.io/dashboard/`. Rule this out first — it is now the most likely cause.
2. **Did the cloud build run and pass?** Actions tab, or
   `https://api.github.com/repos/24EMK24/dashboard/actions/runs?per_page=60` (no auth needed).
   **Check the GAPS between runs, not just their conclusions** — the 2026-07-27 problem was 12
   consecutive *successful* runs spread over 24.5 hours, because GitHub silently drops
   scheduled runs on free public repos under load. Nothing looks broken when this happens; the
   page is simply old. Also: **scheduled workflows auto-disable after 60 days of repo
   inactivity** (any commit resets it).
3. **Is it browser-side?** `template.html` self-reloads on a 30-min timer plus a
   `visibilitychange` handler, because browsers freeze timers in backgrounded tabs.
4. **Only then** look at feed coverage / throttling.

A clean unthrottled 25-channel build takes **~108 seconds** locally (measured 2026-07-25) and
run #1 in the cloud took **~2 minutes** end to end including `pip install`. Multi-minute runs
seen in sessions 3–5 were wall clock inflated by throttling back-offs or a sleep suspension,
not normal cost.

## Key Commands / Endpoints

TBD — will be filled in as commands, routes, or user-facing operations are implemented.

## Shared Utilities & Patterns

- **Comment-every-non-obvious-line** is the house style here (see rule 1 above).
- **One concept at a time** — don't introduce a new library, pattern, and API in the same
  step if it can be avoided; define new terms the first time they appear in real code.
- **Cache-to-disk** pattern (live since Panel 2): `get_cached(name, fetch_fn, max_age)` in
  `panels/common.py` saves a fetch to `cache/<name>.json` and reuses it while fresh. Stocks
  and YouTube both fetch through it. **Pass `CACHE_MAX_AGE`, never a bare `900`** — the
  freshness strip promises that same number to Eli on the page. `FORCE_REFRESH=1` in the
  environment bypasses it for one run. Use this helper for every new fetching panel.
- **Persistent browser state via `localStorage`** (since Panel 3): anything the user changes
  in the browser between runs (YouTube deletions, the Watch-Later list) is stored in
  `localStorage` in `template.html`'s JS, because a static file has no server. State is
  per-browser and won't follow to the phone (that's the v2 hosting concern).

## Roadmap

| Milestone | What it adds |
| --- | --- |
| **v1** | Weather + stocks + YouTube + news panels, generated as a local `dashboard.html` opened on the laptop. **COMPLETE as of 2026-07-23.** |
| **v2** | Reachable from Eli's phone, not dependent on Windows. **COMPLETE as of 2026-07-26** — GitHub Actions rebuilds on a schedule and publishes to GitHub Pages at **https://24emk24.github.io/dashboard/**. First cloud build passed on the first attempt; phone confirmed by Eli; laptop updater retired the same day. Refresh cadence was found to be far worse than the cron claimed and was reworked on 2026-07-27 (see the workflow notes above). |
| **Score keeper** | Mariners + Seahawks scores at the top of the page (`panels/scores.py`). **Added 2026-07-28 on Eli's direct request**, outside the v1/v2/v3 tiers — it is not scope creep and it is not a v3 feature. Needs no key, no account and no new dependency (`requests` was already pinned), so it did not pull the project toward the server/database complexity v3 is holding back. |
| **v3** | Price-drop alerts, notifications, and/or true cross-device state sync. The genuinely hard, optional tier. **Not started — do not begin any of it unprompted.** Note that `localStorage` (deletions, Watch Later) is per-browser AND per-origin, so laptop and phone each keep their own; real sync needs a backend, which the project has deliberately avoided so far. |

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
