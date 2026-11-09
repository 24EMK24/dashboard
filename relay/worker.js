// relay/worker.js — the YouTube relay, run on Cloudflare (added 2026-11-09).
//
// WHY THIS EXISTS: the dashboard page would like to ask YouTube for new videos itself,
// every time it is opened, instead of waiting for a GitHub rebuild. But YouTube's feed
// does not send the "Access-Control-Allow-Origin" header, so a browser is not ALLOWED to
// read it from another site. This tiny program sits in between: the page asks the relay,
// the relay asks YouTube, and hands the answer back WITH that permission header added.
//
// It also gets us off GitHub's shared machines, which YouTube throttles in the evenings
// (measured: the build's fetch step took 5 s in the morning and ~4 minutes at night).
//
// HOW TO USE IT:   https://<your-relay>.workers.dev/?channel_id=UCxxxxxxxxxxxxxxxxxxxxxx
// It answers with the channel's RSS feed (the same XML the Python build reads).
//
// DEPLOYING: this file is pasted into the Cloudflare dashboard (Workers -> the relay ->
// Edit code -> Deploy). It is kept in the repo so the code that runs there is not a
// mystery. Editing it HERE changes nothing until it is pasted there again.
//
// Nothing secret lives in here — no key, no token. The relay only ever reads public
// YouTube feeds, so someone else using its address can't do any harm.

// The header that gives every website permission to read our answers. "*" means "anyone",
// which is fine because the answer is a public YouTube feed.
const CORS_HEADERS = { "Access-Control-Allow-Origin": "*" };

// The same short User-Agent the Python panels use. (Never a long "Chrome/…" one — some
// sites refuse requests that claim to be Chrome without sending everything Chrome sends.)
const USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)";

// How long (in seconds) an answer may be reused before asking YouTube again: 10 minutes.
// The phone's browser obeys this too, so reopening the page within 10 minutes does not
// even reach the relay.
const MAX_AGE_SECONDS = 600;

// A YouTube channel id is always "UC" followed by 22 letters, digits, "_" or "-".
// Anything else is refused, so the relay can only ever be used to fetch YouTube feeds.
const CHANNEL_ID_PATTERN = /^UC[A-Za-z0-9_-]{22}$/;

// A small helper: a plain-text reply with the permission header, for error messages.
function textReply(message, status) {
  return new Response(message, { status: status, headers: CORS_HEADERS });
}

export default {
  // Cloudflare calls this once for every request that reaches the relay.
  async fetch(request) {
    // Read "?channel_id=…" out of the address the page asked for.
    const address = new URL(request.url);
    const channelId = address.searchParams.get("channel_id") || "";

    // Refuse anything that isn't a real-looking channel id (400 = "bad request").
    if (!CHANNEL_ID_PATTERN.test(channelId)) {
      return textReply("Expected ?channel_id=UC… (a YouTube channel id)", 400);
    }

    // Ask YouTube for that channel's feed. The "cf" part asks Cloudflare to keep a copy
    // for 10 minutes and reuse it, so many page loads cost YouTube only one request.
    // (If Cloudflare declines to keep it, everything still works — just with more asking.)
    let reply;
    try {
      reply = await fetch(
        "https://www.youtube.com/feeds/videos.xml?channel_id=" + channelId,
        {
          headers: { "User-Agent": USER_AGENT },
          cf: { cacheTtl: MAX_AGE_SECONDS, cacheEverything: true },
        }
      );
    } catch (error) {
      // YouTube could not be reached at all (502 = "the thing behind me failed").
      return textReply("Could not reach YouTube: " + error, 502);
    }

    // YouTube answered, but with an error (throttled, or the channel is gone). Pass the
    // status along in words so the page — and anyone debugging — can see what happened.
    if (!reply.ok) {
      return textReply("YouTube answered " + reply.status, 502);
    }

    // Success: hand back the feed's text with the permission header attached.
    const feedText = await reply.text();
    return new Response(feedText, {
      status: 200,
      headers: {
        ...CORS_HEADERS,
        "Content-Type": "text/xml; charset=UTF-8",
        "Cache-Control": "public, max-age=" + MAX_AGE_SECONDS,
      },
    });
  },
};
