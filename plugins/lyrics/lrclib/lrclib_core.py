from pathlib import Path
import json, requests, re

class Plugin():
    def __init__(self, config: Path):
        current_dir = Path(__file__).parent

        p = Path(config)

        config_file = p.parent.parent.parent.parent / p.name
        with open(config_file, "r") as f:
            self.config_data = json.load(f)
    def _parse_lrc(self, lrc_text):
        if not lrc_text:
            return {}
        
        lyrics_dict = {}
        pattern = re.compile(r'\[(\d{2}):(\d{2})[.,](\d{2,3})\](.*)')
        
        for line in lrc_text.splitlines():
            match = pattern.match(line.strip())
            if match:
                minutes = int(match.group(1))
                seconds = int(match.group(2))
                fraction = float(f"0.{match.group(3)}")
                
                total_seconds = round(minutes * 60 + seconds + fraction, 2)
                
                text = match.group(4).strip()
                lyrics_dict[total_seconds] = text
                
        return lyrics_dict

    def get_lyrics(self, track_name, artist_name):
        url = "https://lrclib.net/api/search"
        email = self.config_data['extra_data'].get("music_brainz_email", "default@example.com")
        params = {
            'track_name': track_name,
            'artist_name': artist_name
        }
    
        headers = {
            'User-Agent': f'MyPythonScript/1.0 ({email})'
        }
    
        response = requests.get(url, params=params, headers=headers)
    
        if response.status_code == 200:
            results = response.json()
            if results:
                best_match = results[0]
            
                synced_lyrics_raw = best_match.get('syncedLyrics')
                parsed_synced_lyrics = self._parse_lrc(synced_lyrics_raw)
                plain_lyrics = best_match.get('plainLyrics')
            
                return {
                    "track": best_match.get("trackName"),
                    "artist": best_match.get("artistName"),
                    "synced": parsed_synced_lyrics,
                    "plain": plain_lyrics
                }
            else:
                print("No lyrics found for this track.")
        else:
            print(f"Error: {response.status_code}\n{response.text}")
        
        return None