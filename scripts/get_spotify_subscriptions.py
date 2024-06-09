import base64
import json
import requests

CLIENT_ID = ""
CLIENT_SECRET = ""
SHOW_ID = "04KgPyGwvYx0IfYoqauNxs"


# Get token
credentials = f"{CLIENT_ID}:{CLIENT_SECRET}"
base64_credentials = base64.b64encode(credentials.encode()).decode()
print(base64_credentials)
headers = {
    "Authorization": f"Basic {base64_credentials}",
}
body = {
    "grant_type": "client_credentials",
}
auth_response = requests.post(
    "https://accounts.spotify.com/api/token",
    headers=headers,
    data=body,
)
print(auth_response.json())
if auth_response.status_code != 200:
    raise Exception("Failed to authenticate with Spotify API")

bearer_token = auth_response.json()["access_token"]
print(bearer_token)

# Get show info
headers = {
    "Authorization": f"Bearer {bearer_token}",
}
spotify_shows = requests.get(
    f"https://api.spotify.com/v1/shows/{SHOW_ID}",
    headers=headers,
)

if spotify_shows.status_code != 200:
    raise Exception("Failed to fetch Spotify show")

show_data = spotify_shows.json()
print(json.dumps(show_data, indent=2))
