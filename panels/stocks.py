# panels/stocks.py
# The Stocks panel: for each ticker, show the latest price, today's change (green/red),
# and a small inline-SVG sparkline of the day's prices. Fetches THROUGH the shared cache
# so repeated runs don't re-hit Yahoo. Moved out of main.py during the panels/ split;
# the logic is unchanged.

# "yfinance" fetches stock prices from Yahoo Finance. No API key or account needed.
import yfinance as yf
# Shared bits: the tickers from config.json, and the cache helpers.
from panels.common import TICKERS, get_cached, cached_time_label

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
    for symbol in TICKERS:
        ticker = yf.Ticker(symbol)
        info = ticker.fast_info
        results.append({
            "symbol": symbol,
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
        stocks = get_cached("stocks", fetch_stocks_data, 900)

        pieces = []
        pieces.append("<h2>Stocks</h2>")
        # Honest "as of" time = when the cached data was actually fetched (the cache
        # file's age), not now. Stocks don't refresh from the browser button (that
        # only re-fetches weather); a run re-fetches them once the cache passes 15 min.
        pieces.append('<p class="updated">As of ' + cached_time_label("stocks")
                      + ' · re-fetched every ~15 min</p>')
        # The list scrolls inside itself if there are lots of tickers, so the widget
        # stays a fixed compact height (see the CSS for .stocks-list).
        pieces.append('<div class="stocks-list">')

        # Each entry in "stocks" is one ticker's saved numbers (from fetch_stocks_data).
        for row in stocks:
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
            pieces.append('<div class="stock">')
            pieces.append('<div class="stock-sym">' + symbol + '</div>')
            pieces.append(chart)
            pieces.append('<div class="stock-nums">')
            pieces.append('<div class="stock-price">$' + str(round(price, 2)) + '</div>')
            pieces.append('<div class="stock-change" style="color:' + colour + '">'
                          + sign + str(change) + ' (' + sign + str(percent) + '%)</div>')
            pieces.append('</div>')
            pieces.append('</div>')

        pieces.append('</div>')
        return "\n".join(pieces)

    except Exception:
        # Fail soft: one broken panel must not blank the rest of the page.
        return "<h2>Stocks</h2><p>Stock prices are unavailable right now.</p>"
