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
- **Claude CAN `git push` (corrected 2026-09-01).** It worked: `git push origin main`
  pushed `2b983e0` cleanly and started cloud run #942. Earlier sessions recorded that it
  was impossible (`fatal: Cannot prompt because user interactivity has been disabled`) and
  that Eli had to push himself — that is no longer true; Git Credential Manager answers
  without a prompt. If it ever fails with that message again, fall back to asking Eli to
  run it in his own terminal, but **try it first rather than assuming.**
- **Write multi-line commit messages to a file and use `git commit -F <file>`.** Do not pass
  them with `-m`. A PowerShell here-string (`@'…'@`) in the PowerShell tool gets re-parsed
  and git reads the fragments as pathspecs (`error: pathspec 'unavailable' did not match any
  file(s)`); PowerShell here-string syntax inside the *Bash* tool fails differently, leaving a
  stray `@` as the subject line. Both have now cost a session a failed commit. A message file
  sidesteps every quoting rule in both shells.

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
- **The Refresh button refreshes WEATHER AND SCORES, and nothing else** (scores added
  2026-09-01). Those are the only two things the browser can fetch for itself; stocks,
  YouTube and news are baked into the file by Python and can only change on a rebuild. Eli
  raised this himself — the button "only refreshes the weather" — so **the label now names
  what it really does** rather than saying a bare "Refresh". Do not relabel it back, and do
  not wire stocks/YouTube/news into it: those feeds have no CORS permission for a browser
  and the request would simply be refused.
- **Open `dashboard.html` in a real browser (Chrome/Edge), NOT VS Code's Simple Browser** —
  the Simple Browser has no DevTools console and doesn't persist `localStorage`, so
  delete/Watch-Later won't stick. `Start-Process dashboard.html` opens the OS default browser.
  Eli can bookmark the `file://` address; stocks + New Today only refresh on a `python main.py`
  re-run, weather refreshes live via its button, and localStorage state persists per-browser.
