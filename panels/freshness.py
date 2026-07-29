# panels/freshness.py
# The freshness strip: the one line under the page title that answers "how old is what I'm
# looking at, and is it worth forcing a refresh right now?"
#
# Why it exists (2026-07-27): the cloud rebuild is on a timer, but GitHub drops a lot of
# scheduled runs, so the real gap between rebuilds varies from ~10 minutes to a couple of
# hours. Before this strip there was no way to tell a page that is 5 minutes old from one
# that is 3 hours old without squinting at each widget's "As of" stamp. It also stops a
# pointless manual re-run: within 15 minutes of the last fetch the panels reuse their saved
# data (see CACHE_MAX_AGE in panels/common.py), so forcing a build then would republish the
# very same videos and headlines.
#
# Python's part is only to work out the times. The live "in 7m 12s" countdown is JavaScript
# in template.html, because a number baked into a static file would start going stale the
# instant it was written.

import json

# cache_status tells us when one source was last fetched and when its saved copy goes
# stale. CACHE_MAX_AGE is the 15-minute rule itself, shared with the panels so the
# countdown can never disagree with what the panels actually do.
from panels.common import cache_status, CACHE_MAX_AGE

# The address of this project's build in the Actions tab. The strip links to it so Eli can
# start a rebuild from his phone — a page served as a plain file cannot run Python itself,
# and triggering a build from the page would need a GitHub token, which anyone could read
# out of a public page and use.
RUN_WORKFLOW_URL = "https://github.com/24EMK24/dashboard/actions/workflows/build.yml"

# The cached sources to report on, in the order they should appear. Each is the cache name
# the panel passes to get_cached(), paired with a friendlier label for the page. Weather is
# absent on purpose: it is not cached, and its Refresh button re-fetches it live.
#
# SCORES is left out on purpose too, and it is worth saying why. This strip answers one
# question — "would forcing a rebuild fetch new videos and headlines, or just republish the
# same ones?" — by counting down to whichever cache expires first. Scores are kept for only
# 5 minutes (see SCORES_MAX_AGE in panels/scores.py), so including them would leave the
# countdown reading "Ready" almost permanently and it would stop telling Eli anything
# useful about YouTube and news. The scores card carries its own "As of" stamp instead.
SOURCES = [
    ("youtube", "YouTube"),
    ("news", "News"),
    ("stocks", "Stocks"),
]


def build_freshness_strip():
    try:
        statuses = [dict(cache_status(name), display=label) for name, label in SOURCES]

        pieces = []
        pieces.append('<div class="fresh-strip">')

        # One "YouTube 5:12 PM" chip per source, so a single lagging feed is obvious.
        pieces.append('<span class="fresh-items">')
        for status in statuses:
            pieces.append('<span class="fresh-item">' + status["display"]
                          + ' <b>' + status["label"] + '</b></span>')
        pieces.append('</span>')

        # The countdown. JavaScript rewrites this text every second; the words here are
        # only what shows in the split second before the script first runs.
        pieces.append('<span class="fresh-next" id="fresh-next">checking…</span>')

        # The manual-rebuild link. rel="noopener" is the usual safety habit for target=_blank.
        pieces.append('<a class="fresh-run" href="' + RUN_WORKFLOW_URL
                      + '" target="_blank" rel="noopener">Run a rebuild &#8599;</a>')

        # Hand the raw numbers to the JavaScript. json.dumps turns our list of dicts into
        # the text form of a JavaScript array, which the script below reads back out of
        # this element's data-sources attribute. It contains only times we generated
        # ourselves — no user text — so there is nothing here that could break the HTML.
        pieces.append('<span id="fresh-data" data-sources=\''
                      + json.dumps(statuses)
                      + '\' data-max-age="' + str(CACHE_MAX_AGE) + '"></span>')

        pieces.append('</div>')
        return "\n".join(pieces)

    except Exception:
        # Fail soft like every panel: the strip is a convenience, and it must never be the
        # reason the dashboard fails to build.
        return ""
