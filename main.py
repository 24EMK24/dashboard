# main.py
# The real dashboard, version 1. This is the entry point: it builds each panel, drops
# the panels' HTML into template.html, and writes the finished dashboard.html that Eli
# opens in a browser.
#
# The panels themselves live in the panels/ package (panels/weather.py, panels/stocks.py,
# panels/youtube.py), and the page shell (all the CSS and JavaScript) lives in
# template.html. Splitting them out keeps this file short and each part easy to find.
#
# Run it from the project root:  python main.py

# Each panel is one function that fetches its own data and returns a chunk of HTML.
from panels.weather import build_weather_panel
from panels.stocks import build_stocks_panel
from panels.youtube import build_youtube_panel
from panels.news import build_news_panel
# The score keeper strip at the top: Mariners and Seahawks scores.
from panels.scores import build_scores_panel
# The little "how old is this data" strip under the page title. Not a panel of its own —
# it reports on when the other panels last fetched.
from panels.freshness import build_freshness_strip
# Location constants for the weather widget's heading and its live-update JavaScript.
from panels.common import LOCATION_NAME, LATITUDE, LONGITUDE

# Build each panel's HTML. Each panel is independent and fails soft on its own, so one
# broken panel returns an "unavailable" message instead of stopping the others.
weather_html = build_weather_panel()
stocks_html = build_stocks_panel()
youtube_html = build_youtube_panel()
news_html = build_news_panel()
scores_html = build_scores_panel()
# Built LAST, and the order matters: it reports when each cache file was written, so it has
# to run after the panels above have had their chance to refresh those files.
freshness_html = build_freshness_strip()

# Read the page shell. It uses simple __TOKENS__ that we swap for real values below with
# .replace(). We do it this way (instead of .format()) because the CSS and the <script>
# are full of { } braces, and .format() would treat every one of those as a placeholder.
with open("template.html", "r", encoding="utf-8") as f:
    page = f.read()

# Swap each token for its real value. LAT/LON go straight into the JavaScript as numbers;
# the big blocks are the panel HTML we built above.
page = page.replace("__LAT__", str(LATITUDE))
page = page.replace("__LON__", str(LONGITUDE))
page = page.replace("__LOCATION_NAME__", LOCATION_NAME)
page = page.replace("__WEATHER_BODY__", weather_html)
page = page.replace("__STOCKS__", stocks_html)
page = page.replace("__YOUTUBE__", youtube_html)
page = page.replace("__NEWS__", news_html)
page = page.replace("__SCORES__", scores_html)
page = page.replace("__FRESHNESS__", freshness_html)

# Write the finished page to dashboard.html. "w" means create-or-overwrite. The "with"
# block makes sure the file is closed properly once writing is done.
with open("dashboard.html", "w", encoding="utf-8") as f:
    f.write(page)

# A confirmation line in the terminal so Eli knows the run finished.
print("Wrote dashboard.html — open it in a browser to see the dashboard.")
