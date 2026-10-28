import lyricsgenius
from pathlib import Path

class Plugin:

  def __init__(self, config: Path):
    self.genius = lyricsgenius.Genius()

    self.genius.verbose = False
    self.genius.remove_section_headers = (
        False
    )
    self.genius.skip_non_songs = True

  def get_lyrics(self, artist: str, track: str):
    try:
      song = self.genius.search_song(track, artist)

      if not song:
        return None

      metadata = {
          "track_name": song.title,
          "artist_name": song.artist,
          "lyrics": song.lyrics,
          "genius_url": song.url,
          "album_art": song.art_image_url,
      }

      return metadata

    except Exception as e:
      print(f"Error fetching lyrics: {e}")
      return None