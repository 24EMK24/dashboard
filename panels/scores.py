# panels/scores.py
# The score keeper strip at the top of the page: one small card per team Eli follows
# (the Mariners and the Seahawks), showing whichever of these matters right now —
#   * a game in progress, with the live score and the inning/quarter
#   * the last three finished games
#   * the team's record and where it sits in its division
#   * when the next game starts
#
# ===========================================================================
# THIS FILE NO LONGER FETCHES ANYTHING. THE BROWSER DOES. (changed 2026-09-01)
# ===========================================================================
# It used to ask ESPN for the scores here, while the page was being built on GitHub's
# machines, and then bake the finished numbers into the HTML. That stopped working:
#
#   * From 2026-08-04 onward the panel was DEAD on the live page — both cards read
#     "Scores unavailable right now." for four solid weeks. The same code fetched ESPN
#     perfectly from Eli's laptop the whole time (checked again 2026-09-01: HTTP 200,
#     Mariners 64-74, 3rd in AL West). ESPN appears to refuse GitHub's runner IPs, and
#     nothing we can write on this side changes whose machine the build runs on.
#   * Even when it DID work, a baked-in score was only as fresh as the last rebuild, and
#     the rebuild cadence is measured at about 16% of what the schedule asks for, with
#     gaps as long as 12.5 hours. A twelve-hour-old "live" score is not a live score.
#
# So the fetch moved to the one machine that is definitely allowed to ask and is
# definitely up to date: Eli's own browser. Two things make that possible —
#
#   1. ESPN sends "Access-Control-Allow-Origin: *" on these addresses, which is the
#      permission slip a browser needs before it will hand a page data from another
#      site. (Verified 2026-09-01 by sending an Origin header from this project's real
#      address. Without that header a browser refuses the reply even though the server
#      answered fine, so this was worth checking before committing to the design.)
#   2. The payload is small once compressed. The MLB season schedule looks alarming at
#      2.6 MB of text, but it travels as 92 KB because the server gzips it and every
#      browser asks for that automatically; the NFL one is 4 KB. Both teams together
#      cost roughly 96 KB per page load, which is fine on a phone.
#
# What is left in this file is the SHELL: an empty card per team, carrying the few facts
# the browser needs to go and ask (which sport, which league, which team). The fetching,
# the parsing and the filling-in all happen in template.html's script — and that script
# is a close translation of the Python that used to live here, which had been verified
# against real live games, rather than a fresh guess at ESPN's shape.
#
# Consequences worth knowing:
#   * There is no cache/scores.json any more and no "As of" stamp baked at build time.
#     The card says when the browser last fetched, which is a truer answer.
#   * The Refresh button now genuinely refreshes these cards (see refreshAll in
#     template.html). Before this change it only ever refreshed the weather.
#   * If Eli opens the page with no internet, the cards say so instead of showing a
#     stale score that looks current.

# html.escape turns characters like < and & into safe text, so a team name out of
# config.json can never break the page's HTML.
import html

# The teams Eli follows, read from config.json's "sports_teams".
from panels.common import SPORTS_TEAMS

# How many finished games each card lists, newest first.
#
# Added 2026-09-01 at Eli's request — he asked to "see previous games, not all of them,
# like maybe the past three". The card used to show only the single most recent result.
# This number is also read by the browser script, which is handed it below rather than
# having its own copy, so the two can never drift apart.
PAST_GAMES_SHOWN = 3


def render_card_shell(team):
    # One empty card, ready for the browser to fill in.
    #
    # The data-* attributes are how Python passes facts to JavaScript on a static page:
    # anything written as data-something="..." on an element shows up in the script as
    # element.dataset.something. Here they carry the three words ESPN's web address
    # needs (sport / league / team, e.g. baseball / mlb / sea) plus Eli's own label for
    # the team, so the script can build the address without a second copy of the team
    # list living in template.html.
    pieces = []
    pieces.append('<div class="score-card"'
                  + ' data-sport="' + html.escape(team.get("sport", "")) + '"'
                  + ' data-league="' + html.escape(team.get("league", "")) + '"'
                  + ' data-team="' + html.escape(team.get("team", "")) + '"'
                  + ' data-name="' + html.escape(team.get("name", "")) + '">')

    # The heading is filled in now because the team's NAME is ours, not ESPN's — there is
    # no reason to make Eli wait for a network reply to find out the card says "Mariners".
    # The record/standing span next to it starts empty and the script fills it.
    pieces.append('<div class="score-head">')
    pieces.append('<span class="score-team">' + html.escape(team.get("name", "")) + '</span>')
    pieces.append('<span class="score-record"></span>')
    pieces.append('</div>')

    # Everything below the heading is replaced wholesale by the script once ESPN answers.
    # Until then it says so, rather than sitting blank and looking broken.
    pieces.append('<div class="score-body"><div class="score-empty">Loading scores…</div></div>')

    pieces.append('</div>')
    return "\n".join(pieces)


def build_scores_panel():
    try:
        # No teams configured — show nothing at all rather than an empty box.
        if not SPORTS_TEAMS:
            return ""

        pieces = []
        # data-past-games hands the browser the PAST_GAMES_SHOWN number above, so that
        # setting lives in exactly one place even though two languages use it.
        pieces.append('<div class="scores-strip" id="scores-strip"'
                      + ' data-past-games="' + str(PAST_GAMES_SHOWN) + '">')
        for team in SPORTS_TEAMS:
            pieces.append(render_card_shell(team))
        # The stamp is filled in by the script with the time IT fetched. It starts with a
        # dash rather than a time, because a time written now would be a lie about data
        # that has not been fetched yet.
        pieces.append('<div class="score-stamp" id="score-stamp">&mdash;</div>')
        pieces.append('</div>')
        return "\n".join(pieces)

    except Exception:
        # Fail soft, like every panel: a problem here must never cost Eli the rest of his
        # dashboard. (There is no network call left in this function, so about the only way
        # to land here is a malformed sports_teams entry in config.json.)
        return ('<div class="scores-strip">'
                '<div class="score-empty">Scores are unavailable right now.</div>'
                '</div>')
