import yt_dlp
from pathlib import Path

class Plugin:
  def __init__(self, config: Path):
    pass

  def fetch_metadata(self, track: str):
    ydl_opts = {
        "quiet": True,
        "no_warnings": True,
        "extract_flat": False,
    }

    search_query = f"scsearch1:{track}"

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
      try:
        info = ydl.extract_info(search_query, download=False)

        if "entries" in info and info["entries"]:
          track_data = info["entries"][0]
        else:
          return None

        metadata = {
            "track_name": track_data.get("title"),
            "artist_name": track_data.get("uploader")
            or track_data.get("channel"),
            "duration_s": track_data.get("duration"),
            "duration_ms": track_data.get("duration") * 1000
            if track_data.get("duration")
            else None,
            "webpage_url": track_data.get("webpage_url"),
            "thumbnail": track_data.get("thumbnail"),
            "play_count": track_data.get("view_count"),
            "id": track_data.get("id"),
        }

        return metadata

      except Exception as e:
        print(f"Error fetching SoundCloud metadata: {e}")
        return None