# panels/common.py
# Shared helpers used by every panel: reading Eli's config.json, and the cache-to-disk
# habit. These lived in main.py before the project was split into a panels/ package;
# they moved here unchanged so all panels can import them from one place.

# Standard-library tools:
#   json -> turn Python data into text we can save, and back again
#   os   -> work with files and folders
#   time -> check how long ago a file was saved
import json
import os
import time
# For friendly Pacific-time timestamps on cached data.
from datetime import datetime
from zoneinfo import ZoneInfo

# NOTE on file paths: this module uses plain relative names like "config.json" and
# "cache/", which resolve against wherever you RUN the program from. Always run the
# dashboard from the project root (python main.py), so these point at the right files.

# ---------------------------------------------------------------------------
# Eli's personal choices, loaded from config.json
# ---------------------------------------------------------------------------
# Location, tickers, and YouTube channels live in config.json so Eli can change what he
# tracks WITHOUT editing code. load_config reads that file; if it's missing or broken,
# it falls back to these built-in defaults so the dashboard still runs (fail soft).

def load_config():
    # The values we use if config.json can't be read. Also documents the shape.
    defaults = {
        "location": {"name": "Seattle", "lat": 47.61, "lon": -122.33},
        "tickers": ["AAPL", "MSFT", "NVDA"],
        "youtube_channels": [],   # no channels by default; Eli lists his in config.json
        "news_subjects": [],      # no news subjects by default; Eli lists his in config.json
        "sports_teams": [],       # no teams by default; Eli lists his in config.json
    }
    try:
        with open("config.json", "r", encoding="utf-8") as f:
            config = json.load(f)     # read the file and turn its text into Python data
    except Exception:
        # Missing file, or not valid JSON — use the defaults rather than crashing.
        return defaults

    # Pull each value out with .get(...), falling back to the default if a key is
    # absent, so even a half-filled config.json still works.
    location = config.get("location", {})
    return {
        "location": {
            "name": location.get("name", defaults["location"]["name"]),
            "lat": location.get("lat", defaults["location"]["lat"]),
            "lon": location.get("lon", defaults["location"]["lon"]),
        },
        "tickers": config.get("tickers", defaults["tickers"]),
        # Each channel is a small dict: {"name": ..., "channel_id": "UC..."}.
        "youtube_channels": config.get("youtube_channels", defaults["youtube_channels"]),
        # Each news subject is a small dict: {"name": ..., "query": "..."} — the query is
        # what we search Google News for. An empty query means "top stories".
        "news_subjects": config.get("news_subjects", defaults["news_subjects"]),
        # Each team is a dict: {"name", "sport", "league", "team"} — the last three are
        # the words ESPN's address needs, e.g. baseball / mlb / sea.
        "sports_teams": config.get("sports_teams", defaults["sports_teams"]),
    }


# Load once at import time, then copy the values into the names the panels use.
_config = load_config()
LOCATION_NAME = _config["location"]["name"]   # e.g. "Seattle" — shown on the weather widget
LATITUDE = _config["location"]["lat"]         # Open-Meteo needs coordinates, not a city name
LONGITUDE = _config["location"]["lon"]
TICKERS = _config["tickers"]                   # the stock tickers to show
YOUTUBE_CHANNELS = _config["youtube_channels"] # the YouTube channels to follow
NEWS_SUBJECTS = _config["news_subjects"]       # the news subjects to watch on Google News
SPORTS_TEAMS = _config["sports_teams"]         # the teams whose scores show at the top


# ---------------------------------------------------------------------------
# Caching to disk (reusable by any panel)
# ---------------------------------------------------------------------------
# Free data sources limit how often you may ask them, so we don't want to fetch on
# every single run. Instead we save each result to a file in cache/ and reuse it
# while it's still fresh. get_cached is written to wrap ANY fetch, so every panel can
# use the same habit.

CACHE_DIR = "cache"   # folder where cached responses are saved (already gitignored)

# How long a cached fetch stays usable, in seconds (900 = 15 minutes). Every panel that
# caches uses this same number, and so does the freshness strip at the top of the page —
# keeping it in ONE place means the countdown Eli sees can never disagree with the real
# rule the panels follow.
CACHE_MAX_AGE = 900


# ---------------------------------------------------------------------------
# Fetching a lot of feeds without waiting for each one in turn
# ---------------------------------------------------------------------------
# WHY THIS EXISTS (measured 2026-09-01). A typical cloud build took 147 seconds, of which
# python main.py was about 111 — and roughly 87 of those 111 seconds were spent doing
# NOTHING but waiting. The YouTube and news panels asked for one feed, slept 2.5 seconds,
# asked for the next, slept again: 25 channels plus 10 news subjects is about 87 seconds of
# deliberate pauses, more than three quarters of the whole build.
#
# Those pauses were added back when the dashboard was built on Eli's laptop, where YouTube
# and Google really were throttling his home connection. They were never re-examined after
# the build moved to GitHub's machines. Rather than simply deleting them and hoping, this
# asks for several feeds AT THE SAME TIME instead of one after another — the same total
# number of requests, spread over far less wall-clock time.
#
# A "thread" is a second line of work running alongside the first, so the program can wait
# on several replies at once instead of one at a time. ThreadPoolExecutor is Python's
# ready-made way to do that: it keeps a small pool of workers and hands them jobs. Threads
# suit this job specifically because the work is almost entirely WAITING for a web reply,
# not calculating — while one thread waits, the others get on with it.
from concurrent.futures import ThreadPoolExecutor

