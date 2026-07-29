# panels/scores.py
# The score keeper strip at the top of the page: one small card per team Eli follows
# (the Mariners and the Seahawks), showing whichever of these matters right now —
#   * a game in progress, with the live score and the inning/quarter
#   * the result of the most recent finished game
#   * when the next game starts
#
# Where the numbers come from: ESPN's public scoreboard service at site.api.espn.com.
# It needs NO API key and NO account, which is the same rule every other source on this
# project follows (Open-Meteo for weather, RSS for YouTube and news, yfinance for stocks).
# It is not a documented, promised-to-stay-put API though — it is the one ESPN's own site
# calls — so treat it as breakable, and let the fail-soft wrapper at the bottom handle it.
#
# One request per team gives us everything: the whole season's schedule, with final scores
# on the games already played and start times on the ones still to come.

# requests -> download a web address. json is handled by requests for us.
import requests
# html.escape turns characters like < and & into safe text, so a team name from ESPN can
# never break the page's HTML. Same habit as the YouTube and news panels.
import html
# For turning ESPN's UTC timestamps into Pacific times Eli can read.
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

# Shared bits: the teams from config.json, and the cache-to-disk helpers.
from panels.common import SPORTS_TEAMS, get_cached, cached_time_label

# Everything on this dashboard is shown in Pacific time.
PACIFIC = ZoneInfo("America/Los_Angeles")

# A browser-style User-Agent. Plain script-looking requests get refused by a lot of
# services; this is the same trick panels/youtube.py uses on the YouTube feeds.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/122.0 Safari/537.36")

# How long a fetched set of scores stays usable, in seconds.
#
# NOTE this is deliberately NOT the project-wide CACHE_MAX_AGE (900 = 15 minutes) that
# YouTube, news and stocks use. A score that is 15 minutes old is wrong in a way a
# 15-minute-old headline is not — during a live game it is several innings behind. The
# 15-minute rule exists because YouTube and Google throttle us for fetching too often;
# ESPN is two small requests here, so there is nothing to protect against.
SCORES_MAX_AGE = 300   # 5 minutes

# How many times to retry one team's request, and how long to wait between tries.
MAX_TRIES = 3
RETRY_PAUSE_SECONDS = 2


def parse_espn_time(text):
    # Turn ESPN's timestamp ("2026-07-29T02:10Z") into a Pacific-time datetime.
    # The trailing "Z" means UTC; Python's parser wants "+0000" instead. ESPN sometimes
    # includes seconds and sometimes doesn't, so we try both shapes and give up quietly
    # (returning None) rather than crashing the whole strip over a formatting change.
    if not text:
        return None
    text = text.replace("Z", "+0000")
    for shape in ("%Y-%m-%dT%H:%M%z", "%Y-%m-%dT%H:%M:%S%z"):
        try:
            return datetime.strptime(text, shape).astimezone(PACIFIC)
        except ValueError:
            continue
    return None


def read_game(event, our_abbreviation):
    # Pull the handful of facts we care about out of one of ESPN's game records.
    # Returns a small plain dict (numbers and text only) so get_cached can save it as
    # JSON, or None if the record isn't shaped the way we expect.
    #
    # An ESPN "event" is one game. Its details live in event["competitions"][0], and the
    # two teams are that competition's "competitors" list.
    competitions = event.get("competitions") or []
    if not competitions:
        return None
    competition = competitions[0]

    competitors = competition.get("competitors") or []
    if len(competitors) != 2:
        return None

    # Work out which of the two is our team and which is the opponent.
    ours = None
    theirs = None
    for side in competitors:
        abbreviation = (side.get("team") or {}).get("abbreviation")
        if abbreviation == our_abbreviation:
            ours = side
        else:
            theirs = side
    if ours is None or theirs is None:
        return None

    def score_of(side):
        # A finished or in-progress game has a score; a scheduled one has none at all.
        # ESPN gives it as {"value": 4.0, "displayValue": "4"} — we want the plain text.
        score = side.get("score")
        if isinstance(score, dict):
            return score.get("displayValue")
        return None

    # "status.type.state" is ESPN's word for where the game is up to:
    #   "pre"  = not started yet
    #   "in"   = being played right now
    #   "post" = finished
    status_type = (competition.get("status") or {}).get("type") or {}
    state = status_type.get("state")

    starts_at = parse_espn_time(event.get("date"))

    return {
        "state": state,
        # "shortDetail" is ESPN's own summary of the moment: "Final", "Bot 7th", "Q3 5:42".
        "detail": status_type.get("shortDetail") or status_type.get("description") or "",
        # The opponent's short name ("Dodgers") and letter code ("LAD").
        "opponent": (theirs.get("team") or {}).get("shortDisplayName") or "",
        "opponent_abbreviation": (theirs.get("team") or {}).get("abbreviation") or "",
        # Whether WE are the home team, so the card can say "vs" or "@".
        "at_home": ours.get("homeAway") == "home",
        "our_score": score_of(ours),
        "their_score": score_of(theirs),
        # True/False on a finished game, None before it is played.
        "won": ours.get("winner"),
        # Store the start time as a plain number of seconds (an "epoch" time) rather than
        # as finished text. The card says things like "Tonight" and "Tomorrow", and a
        # phrase like that baked in at fetch time would be wrong after midnight.
        "starts_at": starts_at.timestamp() if starts_at else None,
    }


