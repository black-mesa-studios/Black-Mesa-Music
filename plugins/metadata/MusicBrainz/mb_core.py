import json
from pathlib import Path
import requests

class Plugin:
    BASE_URL = "https://musicbrainz.org/ws/2/"

    def __init__(self, config: Path):
        p = Path(config)

        config_file = p.parent.parent.parent.parent / "config.json"

        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config_data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            config_data = {}

        extra_data = config_data.get('extra_data', {})
        email = extra_data.get("music_brainz_email", "default@example.com")
        
        self.headers = {
            'User-Agent': f'MusicApp/1.0 ({email})'
        }

    def fetch_metadata(self, title: str):
        query = f'recording:"{title}"'
        url = f"{self.BASE_URL}recording/"
        params = {
            'query': query,
            'fmt': 'json'
        }
        
        response = requests.get(url, headers=self.headers, params=params)
        response.raise_for_status()
        
        return response.json()