# How many feeds to have in flight at once.
#
# This number is a compromise, not an optimum. Higher finishes sooner but looks more like a
# burst, which is exactly what gets a shared IP throttled — and GitHub's runner IPs are
# shared with an enormous number of other people. Six turns 25 channels into about five
# rounds instead of 25, which recovers most of the 87 seconds while still being far gentler
# than asking for all 25 at once.
#
# IMPORTANT: this is a speed change, NOT a removal of the safety nets. Both panels still do
# a second pass over whatever came back empty, and still carry a channel's or subject's
# last-known items forward when it stays empty. If throttling does get worse, those nets
# catch it — and the honest fix is to lower this number, not to reach for anything cleverer.
FETCH_WORKERS = 6


def fetch_in_parallel(items, fetch_one):
    # Run fetch_one(item) for every item, several at a time, and return the results as a
    # list lined up with the items you passed in — results[3] is the answer for items[3].
    #
    # Keeping the original ORDER matters here: the news panel shows subjects in the order
    # Eli listed them in config.json, and replies do not come back in the order they were
    # asked for. So each job remembers its own position and writes its answer into that
    # slot, rather than results being appended as they arrive.
    #
    # A job that raises leaves None in its slot instead of bringing the whole build down.
    # That is the same fail-soft habit the panels already follow, and both callers already
    # treat "nothing came back" as a channel to retry rather than as an error.
    results = [None] * len(items)

    # "with" closes the pool at the end, which also waits for every job to finish.
    with ThreadPoolExecutor(max_workers=FETCH_WORKERS) as pool:
        # submit() starts a job and hands back a "future" — a receipt you can later ask
        # for the answer. We keep a note of which position each receipt belongs to.
        jobs = {}
        for position, item in enumerate(items):
            jobs[pool.submit(fetch_one, item)] = position

        for job in jobs:
            position = jobs[job]
            try:
                results[position] = job.result()
            except Exception:
                results[position] = None

    return results


def force_refresh_requested():
    # True when the build was told to ignore the cache and re-fetch everything.
    #
    # Why this exists: the cloud build normally reuses anything fetched in the last 15
    # minutes (see get_cached below). That is the right default — it stops us hammering
    # YouTube and Google. But it also meant pressing "Run workflow" by hand right after a
    # build would rebuild the page from the SAME saved data, so the manual button looked
    # broken. The workflow now sets FORCE_REFRESH=1 when Eli ticks its "force_refresh"
    # box, and this switch makes that run fetch for real.
    #
    # It reads an ENVIRONMENT VARIABLE — a named value the surrounding system (here, the
    # GitHub Actions workflow) hands to the program when it starts. os.environ.get returns
    # "" if it was never set, so a normal run is unaffected.
    value = os.environ.get("FORCE_REFRESH", "").strip().lower()
    return value in ("1", "true", "yes", "on")


def get_cached(name, fetch_function, max_age_seconds=CACHE_MAX_AGE):
    # Return the saved data in cache/<name>.json if it was written less than
    # max_age_seconds ago. Otherwise call fetch_function(), save what it returns,
    # and return that. We pass the fetch in as a function so this one cache can wrap
    # any kind of fetch. The data must be JSON-friendly (lists / dicts / numbers).
    os.makedirs(CACHE_DIR, exist_ok=True)             # create cache/ on first run
    path = os.path.join(CACHE_DIR, name + ".json")    # e.g. "cache/stocks.json"

    # If a saved copy exists and is still fresh, read it and return — no fetch.
    # A forced refresh skips this shortcut so we always go and fetch. Note it does NOT
    # delete the file: the throttle protection in youtube.py/news.py reads the previous
    # cache to carry channels forward, so the old copy must stay put until we overwrite it.
    if os.path.exists(path) and not force_refresh_requested():
        age_seconds = time.time() - os.path.getmtime(path)   # how old the file is
        if age_seconds < max_age_seconds:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)

    # Otherwise the copy is missing or stale: fetch fresh, save it, return it.
    data = fetch_function()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f)
    return data


def cached_time_label(name):
    # A friendly Pacific-time label ("7:26 PM") for when cache/<name>.json was last
    # written — i.e. when its data was really fetched. Lets a cached panel say
    # honestly how old its numbers are. .lstrip("0") turns "07:26 PM" into "7:26 PM".
    path = os.path.join(CACHE_DIR, name + ".json")
    when = datetime.fromtimestamp(os.path.getmtime(path), ZoneInfo("America/Los_Angeles"))
    return when.strftime("%I:%M %p").lstrip("0")


def cache_status(name, max_age_seconds=CACHE_MAX_AGE):
    # Describe the state of one cached source, for the freshness strip at the top of the
    # page. Returns a small dict:
    #   label   -> "5:12 PM", when this data was really fetched (or "never")
    #   fetched -> that same moment as an epoch number in MILLISECONDS, or None
    #   expires -> the epoch (ms) when the cache goes stale and a re-run would fetch again
    # Milliseconds because the countdown that uses these is JavaScript, and JavaScript
    # measures time in milliseconds while Python uses seconds.
    path = os.path.join(CACHE_DIR, name + ".json")
    try:
        fetched_seconds = os.path.getmtime(path)
    except OSError:
        # No cache file yet (first ever run, or the cloud cache was evicted).
        return {"name": name, "label": "never", "fetched": None, "expires": None}
    return {
        "name": name,
        "label": cached_time_label(name),
        "fetched": int(fetched_seconds * 1000),
        "expires": int((fetched_seconds + max_age_seconds) * 1000),
    }