- **Testing the page's JavaScript: Node IS available (v24.18.0 as of 2026-08-04).** Older
  notes claiming there is no Node on this machine are wrong. `node --check` on the extracted
  `<script>` catches a syntax error that would otherwise silently break every interactive
  feature at once (the freshness countdown sitting on "checking…" is the usual symptom), and
  **`jsdom` gives a real DOM plus a real `localStorage`**, so the ✕ buttons, the click-to-clear
  and the per-day clean-slate rules can be exercised against the actual generated
  `dashboard.html`. **Install jsdom in a scratch folder, NOT into this project** — nothing in
  the build needs it and `requirements.txt` is Python-only.
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
  **BUT THE SIX-SLOT CRON DID NOT FIX THE CADENCE — measured over 7 days, 2026-08-04.**
  95 scheduled runs delivered out of **984 requested (10%)**, all successful, gaps **min 48 ·
  median 93 · mean 105 · max 218 minutes**. Against the old `*/30` baseline (median 99) that
  is noise, not a fix. **Asking GitHub for more scheduled runs does not get more** — the
  congestion-dodging theory is disproven, so do not spend another session re-tuning this
  expression. Leaving it at six slots is still correct (it is no worse, and costs nothing on a
  public repo), and **`*/30` is still not an improvement to revert to**. The only real
  escalation left is an **external cron service (e.g. cron-job.org) hitting a
  `repository_dispatch` webhook** — more reliable, but it costs an account, a token and
  another failure point, so **discuss it with Eli before building it.** Treat the effective
  rebuild cadence as ~1.5 hours when reasoning about anything else on this project.
  The `force_refresh` input is passed to the build step as **`env: FORCE_REFRESH`** and read by
  `force_refresh_requested()` in `panels/common.py`, which makes `get_cached()` ignore the
  15-minute cache. Without it a manual run inside that window republishes identical data.
  **ACTION VERSIONS ARE PINNED PAST NODE 20 (bumped 2026-09-01):** `checkout@v7`,
  `setup-python@v7`, `cache/restore`+`cache/save@v6`, `deploy-pages@v5`,
  `upload-pages-artifact@v5`. Every manual run used to print "Node.js 20 is deprecated...
  being forced to run on Node.js 24" — harmless then, a real failure once GitHub finishes
  retiring that runtime. **Each version was verified by reading that tag's own `action.yml`
  `runs.using:` field, not guessed** — the bumped majors say `node24`, the ones they replace
  say `node20`. `upload-pages-artifact` is a `composite` action either way. If that warning
  ever comes back, check the same field again rather than guessing a number.
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
  **`fetch_in_parallel(items, fetch_one)` + `FETCH_WORKERS = 6` (added 2026-09-01)** — the
  shared way every feed panel now fetches. It runs `fetch_one` over the items several at a
  time in a `ThreadPoolExecutor` and returns the answers **lined up with the items you
  passed in**, because replies do not arrive in the order they were asked for and the news
  panel must keep Eli's `config.json` subject order. A job that raises leaves `None` in its
  slot rather than bringing the build down.
  **Why it exists:** a typical cloud build was 147 s, of which `python main.py` was ~111 s,
  of which **~87 s was pure `time.sleep()`** — 25 YouTube channels and 10 news subjects,
  each with a 2.5 s gap, one after another. Those pauses were written for Eli's throttled
  home IP and were never re-examined after the build moved to GitHub's machines. **Measured
  result: a full forced rebuild went from ~111 s to 5 s with NO loss of coverage** (25/25
  channels, 375 videos, 10/10 news subjects, none empty).
  **If throttling ever gets worse, LOWER `FETCH_WORKERS` — do not reach for anything
  cleverer.** Six is a compromise, not an optimum: higher finishes sooner but looks more
  like a burst, and runner IPs are shared with a very large number of other people. The
  safety nets are unchanged and still do the real protecting — both panels still retry
  whatever came back empty, and still carry a channel's or subject's last-known items
  forward when it stays empty. The **retry passes deliberately KEEP their 2.5 s gaps**:
  they only run after something already came back empty, which is the moment to be gentle
  rather than fast.
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
  the freshness strip and the widget grid. One compact card per team in `config.json`'s
  **`sports_teams`** (Mariners, Seahawks).
  **THIS PANEL NO LONGER FETCHES ANYTHING — THE BROWSER DOES (changed 2026-09-01).** Python
  now emits only the card SHELL: an empty card per team carrying `data-sport` /
  `data-league` / `data-team` / `data-name`, plus `data-past-games` on the strip. All the
  fetching, parsing and rendering lives in `template.html`'s script (see below). There is
  no `cache/scores.json` any more, no `SCORES_MAX_AGE`, and no build-time "As of" stamp.
  **Two reasons it moved.** (1) **ESPN refuses GitHub's runner IPs.** The panel was dead on
  the live page for four weeks — both cards read "Scores unavailable right now." from
  2026-08-04 to 2026-09-01 — while the identical code fetched fine from Eli's laptop
  throughout (re-confirmed 2026-09-01: HTTP 200, Mariners 64-74). Nothing we can write
  changes whose machine the build runs on. (2) **A baked-in score is only as fresh as the
  last rebuild**, and the rebuild cadence is measured at ~16% of what the cron asks for,
  with gaps up to 12.5 hours. Browser-side, the score is as new as the moment you look.
  **What made it possible: ESPN sends `Access-Control-Allow-Origin: *`** on both
  `/schedule` and `/scoreboard` (verified by sending an `Origin:` header from the real
  published address — check this before assuming any other API can move the same way).
  **Payload is a non-issue despite appearances:** the MLB season schedule is 2.6 MB of text
  but **92 KB on the wire** because the server gzips it and browsers ask for that
  automatically; the NFL one is 4 KB. Both teams ≈ 96 KB per page load. Note ESPN **ignores
  a `limit` param** on that address, so do not bother trying to trim it that way.
