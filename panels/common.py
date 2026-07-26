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
    }


# Load once at import time, then copy the values into the names the panels use.
_config = load_config()
LOCATION_NAME = _config["location"]["name"]   # e.g. "Seattle" — shown on the weather widget
LATITUDE = _config["location"]["lat"]         # Open-Meteo needs coordinates, not a city name
LONGITUDE = _config["location"]["lon"]
TICKERS = _config["tickers"]                   # the stock tickers to show
YOUTUBE_CHANNELS = _config["youtube_channels"] # the YouTube channels to follow
NEWS_SUBJECTS = _config["news_subjects"]       # the news subjects to watch on Google News


# ---------------------------------------------------------------------------
# Caching to disk (reusable by any panel)
# ---------------------------------------------------------------------------
# Free data sources limit how often you may ask them, so we don't want to fetch on
# every single run. Instead we save each result to a file in cache/ and reuse it
# while it's still fresh. get_cached is written to wrap ANY fetch, so every panel can
# use the same habit.

CACHE_DIR = "cache"   # folder where cached responses are saved (already gitignored)


def get_cached(name, fetch_function, max_age_seconds):
    # Return the saved data in cache/<name>.json if it was written less than
    # max_age_seconds ago. Otherwise call fetch_function(), save what it returns,
    # and return that. We pass the fetch in as a function so this one cache can wrap
    # any kind of fetch. The data must be JSON-friendly (lists / dicts / numbers).
    os.makedirs(CACHE_DIR, exist_ok=True)             # create cache/ on first run
    path = os.path.join(CACHE_DIR, name + ".json")    # e.g. "cache/stocks.json"

    # If a saved copy exists and is still fresh, read it and return — no fetch.
    if os.path.exists(path):
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
