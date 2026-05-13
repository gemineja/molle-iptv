import requests

SOURCES = [
    # Add more legal sources as needed
    ("iptv-org", "https://raw.githubusercontent.com/iptv-org/iptv/master/playlists/all.m3u") ,
    ("Free-TV/IPTV", "https://raw.githubusercontent.com/Free-TV/IPTV/master/m3u/clean.m3u")
]

def fetch_playlist(url):
    resp = requests.get(url, timeout=20)
    resp.raise_for_status()
    return resp.text

def merge_playlists(sources):
    merged = ['#EXTM3U']
    seen_urls = set()
    for name, url in sources:
        try:
            data = fetch_playlist(url)
            lines = data.split('\n')
            for i, line in enumerate(lines):
                if line.startswith('#EXTINF'):
                    stream_url = lines[i + 1].strip() if i + 1 < len(lines) else ''
                    if stream_url and stream_url not in seen_urls:
                        merged.append(lines[i])
                        merged.append(stream_url)
                        seen_urls.add(stream_url)
        except Exception as e:
            print(f'Failed to fetch {name}: {e}')
    return '\n'.join(merged)

def main():
    playlist = merge_playlists(SOURCES)
    with open('playlist.m3u8', 'w', encoding='utf-8') as f:
        f.write(playlist)
    print(f'Playlist updated with {len(playlist.split("#EXTINF"))-1} channels.')

if __name__ == "__main__":
    main()
