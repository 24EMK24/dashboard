# Personal Dashboard — Design & Implementation Document

_Hand this to Claude Code together with the session-bootstrap prompt. This document
is the source of truth for what the project is, what it is **not** (yet), and the
order things get built. The bootstrap prompt sets up the session framework; this
document tells the framework what to build._

---

## 0. Who this is for and how to use it

The developer (Eli) is early in learning to code: a Python course a few years back,
a bit of Arduino, comfortable with the *ideas* but new to web terms (API, HTML, RSS).
He is building this with an AI assistant ("vibe coding").

**Two rules that override normal AI defaults on this project:**

1. **Explainability over cleverness.** Do not write clever or condensed code. Prefer
   the simplest version that works, even if it is longer. Every non-obvious line gets
   a plain-language comment. If asked to explain any piece, explain it narrowly and
   concretely, not with a wall of text.

2. **No silent scope creep.** This project has a strict build order (Section 4) and a
   deferred list (Section 8). Do not build a later panel early because it seems easy,
   and do not pull in a framework, database, or server before the roadmap calls for it.
   If a change seems worth making out of order, raise it as a decision first.

---

## 1. What this project is

A personal dashboard: a single page showing, at a glance, the things Eli checks
regularly. Built as a Python script that fetches data and writes one HTML file.
He opens that file in a browser. No accounts, no server, no database in v1.

**Panels (in build order):**

1. Hourly weather for the next two days
2. Stocks he is tracking
3. New uploads from a chosen set of YouTube channels
4. News items matching his interests
5. Price-drop alerts for items he wants to buy _(deferred — see Section 8)_

---

## 2. Design principles

- **Static-file first.** The program's output is one `dashboard.html` file written to
  disk. Opening that file *is* the product. This removes servers, ports, accounts,
  and databases from v1 entirely — the single biggest source of beginner complexity.
- **Each panel is independent.** A panel fetches something and renders its own chunk
  of HTML. No panel depends on another. A broken or half-built panel must never stop
  the others from rendering.
- **Fail soft.** If a data source is down or returns junk, that panel shows a short
  "unavailable" message and the rest of the dashboard still builds. One dead API must
  not blank the whole page.
- **Config, not code, for personal choices.** Tickers, channel IDs, news keywords,
  and location live in one config file (Section 6), not scattered through the code.
  Eli edits that file to change what he tracks; he should not have to touch logic.
- **Local before remote.** Everything runs on his Windows laptop first. Making it
  reachable from his phone is a later milestone, not a v1 concern (Section 7).

---

## 3. Architecture

A single run does this, top to bottom:

```
main.py
  ├── load config.json            (locations, tickers, channels, keywords)
  ├── build weather panel  -> HTML string
  ├── build stocks panel   -> HTML string
  ├── build youtube panel  -> HTML string
  ├── build news panel     -> HTML string
  ├── assemble full page   (drop the panel strings into an HTML template)
  └── write dashboard.html to disk
```

Each panel is its own function (later, its own file) that returns a string of HTML.
`main.py` calls each one inside a try/except so a failure returns an "unavailable"
message instead of crashing the run.

**Proposed file layout (grows over time):**

```
dashboard/
  main.py                 entry point; builds and writes the page
  config.json             Eli's personal choices (see Section 6)
  panels/
    weather.py
    stocks.py
    youtube.py
    news.py
  template.html           page shell the panels get inserted into
  cache/                  saved API responses (gitignored)
  dashboard.html          the generated output (gitignored)
  .gitignore
```

Start smaller than this. v1 can be a single `main.py`. Split into `panels/` once
the file gets unwieldy — probably around panel three. Don't pre-build the structure.

---

## 4. Build order and per-panel specification

Build strictly in this order. Get each panel working and visible before starting the
next. The first working panel on screen is worth more than a perfect plan.

### Panel 1 — Weather (easy — build first)

- **Source:** Open-Meteo. Free, **no API key**, no account.
- **What it does:** given a latitude/longitude, returns hourly forecast values
  (temperature, precipitation chance, etc.).
- **Scope:** show the next ~48 hours, hour by hour. A simple table or row of cells is
  fine. Group by day so "today" and "tomorrow" are visually separate.
- **Why first:** simplest possible real API call, and the payoff (a working dashboard
  on screen) arrives in one sitting. This panel teaches the whole loop: build a URL,
  fetch it, read the JSON, turn it into HTML.
