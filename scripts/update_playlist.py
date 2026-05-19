import requests
import sys

SOURCES = [
    ("iptv-org/index", "https://iptv-org.github.io/iptv/index.m3u"),
    ("iptv-org/all", "https://raw.githubusercontent.com/iptv-org/iptv/master/playlists/all.m3u"),
    ("Free-TV/IPTV", "https://raw.githubusercontent.com/Free-TV/IPTV/master/m3u/clean.m3u"),
]

def fetch_playlist(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def merge_playlists(sources):
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
                        merged.append(line)
                        merged.append(stream_url)
                        seen_urls.add(stream_url)
        except Exception as e:
            print(f"WARNING: Failed to fetch {name}: {e}", file=sys.stderr)
    return "\n".join(merged)

def main():
    playlist = merge_playlists(SOURCES)
    channel_count = playlist.count("#EXTINF")
    if channel_count == 0:
        print("ERROR: All sources failed.", file=sys.stderr)
        sys.exit(1)
    with open("playlist.m3u8", "w", encoding="utf-8") as f:
        f.write(playlist)
    print(f"Playlist updated with {channel_count} channels.")

if __name__ == "__main__":
    main()