# panels/news.py
# The News panel: for each subject in config.json, read Google News' RSS feed for that
# subject and show the recent headlines. Google News is an AGGREGATOR — it gathers the
# same story from many outlets and tags each result with the outlet that published it.
# We use that: when several different outlets are carrying what looks like the SAME story,
# we collapse them into one row and show a "✓ N sources" badge, most-corroborated first.
#
# HONEST LIMITS (v1, on purpose — see the design doc's "news is a rabbit hole" note):
#   * This is CORROBORATION, not truth. "4 sources" means 4 outlets ran it, which is a good
#     signal it's real and significant — but outlets often echo one wire story, so it is
#     not 4 independent confirmations. We don't claim a story is "true".
#   * Deciding two headlines are "the same story" is done crudely, by shared words. It will
#     sometimes merge two different stories or miss a match. Kept deliberately simple.
#
# Like the YouTube panel, feeds are fetched THROUGH the shared cache so repeated runs don't
# re-hit Google, and the whole thing fails soft: any breakage returns a short message.

# "feedparser" reads the RSS/Atom XML and hands back easy Python objects (same as YouTube).
import feedparser
# "requests" does the actual download so we can send a browser User-Agent and retry —
# Google, like YouTube, throttles rapid plain requests. Reused pattern from youtube.py.
import requests
# "time" for polite pauses between requests and for "how long ago" timestamps.
import time
# "html" gives html.escape() to make headlines safe to drop into the page.
import html
# "calendar" turns feedparser's UTC time-tuple into a plain epoch number (seconds since 1970).
import calendar
# "re" (regular expressions) is used once, to split a headline into plain words.
import re
# "os" and "json" let us read the PREVIOUS run's cache file directly, so a subject that
# Google throttles this run can keep the items it had last run (see fetch_news_data) —
# the same carry-forward trick the YouTube panel uses so nothing silently blanks out.
import os
import json
# "urllib.parse.quote" percent-encodes a search term so spaces/punctuation are safe in a URL.
from urllib.parse import quote
# datetime + ZoneInfo let us ask "what is today's date in Pacific?" so we can keep only
# today's stories — the same today-only rule the YouTube panel uses.
from datetime import datetime
from zoneinfo import ZoneInfo

# Eli's subject list from config.json, plus the shared cache helpers. CACHE_DIR is the
# folder get_cached writes to; we read cache/news.json from it to carry subjects over
# when Google throttles a fetch.
from panels.common import NEWS_SUBJECTS, get_cached, cached_time_label, CACHE_DIR

# A normal browser User-Agent, so Google News serves the feed instead of throttling us.
USER_AGENT = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Pacific time zone object — the whole dashboard works in Pacific, and "today" is a
# Pacific calendar day (same as the YouTube panel).
PACIFIC = ZoneInfo("America/Los_Angeles")

# How many stories to show per subject (the rest are reachable by scrolling the widget).
STORIES_PER_SUBJECT = 4

# How long to wait between subjects. A bigger gap makes Google far less likely to throttle
# the burst of requests. Same values the YouTube panel settled on, so both panels behave
# the same way (it used to be 1s here, which offered no real protection).
SUBJECT_GAP_SECONDS = 2.5
# After the first pass, subjects that still returned nothing get ONE more try — but only
# after a longer cool-off, since throttling is usually brief. This recovers most stragglers.
RETRY_PASS_PAUSE = 10

# Words too common to help decide if two headlines are the same story. Ignored when we
# compare headlines. Kept short and obvious on purpose.
STOPWORDS = {
    "the", "a", "an", "and", "or", "but", "for", "nor", "so", "yet", "of", "to", "in",
    "on", "at", "by", "with", "from", "as", "is", "are", "was", "were", "be", "been",
    "it", "its", "this", "that", "these", "those", "he", "she", "they", "you", "we",
    "his", "her", "their", "your", "our", "not", "will", "has", "have", "had", "new",
    "says", "say", "said", "after", "over", "into", "out", "up", "down", "who", "what",
    "how", "why", "when", "amid", "vs", "-",
}