- **Gotchas:** Open-Meteo wants latitude and longitude, not a city name. Look Eli's up
  once and put it in config.

### Panel 2 — Stocks (easy)

- **Source:** a free stock-quote API (e.g. Alpha Vantage or Finnhub, both have free
  tiers; or the `yfinance` Python library, which needs no key but scrapes Yahoo and
  can break without warning). Pick one during the session and record why in the
  decisions log. **Verify the current free-tier request limits before committing** —
  they change, and they're the main constraint here.
- **What it does:** given a list of tickers from config, fetch the latest price (and
  ideally the day's change) for each.
- **Scope:** a small table — ticker, price, change, up/down colour. Nothing fancy.
- **Gotchas:** free tiers limit how many requests you can make per minute/day. This is
  the first place **caching** matters: save the last response to `cache/` and only
  re-fetch if it's older than, say, 15 minutes. Build the cache habit here; it carries
  to every later panel.

### Panel 3 — YouTube uploads (medium)

- **Source:** YouTube's per-channel **RSS feed**. Every channel publishes one at
  `https://www.youtube.com/feeds/videos.xml?channel_id=CHANNEL_ID`. **No API key, no
  quota.** Use the `feedparser` Python library to read it.
- **What it does:** for each channel in config, list the most recent uploads (title,
  link, date).
- **Important reality check:** you **cannot** get "upcoming" content. Nothing exposes
  what a creator *will* post. You can get latest uploads and scheduled premieres; that
  is all. Frame this panel as **"new since I last looked,"** not "upcoming." Adjust
  Eli's original wording accordingly.
- **Gotchas:** the feed uses **channel IDs** (start with `UC...`), not the handle you
  see in the URL (`@SomeName`). Part of setup is resolving each channel he wants into
  its channel ID and storing that in config.

### Panel 4 — News by interest (medium)

- **Source (v1, the easy honest version):** a handful of **RSS feeds** from news sites
  Eli likes, read with `feedparser`, then **filtered by keywords** he lists in config.
  Show items whose title or summary contains one of his keywords.
- **What it does:** pull recent headlines across those feeds, keep the ones matching
  his interests, show title + source + link.
- **Deliberately NOT in v1:** actually *judging* relevance (semantic matching, ranking,
  "is this interesting to Eli"). That is a rabbit hole and a separate project. Keyword
  filtering is crude but works and ships. Note this limitation in the code so future-Eli
  knows it was a choice, not an oversight.
- **Gotchas:** keyword matching is blunt — it will over- and under-match. That's fine
  for v1. Resist the urge to make it smart mid-build.

### Panel 5 — Price alerts (HARD — deferred, see Section 8)

Do not build this in v1. It is a genuinely different and harder kind of program.
Reasons and the plan for it are in Section 8.

---

## 5. Data sources at a glance

| Panel   | Source                     | API key? | Library      | Difficulty | Main risk |
| ------- | -------------------------- | -------- | ------------ | ---------- | --------- |
| Weather | Open-Meteo                 | No       | `requests`   | Easy       | none major |
| Stocks  | Alpha Vantage / Finnhub / `yfinance` | Maybe | `requests` or `yfinance` | Easy | rate limits |
| YouTube | Channel RSS feeds          | No       | `feedparser` | Medium     | need channel IDs, no "upcoming" |
| News    | Site RSS feeds + keywords  | No       | `feedparser` | Medium     | crude relevance |
| Price   | eBay API (has one); most retailers none | Varies | TBD | Hard | scraping, scheduling, blocking |

---

## 6. Configuration file

All of Eli's personal choices live in `config.json` so he never edits logic to change
what he tracks. Rough shape (fill in real values during setup):

```json
{
  "location": { "name": "Seattle", "lat": 47.61, "lon": -122.33 },
  "tickers": ["AAPL", "MSFT", "NVDA"],
  "youtube_channels": [
    { "name": "Example Channel", "channel_id": "UCxxxxxxxxxxxxxxxx" }
  ],
  "news_feeds": ["https://example.com/rss"],
  "news_keywords": ["engineering", "space", "chess"]
}
```

Part of first-run setup is helping Eli fill this in — including the one-time chore of
resolving each YouTube handle into its `UC...` channel ID.

---

## 7. Roadmap

Lock this order in the framework's roadmap table. It exists to stop the hard version
from being built first.

| Milestone | What it adds |
| --------- | ------------ |
| **v1** | Weather + stocks + YouTube + news panels, generated as a local `dashboard.html` opened on the laptop. |
| **v2** | Reachable from Eli's phone. The script runs on a free host on a schedule and produces a page his phone can load. This is a clean, separable task — do it only after v1 works. |
| **v3** | Price-drop alerts (Section 8), and/or auto-refresh, notifications. The genuinely hard, optional tier. |

**On "phone access" (v2):** the only new concept is that the page has to live somewhere
the phone can reach — a small free host running the script on a schedule. This does not
change the language or the panel code; it's an added deployment step. That's why it's
deferred: bolting it on while the panels are half-built would tangle two hard things
together. Build the working page first, then move it.

---

## 8. Explicitly deferred / non-goals for v1

- **Price-drop alerts.** Different beast: needs to run on a schedule while Eli isn't
  looking, store price history to even define "a good price," and pull from sites that
  actively resist scraping and change layout without notice. Many retailers block or
  ban scrapers. eBay has a real API; Amazon effectively doesn't for this use. Correct
  approach when it's time: one source with a real API (likely eBay), scheduled runs,
  a stored price history, alert on a threshold. **Do not let this panel be the reason
  the project stalls.** Build it last or not at all.
- **Live auto-refresh in the browser.** v1 is a page you reload manually.
- **Accounts, login, multiple users.** Never needed — this is one person's dashboard.
- **A database.** Config is a JSON file; cache is files on disk. No database until
  something genuinely forces one, which for this project is unlikely.
- **Smart/semantic news relevance.** Keyword filtering only in v1.
- **A web framework (Flask/Django/React/etc.).** Not in v1. The output is a static
  file. Introducing a framework is a roadmap decision, not a default.

---

## 9. Tech decisions (seed the decisions log with these)

These are the choices already reasoned through. Copy them into `STATE.md`'s decisions
log at first session so future sessions don't reverse them by accident.

| Decision | Rationale |
| -------- | --------- |
| Language: **Python** | Eli has prior Python exposure; the fetch/parse libraries for this are as simple as it gets; it's the best-supported language for AI-assisted coding, so fewer wrong turns. |
| Output: **static HTML file**, no server in v1 | Removes servers, accounts, and databases — the biggest beginner complexity sinks — while still producing a real, usable dashboard. |
| **Local first, phone later** | Phone hosting is an independent, separable problem; solving it before the panels work would tangle two hard things. |
| Panel order: **weather → stocks → youtube → news → price** | Ascending difficulty; earliest panels give a visible working result fastest. |
| YouTube via **RSS**, not the Data API | No key, no quota, simpler. Accepts the limitation that "upcoming" content isn't available. |
| News via **RSS + keyword filter** in v1 | Ships something useful now; real relevance judgment is a separate rabbit hole. |
| **Cache** API responses to disk | Free-tier rate limits (esp. stocks) require not re-fetching every run. |

---

## 10. Learning guardrails (for both Eli and the AI)

The failure mode of vibe coding is ending up with a working program nobody understands,
which then can't be fixed when it breaks. Defenses, to be honored throughout:

- **Eli refuses to accept code he can't explain out loud.** When code appears that he
  doesn't follow, he stops and asks a narrow question ("what does `.json()` do here and
  why is it needed?") rather than moving on.
- **The AI keeps explanations narrow and concrete** when asked, and comments non-obvious
  lines by default on this project.
- **New terms get defined the first time they're used in real code**, not front-loaded.
- **One concept at a time.** Don't introduce a new library, pattern, and API in the same
  step if it can be avoided.

---

## 11. First concrete task

Before the full dashboard, before wiring the framework's roadmap, the very first task is
the smallest real thing:

> A single Python script that calls the Open-Meteo API for Eli's location and prints the
> next 24 hours of temperature to the terminal. As short as possible, a comment on every
> line explaining what it does.

When real numbers appear in the terminal, the whole fetch→parse→use loop is understood,
and Panel 1 is a short step from there. That printed-temperature script is the seed the
rest of the project grows from.

**Windows note:** absolute paths use backslashes, e.g.
`C:\Users\<name>\dashboard\.planning\STATE.md`. If a path ever seems ignored by a tool,
mismatched slashes are the usual cause — some tools want them doubled or want forward
slashes.