def fetch_one_team(team):
    # Fetch one team's season and reduce it to just the three games we might show.
    # "team" is one entry from config.json's sports_teams list.
    address = ("https://site.api.espn.com/apis/site/v2/sports/"
               + team["sport"] + "/" + team["league"]
               + "/teams/" + team["team"] + "/schedule")

    # Try a few times: a single hiccup shouldn't cost us the card. Anything still failing
    # after the last try raises, and the caller below turns that into a quiet "unavailable".
    response = None
    for attempt in range(MAX_TRIES):
        try:
            response = requests.get(address, headers={"User-Agent": USER_AGENT}, timeout=25)
            response.raise_for_status()   # treat a 404/500 reply as a failure, not success
            break
        except Exception:
            if attempt == MAX_TRIES - 1:
                raise
            # Wait a moment before trying again, a little longer each time.
            import time
            time.sleep(RETRY_PAUSE_SECONDS * (attempt + 1))

    data = response.json()

    # The response's own "team" block carries the season record and league position.
    team_block = data.get("team") or {}
    our_abbreviation = team_block.get("abbreviation") or team["team"].upper()

    # Sort every game in the season into finished / playing now / still to come.
    played = []
    playing_now = None
    upcoming = []
    for event in data.get("events") or []:
        game = read_game(event, our_abbreviation)
        if game is None:
            continue
        if game["state"] == "post":
            played.append(game)
        elif game["state"] == "in":
            playing_now = game
        elif game["state"] == "pre":
            upcoming.append(game)

    return {
        "name": team["name"],                       # Eli's own label, e.g. "Mariners"
        "abbreviation": our_abbreviation,
        "record": team_block.get("recordSummary") or "",      # e.g. "52-55"
        "standing": team_block.get("standingSummary") or "",  # e.g. "3rd in AL West"
        # Only show the record once the season has actually started. Out of season ESPN
        # still reports LAST season's record (the Seahawks read "14-3" in July), which
        # sitting next to a September fixture would look like this year's result.
        "show_record": len(played) > 0,
        "live": playing_now,
        "last": played[-1] if played else None,     # the most recently finished game
        "next": upcoming[0] if upcoming else None,  # the soonest one still to come
    }


def fetch_scores_data():
    # Fetch every team Eli follows. One team failing must not cost us the other, so each
    # is wrapped on its own and a failure becomes a card that says so.
    results = []
    for team in SPORTS_TEAMS:
        try:
            results.append(fetch_one_team(team))
        except Exception:
            results.append({"name": team.get("name", "Team"), "failed": True})
    return results


# ---------------------------------------------------------------------------
# Turning the data into the little cards
# ---------------------------------------------------------------------------

def when_label(epoch_seconds):
    # A short, friendly Pacific-time label for when a game starts: "Tonight 7:10 PM",
    # "Tomorrow 1:05 PM", or "Sat Aug 2 6:40 PM" for anything further out.
    # Worked out at render time, not fetch time, so it can't be left saying "Tonight"
    # about yesterday.
    if not epoch_seconds:
        return ""
    when = datetime.fromtimestamp(epoch_seconds, PACIFIC)
    now = datetime.now(PACIFIC)

    # .date() compares calendar days, ignoring the time of day.
    days_away = (when.date() - now.date()).days
    # .lstrip("0") turns "07:10 PM" into "7:10 PM".
    clock = when.strftime("%I:%M %p").lstrip("0")

    if days_away == 0:
        return "Today " + clock
    if days_away == 1:
        return "Tomorrow " + clock
    return when.strftime("%a %b ") + str(when.day) + " " + clock