def feed_url_for(query):
    # Build the Google News RSS address for one subject. An empty query means Eli wants the
    # general "top stories" feed; otherwise we hit the search feed for that query. The
    # hl/gl/ceid bits ask Google for US English results.
    tail = "hl=en-US&gl=US&ceid=US:en"
    if query.strip() == "":
        return "https://news.google.com/rss?" + tail
    return "https://news.google.com/rss/search?q=" + quote(query) + "&" + tail


def fetch_one_feed(url):
    # Fetch one Google News feed and return its entries (a list). Google throttles rapid
    # requests — a throttled reply comes back as an error code or empty — so on a bad reply
    # we wait a moment and retry a couple of times. Returns [] if it never succeeds, so one
    # stubborn subject just contributes nothing this run. (Same shape as youtube.py's fetch.)
    for attempt in range(3):                       # up to 3 tries
        try:
            reply = requests.get(url, headers=USER_AGENT, timeout=15)
            if reply.status_code == 200:
                feed = feedparser.parse(reply.content)
                if feed.entries:
                    return feed.entries
        except Exception:
            pass                                   # network hiccup — fall through to retry
        time.sleep(2.0 * (attempt + 1))            # back off (2s, then 4s) before retrying
    return []


def split_headline(raw_title):
    # Google News formats titles as "Actual headline - Outlet Name". Split off that trailing
    # " - Outlet" so we can show a clean headline and know which outlet it came from.
    # rpartition splits on the LAST " - ", which is where the outlet sits.
    headline, sep, outlet = raw_title.rpartition(" - ")
    if sep == "":                 # no " - " at all: keep the whole thing, outlet unknown
        return raw_title.strip(), ""
    return headline.strip(), outlet.strip()


def entry_to_item(entry):
    # Turn one feedparser entry into our plain, JSON-friendly dict — or None if it's missing
    # a date (we can't order it). Pulled out of the loop so both the first pass and the retry
    # pass below build items the exact same way.
    if not entry.get("published_parsed"):
        return None
    headline, outlet_from_title = split_headline(entry.get("title", ""))
    # Google News also puts the outlet in a <source> tag; prefer it, fall back to the outlet
    # we split off the title, then to "Unknown".
    source = ""
    if entry.get("source"):
        source = entry.source.get("title", "")
    source = source or outlet_from_title or "Unknown"
    return {
        "headline": headline,
        "url": entry.get("link", ""),
        "source": source,
        # published_parsed is a UTC time-tuple; timegm turns it into an epoch number.
        "published_epoch": calendar.timegm(entry.published_parsed),
    }


def load_previous_by_subject():
    # Read the items the LAST run saved (cache/news.json is a list of subject dicts) and
    # group them by subject name: {name: [item, ...]}. We use this to carry a subject's
    # items forward when Google throttles its feed this run, so today's news that was
    # showing earlier doesn't suddenly vanish. Returns {} if there's no cache yet or it
    # can't be read — in that case there's simply nothing to carry over. (Mirrors the
    # YouTube panel's load_previous_by_channel.)
    path = os.path.join(CACHE_DIR, "news.json")
    previous = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for s in json.load(f):
                previous[s["name"]] = s.get("items", [])
    except Exception:
        pass
    return previous


