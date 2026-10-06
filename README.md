# molle-iptv

A self-updating playlist of free, public TV channels — and, more to the point,
a workflow that throws away the ones that don't work.

Anyone can merge a few public m3u files. The problem is that roughly half the
streams in them can't play in a web browser at all, so a visitor clicks a
channel and gets nothing, with no explanation. This repo exists to fix that
part. Every 12 hours a GitHub Action merges the sources, fills in the missing
metadata, tests every stream, and publishes only the ones that answered.

Used live at [molle.me/tv.html](https://molle.me/tv.html) — the page itself is
[`site/tv.html`](site/tv.html) in this repo.

## The two playlists

| File | Channels | For |
|---|---|---|
| `playlist.m3u8` | verified | **Web pages.** Every channel was reachable over https with open CORS at build time. This is the one to embed. |
| `playlist-all.m3u8` | everything | **VLC, Kodi, TiviMate.** Native players don't care about https or CORS, so they can play a great deal more. |

Both are deduplicated and carry `group-title`, `tvg-country`, `tvg-region` and
`tvg-language` on every entry.

## Use it on your own site

```html
<script src="https://cdn.jsdelivr.net/npm/hls.js@1.7.3/dist/hls.min.js"></script>
<video id="tv" controls playsinline></video>
<script>
  const PLAYLIST =
    'https://raw.githubusercontent.com/gemineja/molle-iptv/main/playlist.m3u8';

  fetch(PLAYLIST).then(r => r.text()).then(text => {
    const lines = text.split('\n');
    const channels = [];
    for (let i = 0; i < lines.length; i++) {
      if (!lines[i].startsWith('#EXTINF')) continue;
      const name = lines[i].split(',').pop().trim();
      const url  = (lines[i + 1] || '').trim();
      const attr = k => (lines[i].match(new RegExp(k + '="([^"]*)"')) || [])[1] || '';
      if (url.startsWith('http')) {
        channels.push({ name, url, country: attr('tvg-country'),
                        region: attr('tvg-region'), group: attr('group-title') });
      }
    }
    // channels[] is now ready to filter by region, country or group
    play(channels[0].url);
  });

  function play(url) {
    const video = document.getElementById('tv');
    if (Hls.isSupported()) {
      const hls = new Hls();
      hls.loadSource(url);
      hls.attachMedia(video);
      hls.on(Hls.Events.MANIFEST_PARSED, () => video.play().catch(() => {}));
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = url;                       // Safari plays HLS natively
    }
  }
</script>
```

Point a region dropdown at `tvg-region` (five continents), a country dropdown
at `tvg-country`, and a genre dropdown at `group-title` (ten categories). That
is the whole navigation — no other setup, no server, no API key.

## Why a channel gets dropped

`is_browser_playable()` in `scripts/update_playlist.py` is the whole policy,
and each rule is a real failure that used to reach visitors:

1. **Not https.** An `http://` stream is blocked as mixed content on any https
   page. Nothing in the page can override this — it is enforced by the browser
   itself. Retrying those over https recovers about 5%, so it isn't worth it.
   They stay in `playlist-all.m3u8`, where VLC plays them happily.
2. **CORS that doesn't allow you.** hls.js fetches over XHR, so a stream needs
   `Access-Control-Allow-Origin`. `*` works for everyone, and so does a server
   that echoes back whichever origin asked. One pinned to somebody else's
   origin — Pluto returns `http://pluto.tv` — is useless to every embedder.
3. **`http://` inside the manifest.** A playlist can answer `200` over https
   and still point every variant at `http://`. The failure then lands one hop
   later, where it looks like nothing happened at all.

Adult channels (`is_nsfw` in iptv-org's data) are excluded.

**Geo-restricted channels are kept, not dropped.** The build runs on a GitHub
runner in the United States; your visitors are somewhere else. A stream that
answers `401`, `403` or `451` is not dead — it simply won't serve *that
machine*. DR1 and DR2 refuse the runner and answer `200` in Copenhagen, and
an earlier version of this check deleted them for it. Those channels stay in
the list carrying `tvg-geo="restricted"`, so a player can tell the visitor a
channel may need to be watched from its home country instead of pretending it
doesn't exist.

**A channel that worked last time gets a second chance.** Free streams are
slow as often as they are dead, and an 8-second timeout used to drop about a
hundred working channels every build and add them back the next — some 900
channels blinked in and out over a dozen builds. Now a channel that was in the
last `playlist.m3u8` and fails *softly* (a timeout, a dropped connection, a
429 or 5xx) is asked once more with a longer timeout before it is removed.
Hard failures — 404, wrong CORS, `http://` — are not retried.

**A bad build never replaces a good one.** If fewer than 60% of last time's
channels pass, the runner's network is the likelier culprit than the
internet, so the old playlist stays and the run fails loudly. Run the
workflow by hand with `min_kept` set to `0` if the drop is real.

## Getting more channels

The honest state of things: iptv-org is the large open-source catalogue, and
most other aggregators either mirror it, are EPG-only, or redistribute paid
services — which this project won't do.

So the way the list grows is people adding sources. If you know a public,
legal one, add it to `SOURCES` at the top of `scripts/update_playlist.py`:

```python
SOURCES = [
    ("iptv-org/index", "https://iptv-org.github.io/iptv/index.m3u"),
    ("Free-TV/IPTV", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
    ("your source", "https://example.com/playlist.m3u"),
]
```

Nothing else needs changing. Duplicates are removed by URL and again by
channel name, and anything broken is filtered out by validation — so a source
that turns out to be mostly dead costs the list nothing. Open a pull request.

## Running it yourself

```bash
pip install -r requirements.txt
python scripts/update_playlist.py
```

| Variable | Default | |
|---|---|---|
| `VALIDATE` | `1` | `0` skips validation — much faster when you only want to see the merge |
| `VALIDATE_WORKERS` | `64` | parallel requests |
| `VALIDATE_TIMEOUT` | `8` | seconds per stream |
| `VALIDATE_RETRY_TIMEOUT` | `15` | seconds for the second look at a published channel that failed softly |
| `VALIDATE_LIMIT` | `0` | cap the number checked, for quick local runs |
| `MIN_KEPT` | `0.6` | refuse to publish below this share of the last playlist; `0` turns it off |

A full validated build takes a few minutes — it opens one request per stream.
Each run on GitHub writes a summary (playable, geo-restricted, dropped,
rescued, new and gone since last time) to the run page.

The parsing and validation rules have offline tests, which the workflow runs
before every build:

```bash
python -m unittest discover -s tests
```

## The workflow

`.github/workflows/refresh.yml` runs at 00:23 and 12:23 UTC — off the hour,
because jobs scheduled for :00 queue behind everyone else's — and again
whenever the script, the tests or the workflow change on `main`. Only one
build runs at a time, so two can never race each other to push. Dependabot
keeps the actions and `requests` current.

## Legal

This merges playlists of streams that broadcasters publish freely and
publicly. It hosts no video and circumvents nothing. Check what applies where
you are before redistributing, and don't add sources for paid services.

## License

Apache 2.0
