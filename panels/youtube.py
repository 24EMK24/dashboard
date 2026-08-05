# panels/youtube.py
# The YouTube panel: for each channel in config.json, read its public RSS feed and show
# the videos released TODAY (Pacific time), newest first, each as a thumbnail + title
# that links to the video. Fetches all feeds THROUGH the shared cache so repeated runs
# don't re-hit YouTube. Fail soft: any breakage returns a short "unavailable" message.
#
# What this panel does NOT do here (it happens in the browser, in template.html's
# <script>): the ✕ delete button, the "clean slate on a new day" reset, and the whole
# "Watch Later" list. Those need to remember your choices between runs, and a static
# HTML file has no server to store them — so they live in the browser's localStorage.
# Python's job is only to lay out today's videos; JavaScript makes them interactive.

# "feedparser" reads RSS/Atom feeds (like YouTube's per-channel feed) and hands back the
# entries as easy Python objects. New library for this panel; no API key or quota.
import feedparser
# "requests" fetches the feed itself (same library the weather panel uses). We fetch with
# requests instead of letting feedparser download, so we can send a normal browser
# User-Agent and retry — YouTube throttles rapid plain requests otherwise.
import requests
# "time" lets us pause briefly between requests so we don't hammer YouTube.
import time
# "html" gives us html.escape(), which makes video titles safe to drop into HTML
# (turns characters like < > & " into their harmless &lt; &gt; &amp; &quot; forms).
import html
# "calendar" turns a UTC time-tuple into a plain epoch number (seconds since 1970) we
# can save as JSON and compare. datetime/ZoneInfo convert that number to Pacific time.
import calendar
# "os" and "json" let us read the PREVIOUS run's cache file directly, so a channel that
# YouTube throttles this run can keep the videos it had last run (see fetch_youtube_data).
import os
import json
from datetime import datetime
from zoneinfo import ZoneInfo

# Eli's channel list from config.json, plus the shared cache helpers. CACHE_DIR is the
# folder get_cached writes to; we read cache/youtube.json from it to carry channels over.
from panels.common import (
    YOUTUBE_CHANNELS, get_cached, cached_time_label, CACHE_DIR, CACHE_MAX_AGE,
)

# YouTube publishes one RSS feed per channel at this address; we fill in the channel id.
FEED_URL = "https://www.youtube.com/feeds/videos.xml?channel_id="

# A normal browser User-Agent. Without one, YouTube throttles the feed requests and
# starts returning errors (404/500) even for perfectly valid channels.
USER_AGENT = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Pacific time zone object, reused below. The whole dashboard works in Pacific.
PACIFIC = ZoneInfo("America/Los_Angeles")

# How long to wait between channels. A bigger gap makes YouTube far less likely to
# throttle the burst of 23 requests (it used to be 1s, which started tripping the limit).
CHANNEL_GAP_SECONDS = 2.5
# After the first pass, channels that still failed get ONE more try — but only after a
# longer cool-off, since throttling is usually brief. This recovers most stragglers.
RETRY_PASS_PAUSE = 10

# NOTE (2026-07-27): there used to be a live-stream / rerun / VOD filter here — a list of
# streamy title phrases (LIVE_MARKERS) plus an is_live_or_rerun() check applied below. It was
# REMOVED at Eli's request: he doesn't want videos hidden. It could only ever guess from the
# title anyway, because YouTube's RSS feed carries no live flag at all (verified on a
# stream-heavy channel — the XML has no "isLive"/"liveBroadcast"/"premiere" field), and on a
# real cache it was hiding 1 video out of 375. If a title-based filter is ever wanted again,
# see this file's history; catching a rerun titled like a normal upload would need the
# YouTube Data API (a key + quota).


def fetch_one_feed(channel_id):
    # Fetch a single channel's RSS and return its entries (a list). YouTube rate-limits
    # rapid requests — a throttled reply comes back as a 404/500 or empty — so on a bad
    # reply we wait a moment and try again a couple of times before giving up. Returns []
    # if it never succeeds, so one stubborn channel just contributes nothing this run.
    url = FEED_URL + channel_id
    for attempt in range(3):                       # up to 3 tries
        try:
            reply = requests.get(url, headers=USER_AGENT, timeout=15)
            if reply.status_code == 200:
                feed = feedparser.parse(reply.content)   # hand the XML to feedparser
                if feed.entries:
                    return feed.entries
        except Exception:
            pass                                   # network hiccup — fall through to retry
        # Back off before the NEXT try (2s, then 4s). No sleep after the last attempt —
        # that just wastes time on a channel we've already given up on this pass, which
        # adds up fast when many channels are being throttled at once.
        if attempt < 2:
            time.sleep(2.0 * (attempt + 1))
    return []


