import requests
import sys

# Each entry is (display_name, url).
# The original file had a syntax error here — a string literal fragment
# "iptv-org" was stuck inside the first URL string without a comma.
# Splitting into two clean entries instead.
SOURCES = [
    ("iptv-org/index",  "https://iptv-org.github.io/iptv/index.m3u"),
    ("iptv-org/all",    "https://raw.githubusercontent.com/iptv-org/iptv/master/playlists/all.m3u"),
    ("Free-TV/IPTV",    "https://raw.githubusercontent.com/Free-TV/IPTV/master/m3u/clean.m3u"),
    ("iptv-org/index",  "https://iptv-org.github.io/iptv/index.m3u"),
    ("iptv-org/all",    "https://raw.githubusercontent.com/iptv-org/iptv/master/playlists/all.m3u"),
    ("Free-TV/IPTV",    "https://raw.githubusercontent.com/Free-TV/IPTV/master/m3u/clean.m3u"),
]
    ("iptv-org/index",  "https://iptv-org.github.io/iptv/index.m3u"),
    ("iptv-org/all",    "https://raw.githubusercontent.com/iptv-org/iptv/master/playlists/all.m3u"),
    ("Free-TV/IPTV",    "https://raw.githubusercontent.com/Free-TV/IPTV/master/m3u/clean.m3u"),
]

def fetch_playlist(url: str) -> str:
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def merge_playlists(sources: list) -> str:
    merged = ["#EXTM3U"]
    seen_urls: set = set()

    for name, url in sources:
        try:
            data = fetch_playlist(url)
            lines = data.split("\n")
            for i, line in enumerate(lines):
                if line.startswith("#EXTINF"):
                    stream_url = lines[i + 1].strip() if i + 1 < len(lines) else ""
                    if stream_url and stream_url not in seen_urls:
                        merged.append(line)
                        merged.append(stream_url)
                        seen_urls.add(stream_url)
        except Exception as e:
            # Print but don't abort — partial results are better than nothing.
            print(f"WARNING: Failed to fetch {name}: {e}", file=sys.stderr)

    return "\n".join(merged)

def main():
    playlist = merge_playlists(SOURCES)
    channel_count = playlist.count("#EXTINF")

    # Refuse to write an empty playlist — this would overwrite a good one with garbage.
    if channel_count == 0:
        print("ERROR: All sources failed. Aborting write to preserve existing playlist.",
              file=sys.stderr)
        sys.exit(1)

    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)

    print(f"Playlist updated with {channel_count} channels.")

if __name__ == "__main__":
    main()