- **The score logic itself now lives in `template.html`** (`refreshScores`, `loadTeamCard`,
  `readGame`, `scoreOf`, `fetchLiveScore`, `renderGameLine`, and the Pacific-time helpers
  `pacificYmd` / `pacificClock` / `pacificDayLabel` / `whenLabel`). It is a close
  TRANSLATION of the Python that used to do the job — which had been verified against three
  genuinely live games — not a fresh guess at ESPN's shapes. Keep it that way.
  **`scoreOf()` must handle TWO score shapes** because ESPN is inconsistent between its own
  endpoints: `/schedule` gives `{"value": 4.0, "displayValue": "4"}` on a finished game,
  `/scoreboard` gives the plain string `"4"` on a live one.
  **Live scores come from a different endpoint.** `/schedule` carries **no score at all
  while a game is being played** (verified against four mid-game teams, 2026-08-04) — only
  the `status`, which is why a LIVE badge once showed with no numbers. `fetchLiveScore()`
  reads `/scoreboard`, and is called **only when the schedule reports a game in progress**,
  so an ordinary day costs one request per team. It has its own try/catch: a scoreboard
  outage costs the numbers, not the card.
  **Pacific time must be done with `Intl`, not the Date object's own getters.** The page now
  runs on Eli's phone wherever it is; `getDate()` answers in the *device's* zone, so a
  7:10 PM Pacific game would land on the wrong calendar day for anyone east of us — and
  "Today" is exactly the word that must not be wrong.
  **TWO REAL BUGS WERE FOUND AGAINST LIVE DATA ON 2026-09-01 — do not regress them:**
  (a) **ESPN answers the NFL schedule with the PRESEASON in early September.** The default
  address returned 3 finished exhibition games and *nothing upcoming*, so the Seahawks card
  showed preseason losses and no "Next:" line on the weekend of the season opener. Fixed by
  re-asking with **`?seasontype=2`** (ESPN's number for the regular season, 17 real
  fixtures) **only when the first reply had nothing upcoming** — so it costs no extra
  request on an ordinary day.
  (b) **ESPN marks BOTH teams `winner: false` in a tie**, which is indistinguishable from a
  loss if you only read our own side. A real Seahawks 9-9 at the Chiefs was rendering as an
  "L". Ties are now detected by **comparing the two scores**, not by trusting the flag.
  **The card shows the past THREE finished games** (`PAST_GAMES_SHOWN` in `scores.py`,
  handed to the browser via `data-past-games` so the number lives in one place), added
  2026-09-01 at Eli's request. The newest result keeps the big type; the earlier ones sit
  in a smaller, dimmer `.score-past` list so the strip stays one short row.
  **The record and division standing** come from the reply's own `team` block
  (`recordSummary`, `standingSummary` — "64-74 · 3rd in AL West"). Shown **only once the
  season has games played**: out of season ESPN still reports LAST season's record, and the
  Seahawks reading "14-3" beside a September fixture looks like this year's result.
  **Scores are deliberately NOT in `panels/freshness.py`'s `SOURCES`** — that countdown
  reports the soonest-expiring cache, and scores no longer have one at all. The strip
  carries its own browser-side "As of" stamp instead.
  Read the ESPN `status.type.state` field as `pre` / `in` / `post`.
  **Do not "verify" the live path with a synthetic fixture** — session 9 did exactly that,
  built it with the finished-game shape, and shipped a bug Eli then found. Point the code
  at a team that is genuinely playing (`/scoreboard` lists them across a league).
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
  **The FIRST pass is now concurrent (2026-09-01)** — it goes through
  `fetch_in_parallel()` (see `panels/common.py`) instead of one channel at a time with a
  2.5 s gap, which is where ~62 s of every build was going. `CHANNEL_GAP_SECONDS` still
  applies to the RETRY pass. The retry pass and the carry-forward are unchanged.
  **Adding a channel:** resolve the `UC…` id from the channel page's `<link rel="canonical">`,
  verify the feed returns entries, then add `{name, channel_id}` to `config.json`. Be aware the
  900 s cache TTL means a rebuild within ~15 minutes of the last fetch serves the OLD cached
  blob and the new channel **silently will not appear** — wait for the cache to expire rather
  than deleting `cache/` (off-limits, and it holds other channels' carry-forward data).
  Renders "New Today" cards with `data-*` attributes; the ✕ delete, the daily clean-slate
  reset, and the whole "Watch Later" widget are handled by JS + `localStorage` in
  `template.html` (a static file has no server to persist those choices). Titles are
  HTML-escaped before insertion.
  **Clicking a video clears it from the list (`clearOnOpen()`, added 2026-08-04 at Eli's
  request), in BOTH lists** — the thumbnail and title links carry
  `onclick="clearOnOpen(this)"`. The two lists forget differently on purpose: a "New Today"
  click dismisses for the rest of today, a "Watch Later" click removes permanently, because
  that list is one Eli built deliberately. **The removal inside `clearOnOpen` is wrapped in a
  0 ms `setTimeout` and that is load-bearing** — taking a link out of the page while its own
  click is still being handled can cancel the new tab in some browsers, and "the video didn't
  open" would be far worse than a card that lingers a moment. It also must never call
  `preventDefault()`. `dismissToday()` was split so `dismissTodayCard(card)` can be called
  from a link rather than a button. Channel IDs (`UC…`) are resolved via each channel's
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
  **The FIRST pass is now concurrent (2026-09-01)**, via `fetch_in_parallel()` — see
  `panels/common.py`. The subject records are built up front so the results come back in
  Eli's `config.json` order; `SUBJECT_GAP_SECONDS` still applies to the RETRY pass.
  **Today-only (Pacific)**, like "New Today". At
  render time it **clusters headlines into "stories"** by crude shared-word overlap
  (`significant_words`/`same_story`/`cluster_stories`) — IMPORTANT: it ignores each subject's
  OWN words (name+query) when matching, else every "Half-Life 3" headline merges into one
  blob — and shows each story with a **✓ N sources** badge (distinct outlets),
  most-corroborated first. Each story has a ✕ delete handled by JS + `localStorage`
  (`news_dismissed_v1`, date-keyed, clean slate each day) in `template.html`, mirroring the
  YouTube deletions.
  **Each subject heading also carries a ✕ that clears every headline under it at once**
  (`clearNewsSubject()`, added 2026-08-04 at Eli's request). It **clears the headlines, it
  does NOT hide the category** — Eli's words were *"i just want the old headlines that were
  deleted gone and if there are new ones they can come in."* It works by pushing every
  visible story's id into the **same** `news_dismissed_v1` list, so it needed no new storage
  and no "unhide" affordance: because a story is remembered by its **link**, cleared
  headlines stay gone while new ones from a later rebuild come straight through. The heading
  always stays; the ✕ is only rendered when the subject has stories and hides itself once its
  group is empty. Honest limits (stated to Eli + on the widget): corroboration ≠ truth,
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
   **Runs, jobs and PER-STEP TIMINGS are all public** — `/actions/runs/<run_id>/jobs` gives a
   step-by-step breakdown, which is how the "87 seconds of sleeping" was found. **Run LOGS
   are NOT public: `/actions/runs/<run_id>/logs` returns 403 without a token.** Any plan
   that depends on "push a print statement and read the public log" therefore needs Eli to
   open it in a browser — worth knowing before proposing one.
   **Check the GAPS between runs, not just their conclusions** — the 2026-07-27 problem was 12
   consecutive *successful* runs spread over 24.5 hours, because GitHub silently drops
   scheduled runs on free public repos under load. Nothing looks broken when this happens; the
   page is simply old. Also: **scheduled workflows auto-disable after 60 days of repo
   inactivity** (any commit resets it).
3. **Is it browser-side?** `template.html` self-reloads on a 30-min timer plus a
   `visibilitychange` handler, because browsers freeze timers in backgrounded tabs.
4. **Is it the score cards specifically?** They are the one panel fetched by the BROWSER,
   not by the build (since 2026-09-01), so they fail on a completely different axis from
   everything else. **A browser-side failure and a build-time failure show the identical
   "Scores unavailable right now." text**, so ask what the REST of the page looks like: a
   healthy page around two dead score cards means his browser or ESPN, not the build.
5. **Only then** look at feed coverage / throttling. **Since 2026-09-01 the first fetch pass
   is concurrent** (`FETCH_WORKERS = 6`), so if coverage ever drops — channels or subjects
   falling back to carried-forward data — **lower that number first.**

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
| **Score keeper** | Mariners + Seahawks scores at the top of the page. **Rebuilt 2026-09-01 to fetch in the BROWSER** (past 3 games + division standing; `panels/scores.py` now emits only shells). **Added 2026-07-28 on Eli's direct request**, outside the v1/v2/v3 tiers — it is not scope creep and it is not a v3 feature. Needs no key, no account and no new dependency (`requests` was already pinned), so it did not pull the project toward the server/database complexity v3 is holding back. |
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