def entry_to_video(entry, channel_name):
    # Turn one feedparser entry into our plain, JSON-friendly dict — or None if it's
    # missing the bits we need. Pulled out of the loop so both the first pass and the
    # retry pass below build videos the exact same way.
    # yt_videoid is feedparser's name for the feed's <yt:videoId> field.
    video_id = entry.get("yt_videoid")
    # published_parsed is a UTC time-tuple. Skip any entry missing an id or a date.
    if not video_id or not entry.get("published_parsed"):
        return None
    # timegm turns that UTC time-tuple into an epoch number (seconds since 1970).
    published_epoch = calendar.timegm(entry.published_parsed)
    return {
        "video_id": video_id,
        "title": entry.get("title", "(untitled)"),
        "url": entry.get("link", "https://www.youtube.com/watch?v=" + video_id),
        # Every YouTube video has a thumbnail at this predictable address.
        "thumbnail": "https://i.ytimg.com/vi/" + video_id + "/hqdefault.jpg",
        "channel": channel_name,             # Eli's chosen display name
        "published_epoch": published_epoch,  # for sorting + the today filter
    }


def load_previous_by_channel():
    # Read the videos the LAST run saved (cache/youtube.json is a plain JSON list) and
    # group them by channel name: {channel_name: [video, ...]}. We use this to carry a
    # channel's videos forward when YouTube throttles its feed this run, so a video that
    # was showing earlier today doesn't suddenly vanish. Returns {} if there's no cache
    # yet or it can't be read — in that case there's simply nothing to carry over.
    path = os.path.join(CACHE_DIR, "youtube.json")
    previous = {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            for v in json.load(f):
                previous.setdefault(v["channel"], []).append(v)
    except Exception:
        pass
    return previous


def fetch_youtube_data():
    # Fetch every channel's feed and return a plain list of dicts (JSON-friendly, so
    # get_cached can save it). We keep the recent uploads each feed returns; deciding
    # which ones count as "today" happens later, at render time, against the current
    # date — that way the list is correct even right after midnight. This is the slow
    # part (one request per channel, with polite pauses), but it only runs when the
    # cache is stale — at most every ~15 minutes.
    #
    # YouTube throttles bursts of requests (replies come back 404/500/empty), so on any
    # given run some channels return nothing. Two things keep that from blanking them:
    #   * a second try over just the failed channels, after a longer cool-off, and
    #   * for any channel STILL failing, we reuse the videos it had last run.
    previous = load_previous_by_channel()   # last run's videos, grouped by channel
    videos = []
    failed = []                             # channels we got nothing for this pass

    # First pass: try every channel once (fetch_one_feed itself retries a few times).
    for channel in YOUTUBE_CHANNELS:
        entries = fetch_one_feed(channel["channel_id"])
        if entries:
            for entry in entries:
                video = entry_to_video(entry, channel["name"])
                if video:
                    videos.append(video)
        else:
            failed.append(channel)          # remember it for the retry pass
        time.sleep(CHANNEL_GAP_SECONDS)     # polite gap so we don't trip the rate limit

    # Second pass: give YouTube a longer breather, then retry only the ones that failed.
    if failed:
        time.sleep(RETRY_PASS_PAUSE)
        for channel in failed:
            got_this_channel = False
            for entry in fetch_one_feed(channel["channel_id"]):
                video = entry_to_video(entry, channel["name"])
                if video:
                    videos.append(video)
                    got_this_channel = True
            if not got_this_channel:
                # Still throttled after two tries: keep whatever this channel had last
                # run so its videos don't disappear. The render step still hides any
                # video not published today, so genuinely old ones drop off on their own.
                videos.extend(previous.get(channel["name"], []))
            time.sleep(CHANNEL_GAP_SECONDS)

    return videos


def build_youtube_panel():
    try:
        # All recent videos, THROUGH THE CACHE (re-fetched at most every ~15 minutes).
        videos = get_cached("youtube", fetch_youtube_data, CACHE_MAX_AGE)

        # Today's date in Pacific, as "2026-07-22". A video counts as "today" if its
        # own published time, converted to Pacific, falls on this same date.
        today = datetime.now(PACIFIC).strftime("%Y-%m-%d")
        todays = []
        for v in videos:
            when = datetime.fromtimestamp(v["published_epoch"], PACIFIC)
            if when.strftime("%Y-%m-%d") == today:
                todays.append(v)

        # Newest first: sort by the epoch number, largest (most recent) at the top.
        todays.sort(key=lambda v: v["published_epoch"], reverse=True)

        pieces = []
        pieces.append("<h2>New Today</h2>")
        # Honest "as of" stamp, like the stocks panel — the browser can't refresh this
        # (YouTube's feed can't be fetched from a page), so it updates when Python re-runs.
        pieces.append('<p class="updated">As of ' + cached_time_label("youtube")
                      + ' · re-run to refresh · new day = clean slate</p>')

        # The scroll box that holds today's video cards. JavaScript on page load hides
        # any you've already dismissed today, and shows an "all caught up" note if the
        # box ends up empty. The id lets the script find this box.
        pieces.append('<div class="yt-list" id="yt-today-list">')

        if not todays:
            # Nothing released yet today (or no channels configured).
            pieces.append('<p class="yt-empty">No new videos yet today.</p>')
        else:
            for v in todays:
                # Escape every piece of text before putting it in HTML/attributes, so a
                # title with < > & or quotes can't break the page. quote=True also
                # escapes the " and ' used around attribute values.
                title = html.escape(v["title"], quote=True)
                url = html.escape(v["url"], quote=True)
                thumb = html.escape(v["thumbnail"], quote=True)
                channel = html.escape(v["channel"], quote=True)
                vid = html.escape(v["video_id"], quote=True)

                # One card. The data-* attributes carry this video's details so the
                # JavaScript can copy them into the "Watch Later" list when its button
                # is pressed, and know which video a ✕ press is dismissing.
                pieces.append(
                    '<div class="yt-card" data-vid="' + vid + '"'
                    ' data-title="' + title + '"'
                    ' data-url="' + url + '"'
                    ' data-thumb="' + thumb + '"'
                    ' data-channel="' + channel + '">'
                )
                # Thumbnail + title both link to the video, opening in a new tab.
                # onclick="clearOnOpen(this)" ALSO takes the card off the list once you
                # open it — once a video has been watched it doesn't need to sit in the
                # list any more. It does not interfere with the link itself; the video
                # opens exactly as before. See clearOnOpen() in template.html.
                pieces.append('<a class="yt-thumb-link" href="' + url + '" target="_blank" rel="noopener"'
                              ' onclick="clearOnOpen(this)">')
                pieces.append('<img class="yt-thumb" src="' + thumb + '" alt="" loading="lazy">')
                pieces.append('</a>')
                pieces.append('<div class="yt-meta">')
                pieces.append('<a class="yt-title" href="' + url + '" target="_blank" rel="noopener"'
                              ' onclick="clearOnOpen(this)">' + title + '</a>')
                pieces.append('<div class="yt-channel">' + channel + '</div>')
                pieces.append('<div class="yt-actions">')
                # Save this card to Watch Later. onclick passes the card element (this)
                # up to a JS function that reads the data-* attributes above.
                pieces.append('<button class="yt-save" onclick="saveForLater(this)">+ Watch later</button>')
                # Dismiss just this card for the rest of today.
                pieces.append('<button class="yt-remove" onclick="dismissToday(this)" title="Remove">&#10005;</button>')
                pieces.append('</div>')   # .yt-actions
                pieces.append('</div>')   # .yt-meta
                pieces.append('</div>')   # .yt-card

        pieces.append('</div>')   # .yt-list
        return "\n".join(pieces)

    except Exception:
        # Fail soft: one broken panel must not blank the rest of the page.
        return "<h2>New Today</h2><p>YouTube is unavailable right now.</p>"