def fetch_news_data():
    # Fetch every subject's feed and return a plain list (JSON-friendly, so get_cached can
    # save it). We keep the recent items each feed returns; grouping the same story across
    # outlets happens later, at render time. This is the slow part (one request per subject
    # with polite pauses), but it only runs when the cache is stale — at most every ~15 min.
    #
    # Google throttles bursts of requests (replies come back empty), so on any given run some
    # subjects return nothing. Two things keep that from blanking them — the SAME two the
    # YouTube panel uses:
    #   * a second try over just the failed subjects, after a longer cool-off, and
    #   * for any subject STILL failing, we reuse the items it had last run.
    previous = load_previous_by_subject()   # last run's items, grouped by subject name
    subjects = []
    failed = []                             # subject records we got nothing for this pass

    # First pass: try every subject once (fetch_one_feed itself retries a few times).
    for subject in NEWS_SUBJECTS:
        # Keep the query too, so the renderer can ignore the subject's own words when
        # deciding which headlines are the same story (see build_news_panel).
        record = {
            "name": subject.get("name", "News"),
            "query": subject.get("query", ""),
            "items": [],
        }
        entries = fetch_one_feed(feed_url_for(record["query"]))
        if entries:
            for entry in entries:
                item = entry_to_item(entry)
                if item:
                    record["items"].append(item)
        else:
            failed.append(record)           # remember it for the retry pass
        subjects.append(record)
        time.sleep(SUBJECT_GAP_SECONDS)      # polite gap so we don't trip the rate limit

    # Second pass: give Google a longer breather, then retry only the ones that failed.
    if failed:
        time.sleep(RETRY_PASS_PAUSE)
        for record in failed:
            for entry in fetch_one_feed(feed_url_for(record["query"])):
                item = entry_to_item(entry)
                if item:
                    record["items"].append(item)
            if not record["items"]:
                # Still throttled after two tries: keep whatever this subject had last run
                # so its news doesn't disappear. The render step still hides any item not
                # published today, so genuinely old ones drop off on their own at midnight.
                record["items"] = previous.get(record["name"], [])
            time.sleep(SUBJECT_GAP_SECONDS)

    return subjects


def significant_words(headline, ignore=frozenset()):
    # Reduce a headline to the set of meaningful words we compare on: lowercase it, keep
    # only letters/numbers, drop very short words and the common stopwords above. Returns a
    # set, so comparing two headlines is just checking how many words they share.
    # `ignore` is an extra set to drop — used to remove a subject's OWN words (e.g. "half",
    # "life", "3" for the Half-Life 3 subject), which every headline there shares and which
    # would otherwise collapse all its different stories into one. Keep digits like "3".
    words = re.findall(r"[a-z0-9]+", headline.lower())   # e.g. "Half-Life 3!" -> half life 3
    keep = {w for w in words if (len(w) >= 3 or w.isdigit()) and w not in STOPWORDS}
    return keep - ignore


def same_story(words_a, words_b):
    # Crude "are these the same story?" test: they must share at least two meaningful words,
    # AND those shared words must be a decent fraction of the shorter headline (so two
    # unrelated stories that happen to share one big word aren't wrongly merged). Deliberately
    # simple for v1 — it will occasionally over- or under-merge, which is why the source
    # count is shown as a rough signal, not a precise fact.
    if not words_a or not words_b:
        return False
    shared = words_a & words_b
    if len(shared) < 2:
        return False
    return len(shared) / min(len(words_a), len(words_b)) >= 0.4


def cluster_stories(items, ignore_words=frozenset()):
    # Group a subject's items into "stories": each story is a bunch of items (from possibly
    # different outlets) that look like the same event. Simple greedy pass: for each item,
    # drop it into the first existing story it matches, otherwise start a new story.
    # `ignore_words` are the subject's own words, removed before comparing so we cluster on
    # the actual event rather than on the subject term every headline shares.
    stories = []
    for item in items:
        words = significant_words(item["headline"], ignore_words)
        placed = False
        for story in stories:
            if same_story(words, story["words"]):
                story["items"].append(item)
                story["words"] = story["words"] | words   # grow the story's word set
                placed = True
                break
        if not placed:
            stories.append({"words": words, "items": [item]})
    return stories


