import requests
import sys

SOURCES = [
    ("iptv-org/index", "https://iptv-org.github.io/iptv/index.m3u"),
    ("Free-TV/IPTV", "https://raw.githubusercontent.com/Free-TV/IPTV/master/playlist.m3u8"),
]

# iptv-org's own channel/feed metadata API — used only to look up each
# channel's spoken language (independent of which country's feed carries
# it), so the player can offer a "show me everything in language X"
# filter regardless of source country.
FEEDS_URL = "https://iptv-org.github.io/api/feeds.json"
LANGUAGES_URL = "https://iptv-org.github.io/api/languages.json"


def fetch_playlist(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text


def fetch_json(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.json()


def build_language_map():
    """tvg-id (e.g. "DR1.dk@SD") -> human-readable language name (e.g. "Danish")."""
    try:
        feeds = fetch_json(FEEDS_URL)
        lang_names = {l["code"]: l["name"] for l in fetch_json(LANGUAGES_URL)}
    except Exception as e:
        print(f"WARNING: Failed to fetch language metadata: {e}", file=sys.stderr)
        return {}

    lang_map = {}
    for feed in feeds:
        codes = feed.get("languages") or []
        if not codes:
            continue
        tvg_id = f"{feed['channel']}@{feed['id']}"
        lang_map[tvg_id] = lang_names.get(codes[0], codes[0])
    return lang_map


def merge_playlists(sources, lang_map):
    merged = ["#EXTM3U"]
    seen_urls = set()
    for name, url in sources:
        try:
            data = fetch_playlist(url)
            lines = data.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("#EXTINF"):
                    stream_url = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    if stream_url and stream_url not in seen_urls:
                        tvg_id_match = line.find('tvg-id="')
                        if tvg_id_match != -1:
                            tvg_id = line[tvg_id_match + 8:line.find('"', tvg_id_match + 8)]
                            language = lang_map.get(tvg_id)
                            if language:
                                line = line.replace(
                                    'tvg-id="', f'tvg-language="{language}" tvg-id="', 1
                                )
                        merged.append(line)
                        merged.append(stream_url)
                        seen_urls.add(stream_url)
        except Exception as e:
            print(f"WARNING: Failed to fetch {name}: {e}", file=sys.stderr)
    return "\n".join(merged)


def main():
    lang_map = build_language_map()
    playlist = merge_playlists(SOURCES, lang_map)
    channel_count = playlist.count("#EXTINF")
    if channel_count == 0:
        print("ERROR: All sources failed.", file=sys.stderr)
        sys.exit(1)
    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)
    print(f"Playlist updated with {channel_count} channels.")


if __name__ == "__main__":
    main()
