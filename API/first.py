import base64
import requests
from conf import USERNAME, API_KEY, BASE_URL

def build_auth_header():
    raw = f"{USERNAME.strip()}:{API_KEY.strip()}"
    token = base64.b64encode(raw.encode()).decode()
    return {"Authorization": f"Basic {token}"}

def get_current_season():
    r = requests.get(BASE_URL, headers=build_auth_header(), timeout=10)
    r.raise_for_status()
    return r.json()["currentSeason"]