# panels/stocks.py
# The Stocks panel: for each ticker, show the latest price, today's change (green/red),
# and a small inline-SVG sparkline of the day's prices. Fetches THROUGH the shared cache
# so repeated runs don't re-hit Yahoo. Moved out of main.py during the panels/ split;
# the logic is unchanged.

#
# SINCE 2026-11-09 THESE ROWS ARE THE BACKUP, NOT THE MAIN SOURCE. The page's JavaScript
# asks Yahoo again (through the Cloudflare relay, relay/worker.js) every time it opens,
# and replaces each row with a fresh one. These build-time rows are what shows if the
# relay is down, and they stay for any symbol the relay could not get.
# Also since then the list is the S&P 500 and the Nasdaq (Eli's choice) rather than three
# single companies, and each entry in config.json carries a display name.

# "yfinance" fetches stock prices from Yahoo Finance. No API key or account needed.
import yfinance as yf
# "html" makes names safe to put in the page; "json" hands the list to the browser.
import html
import json
# Shared bits: the tickers from config.json, the relay address, and the cache helpers.
from panels.common import TICKERS, get_cached, cached_time_label, CACHE_MAX_AGE, YOUTUBE_RELAY


def ticker_list():
    # The tickers as a list of {"name", "symbol"} dicts. config.json used to hold plain
    # symbols like "AAPL", so a plain string is still accepted and used as its own name.
    result = []
    for entry in TICKERS:
        if isinstance(entry, str):
            result.append({"name": entry, "symbol": entry})
        else:
            symbol = entry.get("symbol", "")
            result.append({"name": entry.get("name", symbol), "symbol": symbol})
    return result


def format_price(symbol, price):
    # "7,549.94" — with thousands commas. A "$" in front only for a company's shares:
    # an index (its symbol starts with "^", like ^GSPC) is measured in points, not dollars.
    text = "{:,.2f}".format(price)
    return text if symbol.startswith("^") else "$" + text

# ---------------------------------------------------------------------------
# Small stock helpers (shared by the panel below)
# ---------------------------------------------------------------------------

def get_stock_prices(ticker):
    # Return today's prices as a plain list of numbers, for drawing the sparkline.
    # ".history(...)" asks Yahoo for past prices: period="1d" = today, interval="15m"
    # = a reading every 15 minutes. If the market is closed (weekend/holiday) today
    # can be empty, so we fall back to the last few days, one point per day. If even
    # that is empty we return [] and the chart is simply skipped.
    history = ticker.history(period="1d", interval="15m")
    if history.empty:
        history = ticker.history(period="5d", interval="1d")
    if history.empty:
        return []
    # "Close" is the price column; .tolist() turns it into an ordinary Python list.
    return history["Close"].tolist()


def sparkline_svg(prices, going_up):
    # Draw a tiny line chart (a "sparkline") from a list of prices and return it as
    # an SVG string — SVG is just text that a browser draws as shapes. Returns ""
    # if there aren't enough points to draw a line.
    if not prices or len(prices) < 2:
        return ""

    width = 150          # the drawing's own coordinate width...
    height = 40          # ...and height. CSS sizes how big it actually appears.
    pad = 4              # keep the line a few units off the top and bottom edges

    low = min(prices)
    high = max(prices)
    span = high - low
    if span == 0:        # a perfectly flat line would divide by zero below
        span = 1

    # Turn each price into an "x,y" point. x steps evenly left→right across the
    # width. y is flipped (SVG's y grows downward), so a higher price sits higher up.
    points = []
    for i in range(len(prices)):
        x = i / (len(prices) - 1) * width
        y = pad + (1 - (prices[i] - low) / span) * (height - 2 * pad)
        points.append(str(round(x, 1)) + "," + str(round(y, 1)))

    # Green line if the stock is up on the day, red if down — matches the number.
    colour = "#1a9e5f" if going_up else "#d64545"
    return (
        '<svg class="spark" viewBox="0 0 ' + str(width) + ' ' + str(height) + '" '
        'preserveAspectRatio="none">'
        '<polyline points="' + " ".join(points) + '" fill="none" '
        'stroke="' + colour + '" stroke-width="2" '
        'stroke-linejoin="round" stroke-linecap="round"/>'
        '</svg>'
    )


