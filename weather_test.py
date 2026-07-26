# weather_test.py
# The smallest real thing: ask Open-Meteo for the weather at Eli's location and
# print the next 24 hours of temperature to the terminal. This is a throwaway
# learning script — it is NOT the real dashboard. It exists to prove one loop:
# build a web address, fetch it, read the answer, use the answer.

# "requests" is a library (a bundle of ready-made code) for fetching things from
# the internet. Importing it makes its tools available below.
import requests

# Eli's location, as latitude and longitude. Open-Meteo needs coordinates, not a
# city name. These are the Seattle placeholder values from the design doc; swap
# them for Eli's real coordinates later.
latitude = 47.61
longitude = -122.33

# The web address (URL) we will ask for data. Everything after the "?" is a list
# of settings the server reads:
#   latitude / longitude  -> where on Earth we want the forecast
#   hourly=temperature_2m -> give us the temperature, hour by hour
#                            ("2m" just means measured 2 metres above the ground)
#   temperature_unit=fahrenheit -> return the numbers in Fahrenheit, not Celsius
url = (
    "https://api.open-meteo.com/v1/forecast"
    "?latitude=" + str(latitude) +
    "&longitude=" + str(longitude) +
    "&hourly=temperature_2m" +
    "&temperature_unit=fahrenheit"
)

# Send the request over the internet and wait for the server's reply. The reply
# is stored in "response". This is the actual fetch — the one line that talks to
# the outside world.
response = requests.get(url)

# The reply arrives as one long block of text in a format called JSON (a common
# way servers package data). ".json()" reads that text and turns it into Python
# data we can pick apart — here, nested dictionaries and lists.
data = response.json()

# Inside the reply, everything hourly sits under the "hourly" key. From there:
#   "time"           -> a list of timestamps, one per hour ("2026-07-21T00:00", ...)
#   "temperature_2m" -> a list of temperatures, lined up with those same hours
times = data["hourly"]["time"]
temperatures = data["hourly"]["temperature_2m"]

# Print a small header so the output is easy to read.
print("Next 24 hours of temperature for lat", latitude, "lon", longitude)

# Walk through the first 24 hours. range(24) gives the numbers 0,1,2,...,23, and
# we use each number to pull the matching time and temperature from the two lists.
for hour in range(24):
    # times[hour] and temperatures[hour] are the pair for this hour. We print the
    # time, a dash, then the temperature with an "F" so the unit is obvious.
    print(times[hour], "-", temperatures[hour], "F")
