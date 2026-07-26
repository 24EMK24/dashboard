# panels/weather.py
# The Weather panel: fetches Open-Meteo and returns a chunk of HTML (a big "right now"
# card, then the coming hours). Moved out of main.py when the project was split into a
# panels/ package; the logic is unchanged.

# "requests" fetches things from the internet.
import requests
# Eli's location comes from config.json, loaded once in panels/common.py.
from panels.common import LATITUDE, LONGITUDE

# ---------------------------------------------------------------------------
# Small weather helpers (shared by the panel below)
# ---------------------------------------------------------------------------
# NOTE: the browser "Update" button re-does this same work in JavaScript in
# template.html. The two versions must stay in sync — if you change the emoji list
# or the time format here, change it in the <script> too. They are kept side by
# side on purpose so it's obvious they mirror each other.

def weather_label(code):
    # Open-Meteo describes conditions as a number ("weather code"). This turns that
    # number into an emoji + short words. Ranges cover related codes in one line.
    if code == 0:
        return ("☀️", "Clear")           # sun
    if code <= 2:
        return ("⛅", "Partly cloudy")          # sun behind cloud
    if code == 3:
        return ("☁️", "Overcast")         # cloud
    if code in (45, 48):
        return ("\U0001f32b️", "Fog")             # fog
    if 51 <= code <= 57:
        return ("\U0001f326️", "Drizzle")          # sun/rain
    if 61 <= code <= 67:
        return ("\U0001f327️", "Rain")             # rain cloud
    if 71 <= code <= 77:
        return ("❄️", "Snow")             # snowflake
    if 80 <= code <= 82:
        return ("\U0001f326️", "Showers")          # sun/rain
    if 85 <= code <= 86:
        return ("❄️", "Snow showers")     # snowflake
    if code >= 95:
        return ("⛈️", "Thunderstorm")     # storm cloud
    return ("\U0001f321️", "—")                # thermometer / dash fallback


def to_ampm(clock):
    # Turn a 24-hour clock string like "14:00" into a friendly "2 PM".
    hour_num = int(clock[:2])                    # the "14" part as a number
    suffix = "AM" if hour_num < 12 else "PM"     # before noon vs after
    display = hour_num % 12                       # 13 -> 1, 14 -> 2, 0 stays 0
    if display == 0:
        display = 12                              # 0 and 12 should both read "12"
    return str(display) + " " + suffix


# ---------------------------------------------------------------------------
# Weather panel
# ---------------------------------------------------------------------------
# Fetches the weather and returns a chunk of HTML: a big "right now" card, then
# the coming hours. It returns only the inner content — the heading and the
# Update button live in the page template. Fail soft: if anything breaks it
# returns a short "unavailable" message so the rest of the page still builds.
def build_weather_panel():
    try:
        # The web address we ask for data. The settings after "?" tell the server:
        #   latitude / longitude          -> where on Earth
        #   current=...                   -> a single "right now" reading
        #   hourly=...                    -> the same values hour by hour
        #     temperature_2m              = air temperature
        #     precipitation_probability   = chance of rain, as a percent
        #     weather_code                = the condition number weather_label reads
        #   temperature_unit=fahrenheit   -> temperatures in Fahrenheit
        #   timezone=America/Los_Angeles  -> every time comes back in Pacific time.
        url = (
            "https://api.open-meteo.com/v1/forecast"
            "?latitude=" + str(LATITUDE) +
            "&longitude=" + str(LONGITUDE) +
            "&current=temperature_2m,weather_code" +
            "&hourly=temperature_2m,precipitation_probability,weather_code" +
            "&temperature_unit=fahrenheit" +
            "&timezone=America/Los_Angeles"
        )

        # Fetch the URL and turn the reply into Python data (dicts and lists).
        data = requests.get(url).json()
        current = data["current"]     # the "right now" reading
        hourly = data["hourly"]       # the hour-by-hour lists

        # Four lists, all lined up by hour: timestamps, temps, rain chances, codes.
        times = hourly["time"]
        temperatures = hourly["temperature_2m"]
        rain_chances = hourly["precipitation_probability"]
        codes = hourly["weather_code"]

        # Find where "now" starts in the hourly lists so we skip hours already gone.
        # current["time"] looks like "2026-07-22T14:30"; cutting it to "...T14:00"
        # gives the top of the current hour. We walk forward until the hourly
        # timestamp reaches that hour, and list from there.
        current_hour = current["time"][:13] + ":00"
        start = 0
        while start < len(times) and times[start] < current_hour:
            start += 1

        # The big "right now" card.
        now_emoji, now_text = weather_label(current["weather_code"])
        updated = to_ampm(current["time"][11:])           # "2 PM"
        # Rain chance for now = the current hour's hourly value (the "current" block
        # doesn't carry a rain percentage). Guard against a missing value with 0.
        now_rain = 0
        if start < len(rain_chances) and rain_chances[start] is not None:
            now_rain = rain_chances[start]

        pieces = []
        pieces.append('<p class="updated">Updated ' + updated + '</p>')
        pieces.append('<div class="hero">')
        pieces.append('<div class="hero-emoji">' + now_emoji + '</div>')
        pieces.append('<div class="hero-main">')
        pieces.append('<div class="hero-temp">' + str(round(current["temperature_2m"])) + '°</div>')
        pieces.append('<div class="hero-cond">' + now_text + '</div>')
        pieces.append('<div class="hero-rain">Rain ' + str(now_rain) + '%</div>')
        pieces.append('</div></div>')

        # The coming hours: the next 24, as small cards. current_day remembers which
        # date we're listing so we can drop a date label whenever the day changes.
        pieces.append('<div class="hours">')
        current_day = ""
        for hour in range(start, min(start + 24, len(times))):
            day_part = times[hour][:10]        # "2026-07-22"
            clock_part = times[hour][11:]      # "14:00"

            if day_part != current_day:
                pieces.append('<div class="day-label">' + day_part + '</div>')
                current_day = day_part

            emoji, _ = weather_label(codes[hour])
            # Guard a missing rain value the same way as above.
            rain = rain_chances[hour] if rain_chances[hour] is not None else 0

            pieces.append('<div class="hour">')
            pieces.append('<div class="hour-time">' + to_ampm(clock_part) + '</div>')
            pieces.append('<div class="hour-emoji">' + emoji + '</div>')
            pieces.append('<div class="hour-temp">' + str(round(temperatures[hour])) + '°</div>')
            pieces.append('<div class="hour-rain">' + str(rain) + '%</div>')
            pieces.append('</div>')
        pieces.append('</div>')

        return "\n".join(pieces)

    except Exception:
        # Any failure at all (no internet, bad reply, missing field) lands here.
        return "<p>Weather is unavailable right now.</p>"