def fetch_stocks_data():
    # Fetch every ticker's numbers and return them as a plain list of dicts — data
    # that get_cached can save as JSON. (Turning it into HTML happens later, in the
    # panel.) float(...) forces plain Python floats, because yfinance sometimes hands
    # back a special number type that json can't save.
    results = []
    for entry in ticker_list():
        symbol = entry["symbol"]
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        results.append({
            "symbol": symbol,
            "name": entry["name"],                   # what the row is labelled with
            "price": float(info.last_price),         # most recent trade price
            "previous": float(info.previous_close),  # yesterday's closing price
            "prices": get_stock_prices(ticker),      # list of prices for the sparkline
        })
    return results


# ---------------------------------------------------------------------------
# Stocks panel
# ---------------------------------------------------------------------------
# Same shape as the weather panel: fetch the data, build an HTML string, return
# it, and fail soft if anything breaks. For each ticker we show its latest price,
# how much it moved today, and colour the row green (up) or red (down).
def build_stocks_panel():
    try:
        # Get the stock numbers THROUGH THE CACHE: if we fetched less than 15 minutes
        # (900 seconds) ago, reuse the saved copy instead of hitting Yahoo again.
        stocks = get_cached("stocks", fetch_stocks_data, CACHE_MAX_AGE)

        pieces = []
        pieces.append("<h2>Stocks</h2>")
        # Honest "as of" time = when the cached data was actually fetched (the cache
        # file's age), not now. Stocks don't refresh from the browser button (that
        # only re-fetches weather); a run re-fetches them once the cache passes 15 min.
        # The id lets the browser replace this line with "Live · checked <time>" once it
        # has fetched fresh prices through the relay.
        pieces.append('<p class="updated" id="stocks-stamp">From the build at '
                      + cached_time_label("stocks") + '</p>')
        # What the browser needs to fetch the same symbols live: the relay's address and
        # the list. Same pattern as the YouTube panel's yt-live-config.
        pieces.append('<div id="stocks-live-config" hidden'
                      ' data-relay="' + html.escape(YOUTUBE_RELAY, quote=True) + '"'
                      ' data-tickers="' + html.escape(json.dumps(ticker_list()), quote=True)
                      + '"></div>')
        # The list scrolls inside itself if there are lots of tickers, so the widget
        # stays a fixed compact height (see the CSS for .stocks-list).
        pieces.append('<div class="stocks-list" id="stocks-list">')

        # Each entry in "stocks" is one ticker's saved numbers (from fetch_stocks_data).
        # Only rows for symbols still in config.json — the cache may be from before a change.
        wanted = [t["symbol"] for t in ticker_list()]
        for row in stocks:
            if row["symbol"] not in wanted:
                continue
            symbol = row["symbol"]
            price = row["price"]          # most recent trade price
            previous = row["previous"]    # yesterday's closing price

            # Today's change: how far the price moved from yesterday's close, and
            # that move as a percentage. round(...) trims the long decimals.
            change = round(price - previous, 2)
            percent = round((change / previous) * 100, 2)

            # up on the day? drives the colour and the sparkline's colour.
            going_up = change >= 0
            colour = "green" if going_up else "red"
            # A leading "+" on positive numbers makes up/down obvious at a glance.
            sign = "+" if going_up else ""

            # The little price chart for this stock (may be "" if no data came back).
            chart = sparkline_svg(row["prices"], going_up)

            # One card for this stock: symbol, its chart, then the price and change.
            # data-symbol lets the browser find this row to replace it with a live one.
            pieces.append('<div class="stock" data-symbol="' + html.escape(symbol, quote=True) + '">')
            pieces.append('<div class="stock-sym">' + html.escape(row.get("name", symbol)) + '</div>')
            pieces.append(chart)
            pieces.append('<div class="stock-nums">')
            pieces.append('<div class="stock-price">' + format_price(symbol, price) + '</div>')
            pieces.append('<div class="stock-change" style="color:' + colour + '">'
                          + sign + "{:,.2f}".format(change) + ' (' + sign + str(percent) + '%)</div>')
            pieces.append('</div>')
            pieces.append('</div>')

        pieces.append('</div>')
        return "\n".join(pieces)

    except Exception:
        # Fail soft: one broken panel must not blank the rest of the page.
        return "<h2>Stocks</h2><p>Stock prices are unavailable right now.</p>"