def relative_time(epoch):
    # A short "how long ago" label like "2h ago" from an epoch number. Keeps the row compact.
    diff = time.time() - epoch
    if diff < 3600:
        mins = max(1, int(diff // 60))
        return str(mins) + "m ago"
    if diff < 86400:
        return str(int(diff // 3600)) + "h ago"
    return str(int(diff // 86400)) + "d ago"


def is_today(epoch):
    # True if this article was published on today's Pacific calendar day. Same today-only
    # rule as the YouTube panel: convert the epoch to Pacific and compare the date part.
    today = datetime.now(PACIFIC).strftime("%Y-%m-%d")
    when = datetime.fromtimestamp(epoch, PACIFIC).strftime("%Y-%m-%d")
    return when == today


def build_news_panel():
    try:
        # Every subject's items, THROUGH THE CACHE (re-fetched at most every ~15 minutes).
        subjects = get_cached("news", fetch_news_data, 900)

        pieces = []
        pieces.append("<h2>News</h2>")
        # Honest "as of" stamp, like stocks/YouTube — the browser can't refresh this, so it
        # updates when Python re-runs. Notes the corroboration caveat AND that this is a
        # today-only, clean-slate-each-day widget (same as YouTube's "New Today").
        pieces.append('<p class="updated">Today · as of ' + cached_time_label("news")
                      + ' · ✓ = how many outlets ran it (a rough signal, not proof)</p>')

        # The scroll box holding every subject group. Its id lets the JavaScript find it to
        # hide stories you've dismissed today.
        pieces.append('<div class="news-list" id="news-list">')

        any_content = False
        for subject in subjects:
            # Keep only TODAY's items (Pacific), then build stories from those. Ordered
            # most-corroborated first (most distinct outlets today), most recent to break
            # ties. We ignore the subject's own words (name + query) when matching, so e.g.
            # every "Half-Life 3" headline isn't merged just because they all say it.
            todays_items = [i for i in subject["items"] if is_today(i["published_epoch"])]
            ignore = significant_words(subject["name"]) \
                | significant_words(subject.get("query", ""))
            stories = cluster_stories(todays_items, ignore)
            ranked = []
            for story in stories:
                sources = {i["source"] for i in story["items"]}            # distinct outlets
                newest = max(story["items"], key=lambda i: i["published_epoch"])
                ranked.append({
                    "headline": newest["headline"],       # show the most recent phrasing
                    "url": newest["url"],
                    "sources": sorted(sources),
                    "count": len(sources),
                    "epoch": newest["published_epoch"],
                })
            ranked.sort(key=lambda s: (s["count"], s["epoch"]), reverse=True)

            # Each subject is its own group: a heading plus today's stories (or a short
            # "nothing today" note). Wrapping them lets the JS show that note again if you
            # delete every story in a group.
            pieces.append('<div class="news-subject">')
            # Subject heading (always shown, so you can see the subject is being watched
            # even on a quiet day).
            pieces.append('<div class="news-subject-title">'
                          + html.escape(subject["name"]) + '</div>')

            if not ranked:
                pieces.append('<p class="news-empty">Nothing today.</p>')
                pieces.append('</div>')   # .news-subject
                continue

            any_content = True
            for story in ranked[:STORIES_PER_SUBJECT]:
                headline = html.escape(story["headline"], quote=True)
                url = html.escape(story["url"], quote=True)
                # Badge: green "✓ N sources" when 2+ outlets ran it, grey "1 source" when one.
                if story["count"] >= 2:
                    badge = ('<span class="news-badge multi">✓ '
                             + str(story["count"]) + ' sources</span>')
                else:
                    badge = '<span class="news-badge single">1 source</span>'
                # The sources line: which outlets carried it (capped so it stays short).
                shown = story["sources"][:3]
                more = story["count"] - len(shown)
                src_text = html.escape(", ".join(shown))
                if more > 0:
                    src_text += " +" + str(more)
                when = relative_time(story["epoch"])

                # data-newsid (the story's link) lets the JS remember which stories you
                # dismissed today, so a ✕ sticks across reloads until a new day resets it.
                pieces.append('<div class="news-story" data-newsid="' + url + '">')
                pieces.append('<a class="news-headline" href="' + url
                              + '" target="_blank" rel="noopener">' + headline + '</a>')
                pieces.append('<div class="news-sub">' + badge
                              + '<span class="news-src">' + src_text + '</span>'
                              + '<span class="news-time">' + when + '</span>'
                              # ✕ delete for just this story, for the rest of today.
                              + '<button class="news-remove" onclick="dismissNews(this)"'
                              + ' title="Remove">&#10005;</button></div>')
                pieces.append('</div>')   # .news-story

            pieces.append('</div>')   # .news-subject

        pieces.append('</div>')   # .news-list

        if not any_content:
            # No subjects configured, or nothing published today across every subject.
            return ('<h2>News</h2><p class="news-empty">No news yet today. '
                    'Check back later, or add subjects in config.json.</p>')

        return "\n".join(pieces)

    except Exception:
        # Fail soft: one broken panel must not blank the rest of the page.
        return "<h2>News</h2><p>News is unavailable right now.</p>"
