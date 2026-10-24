from pathlib import Path
import json, yt_dlp

class Plugin():
    def __init__(self, config: Path):
        current_dir = Path(__file__).parent
        p = Path(config)

        config_file = p.parent.parent.parent.parent / p.name

        with open(config_file, "r") as f:
            config_data = json.load(f)
    def download(self, artist, track):
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': 'songs_cache/%(title)s.%(ext)s',
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
                }],
        }

        query = f"ytsearch1:{artist} - {track}"

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([query])