import os
import yt_dlp
from pathlib import Path

class Plugin:

  def __init__(self, config: Path):
    self.download_dir = "songs_cache"

  def download(self, artist: str, track: str):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": os.path.join(self.download_dir, "%(title)s.%(ext)s"),
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            }
        ],
        "quiet": True,
        "no_warnings": True,
    }

    search_query = f"scsearch1:{artist} - {track}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      try:
        info = ydI_info = ydl.extract_info(search_query, download=True)

        if "entries" in info and info["entries"]:
          track_data = info["entries"][0]
        else:
          track_data = info

        filename = ydl.prepare_filename(track_data)
        base, _ = os.path.splitext(filename)
        final_filepath = base + ".mp3"

        return {
            "status": "success",
            "track_name": track_data.get("title"),
            "artist_name": track_data.get("uploader"),
            "file_path": final_filepath,
        }

      except Exception as e:
        print(f"Error downloading track: {e}")
        return None