def past_label(epoch_seconds):
    # "Mon Jul 27" — the day a finished game was played.
    if not epoch_seconds:
        return ""
    when = datetime.fromtimestamp(epoch_seconds, PACIFIC)
    return when.strftime("%a %b ") + str(when.day)


def opponent_label(game):
    # "vs Dodgers" when we're at home, "@ Dodgers" when we're away — the usual shorthand.
    separator = "vs " if game["at_home"] else "@ "
    return separator + html.escape(game["opponent"])


def render_game_line(game, is_live):
    # The one line of a card that carries the score. Live games get the score plus
    # whatever ESPN says about the moment ("Bot 7th"); finished games get a W or L.
    pieces = []

    our_score = game.get("our_score")
    their_score = game.get("their_score")

    if is_live:
        pieces.append('<span class="score-pill score-live">LIVE</span>')
    elif game.get("won") is True:
        pieces.append('<span class="score-pill score-win">W</span>')
    elif game.get("won") is False:
        pieces.append('<span class="score-pill score-loss">L</span>')
    else:
        # A finished game with no winner recorded — a tie, or a postponement.
        pieces.append('<span class="score-pill">&mdash;</span>')

    # The score itself, our number first so it reads the way Eli would say it.
    if our_score is not None and their_score is not None:
        pieces.append('<span class="score-nums">' + html.escape(str(our_score))
                      + '&ndash;' + html.escape(str(their_score)) + '</span>')

    pieces.append('<span class="score-vs">' + opponent_label(game) + '</span>')

    # For a live game the inning/quarter matters; for a finished one the date does.
    if is_live:
        trailing = html.escape(game.get("detail") or "")
    else:
        trailing = past_label(game.get("starts_at"))
    if trailing:
        pieces.append('<span class="score-when">' + trailing + '</span>')

    return '<div class="score-line">' + "".join(pieces) + '</div>'


def render_team_card(team):
    pieces = []
    pieces.append('<div class="score-card">')

    # Heading: the team name, plus the record once the season is underway.
    pieces.append('<div class="score-head">')
    pieces.append('<span class="score-team">' + html.escape(team.get("name", "")) + '</span>')
    if team.get("show_record") and team.get("record"):
        # html.escape runs on each piece BEFORE the &middot; is added, so the separator
        # stays a real HTML entity instead of being turned into literal text.
        record_text = html.escape(team["record"])
        if team.get("standing"):
            record_text += " &middot; " + html.escape(team["standing"])
        pieces.append('<span class="score-record">' + record_text + '</span>')
    pieces.append('</div>')

    if team.get("failed"):
        # This one team's fetch failed; the others still show.
        pieces.append('<div class="score-empty">Scores unavailable right now.</div>')
        pieces.append('</div>')
        return "\n".join(pieces)

    live = team.get("live")
    last = team.get("last")
    upcoming = team.get("next")

    # A game happening right now beats everything else — that is the whole point of the
    # strip. Otherwise show how the last one ended.
    if live:
        pieces.append(render_game_line(live, is_live=True))
    elif last:
        pieces.append(render_game_line(last, is_live=False))

    # And always say what's next, so the card is useful on a day with no game.
    if upcoming:
        pieces.append('<div class="score-next">Next: ' + opponent_label(upcoming)
                      + ' &middot; ' + when_label(upcoming.get("starts_at")) + '</div>')
    elif not live and not last:
        pieces.append('<div class="score-empty">No games scheduled.</div>')

    pieces.append('</div>')
    return "\n".join(pieces)


def build_scores_panel():
    try:
        # No teams configured — show nothing at all rather than an empty box.
        if not SPORTS_TEAMS:
            return ""

        scores = get_cached("scores", fetch_scores_data, SCORES_MAX_AGE)

        pieces = []
        pieces.append('<div class="scores-strip">')
        for team in scores:
            pieces.append(render_team_card(team))
        # Honest "as of" stamp, read from the cache file's own age — the same habit the
        # stocks and YouTube widgets follow.
        pieces.append('<div class="score-stamp">As of ' + cached_time_label("scores") + '</div>')
        pieces.append('</div>')
        return "\n".join(pieces)

    except Exception:
        # Fail soft, like every panel: a broken score service must never cost Eli the
        # rest of his dashboard.
        return ('<div class="scores-strip">'
                '<div class="score-empty">Scores are unavailable right now.</div>'
                '</div>')
