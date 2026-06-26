# Molle IPTV

A fully automated, self-updating legal IPTV web player. This project fetches and merges free, legal IPTV playlists (like iptv-org/iptv and Free-TV/IPTV) and presents them in a web player with channel navigation—ready for deployment on your own domain!

## Features
- Automated channel updates: runs every 12 hours via GitHub Actions
- Playlist merging from major public IPTV sources
- Simple and clean web player—all in your browser!
- Direct playback of live channels (no local server needed)
- Easily customizable

## How it works
- The Python script in `scripts/update_playlist.py` fetches/merges m3u8 sources.
- The GitHub Actions workflow updates `playlist.m3u8` and commits if changed.
- Your `index.html` loads this playlist from GitHub and lets users select and watch channels instantly.

## Usage
1. **Deploy:** Copy `index.html` to your own web hosting.
2. **Update:** Channels are refreshed automatically.  
3. **Watch:** Open your site and enjoy up-to-date, legal IPTV channels.

## Customizing Channels
- Edit `scripts/update_playlist.py` and add any extra (legal!) m3u8 sources.
- The playlist is re-generated every 12 hours.

## Legal Notice
- This project merges public domain streams. Only use and distribute legal and freely available channels. You are responsible for complying with your local laws.

## License
Apache License 2.0