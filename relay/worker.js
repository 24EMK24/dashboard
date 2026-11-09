// relay/worker.js — the dashboard's relay, run on Cloudflare (added 2026-11-09).
//
// WHY THIS EXISTS: the dashboard page would like to fetch YouTube videos, news headlines
// and stock prices itself, every time it is opened, instead of waiting for a GitHub
// rebuild. But YouTube, Google News and Yahoo do not send the
// "Access-Control-Allow-Origin" header, so a browser is not ALLOWED to read them from
// another site. This tiny program sits in between: the page asks the relay, the relay
// asks the real site, and hands the answer back WITH that permission header added.
//
// It also gets us off GitHub's shared machines, which YouTube and Google throttle in the
// evenings (measured: the build's fetch step took 5 s in the morning and ~4 min at night).
//
// HOW TO USE IT — exactly one of these per request:
//   ?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx   a YouTube channel's RSS feed (XML)
//   ?news=Seattle Seahawks                  Google News search results (RSS XML)
//   ?news=                                  Google News top stories (RSS XML)
//   ?stock=^GSPC&range=1d                   Yahoo's price chart for one symbol (JSON);
//                                           range is "1d" (every 15 min) or "5d" (daily)
//
// DEPLOYING: this file is pasted into the Cloudflare dashboard (Workers -> yt-relay ->
// Edit code -> Deploy). It is kept in the repo so the code that runs there is not a
// mystery. Editing it HERE changes nothing until it is pasted there again.
//
// Nothing secret lives in here — no key, no token. The relay only ever reads public
// pages, and only the three kinds above, so someone else using its address can't do harm.

// The header that gives every website permission to read our answers. "*" means "anyone",
// which is fine because every answer is public information.
const CORS_HEADERS = { "Access-Control-Allow-Origin": "*" };

// The same short User-Agent the Python panels use. (Never a long "Chrome/…" one — some
// sites refuse requests that claim to be Chrome without sending everything Chrome sends.)
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)";

// How long (in seconds) an answer may be reused before asking again: 10 minutes for
// videos and news, 2 minutes for stock prices (which move faster). The phone's browser
// obeys this too, so reopening the page within that time does not even reach the relay.
const FEED_MAX_AGE_SECONDS = 600;
const STOCK_MAX_AGE_SECONDS = 120;

// What each kind of request is allowed to look like. Anything else is refused, so the
// relay can only ever be used to fetch these three things.
// A YouTube channel id is always "UC" followed by 22 letters, digits, "_" or "-".
const CHANNEL_ID_PATTERN = /^UC[A-Za-z0-9_-]{22}$/;
// A stock symbol: letters, digits and a few marks, e.g. "AAPL", "^GSPC", "BRK-B".
const STOCK_PATTERN = /^\^?[A-Za-z0-9.=-]{1,12}$/;
// A news search is plain text; we only cap its length.
const NEWS_MAX_LENGTH = 200;

// A small helper: a plain-text reply with the permission header, for error messages.
function textReply(message, status) {
  return new Response(message, { status: status, headers: CORS_HEADERS });
}

// Fetch one address and pass the answer back with the permission header attached.
// Shared by all three kinds of request, so they behave identically.
async function relay(targetUrl, contentType, maxAgeSeconds) {
  let reply;
  try {
    // The "cf" part asks Cloudflare to keep a copy and reuse it for a while, so many page
    // loads cost the real site only one request. (If Cloudflare declines to keep it,
    // everything still works — just with more asking.)
    reply = await fetch(targetUrl, {
      headers: { "User-Agent": USER_AGENT },
      cf: { cacheTtl: maxAgeSeconds, cacheEverything: true },
    });
  } catch (error) {
    // The site could not be reached at all (502 = "the thing behind me failed").
    return textReply("Could not reach the site: " + error, 502);
  }

  // The site answered, but with an error (throttled, or the thing is gone). Pass the
  // status along in words so the page — and anyone debugging — can see what happened.
  if (!reply.ok) {
    return textReply("The site answered " + reply.status, 502);
  }

  // Success: hand back the text with the permission header attached.
  const body = await reply.text();
  return new Response(body, {
    status: 200,
    headers: {
      ...CORS_HEADERS,
      "Content-Type": contentType,
      "Cache-Control": "public, max-age=" + maxAgeSeconds,
    },
  });
}

export default {
  // Cloudflare calls this once for every request that reaches the relay.
  async fetch(request) {
    // Read the "?…" part of the address the page asked for.
    const params = new URL(request.url).searchParams;

    // 1. A YouTube channel's feed.
    if (params.has("channel_id")) {
      const channelId = params.get("channel_id");
      if (!CHANNEL_ID_PATTERN.test(channelId)) {
        return textReply("Expected ?channel_id=UC… (a YouTube channel id)", 400);
      }
      return relay("https://www.youtube.com/feeds/videos.xml?channel_id=" + channelId,
                   "text/xml; charset=UTF-8", FEED_MAX_AGE_SECONDS);
    }

    // 2. Google News. An empty search means the general top-stories feed — the same rule
    // panels/news.py follows. hl/gl/ceid ask Google for US English results.
    if (params.has("news")) {
      const query = params.get("news").trim();
      if (query.length > NEWS_MAX_LENGTH) {
        return textReply("News search too long", 400);
      }
      const tail = "hl=en-US&gl=US&ceid=US:en";
      const address = query === ""
        ? "https://news.google.com/rss?" + tail
        : "https://news.google.com/rss/search?q=" + encodeURIComponent(query) + "&" + tail;
      return relay(address, "text/xml; charset=UTF-8", FEED_MAX_AGE_SECONDS);
    }

    // 3. A stock or index's price chart from Yahoo. "1d" = today, a reading every 15
    // minutes; "5d" = the last few days, one reading a day (used when today has nothing,
    // e.g. at the weekend). Same two choices panels/stocks.py makes.
    if (params.has("stock")) {
      const symbol = params.get("stock");
      if (!STOCK_PATTERN.test(symbol)) {
        return textReply("Expected ?stock=SYMBOL", 400);
      }
      const range = params.get("range") === "5d" ? "5d" : "1d";
      const interval = range === "5d" ? "1d" : "15m";
      return relay("https://query1.finance.yahoo.com/v8/finance/chart/"
                   + encodeURIComponent(symbol) + "?range=" + range + "&interval=" + interval,
                   "application/json; charset=UTF-8", STOCK_MAX_AGE_SECONDS);
    }

    // None of the three: say what is expected (400 = "bad request").
    return textReply("Expected ?channel_id=…, ?news=… or ?stock=…", 400);
  },
};
