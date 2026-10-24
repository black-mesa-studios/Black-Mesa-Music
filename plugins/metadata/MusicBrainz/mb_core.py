import json
from pathlib import Path
import requests

class Plugin:
    BASE_URL = "https://musicbrainz.org/ws/2/"

    def __init__(self, config: Path):
        current_dir = Path(__file__).parent
        
        p = Path(config)

        config_file = p.parent.parent.parent.parent / p.name

        with open(config_file, "r") as f:
            config_data = json.load(f)
            
        email = config_data['extra_data'].get("music_brainz_email", "default@example.com")
        self.headers = {
            'User-Agent': f'MusicApp/1.0 ({email})'
        }

    def search(self, artist: str, title: str):
        query = f'recording:"{title}" AND artist:"{artist}"'
        url = f"{self.BASE_URL}recording"
        params = {
            'query': query,
            'fmt': 'json'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()