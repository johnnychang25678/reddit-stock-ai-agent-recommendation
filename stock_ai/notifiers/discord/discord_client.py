
import httpx

class DiscordClient:
    def __init__(self, webhook_url: str):
        self.webhook_url = webhook_url

    def send_message(self, message: str):
        try:
            res = httpx.post(self.webhook_url, json={"content": message})
            res.raise_for_status()
            try:
                return res.json()  # may raise ValueError if 204 No Content
            except ValueError:
                return None
        except httpx.HTTPStatusError as e:
            print("Discord API error:", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            print("Request failed:", e)
            raise
    
    def send_embed(self, embed: dict):
        """Example embed:
        {
            "title": "Embed Title",
            "description": "Embed Description",
            "color": 0x00ff00,
            "fields": [
                {"name": "Field 1", "value": "Value 1", "inline": True},
                {"name": "Field 2", "value": "Value 2", "inline": True}
            ]
        }
        """
        try:
            res = httpx.post(self.webhook_url, json={"embeds": [embed]})
            res.raise_for_status()
            try:
                return res.json()  # may raise ValueError if 204 No Content
            except ValueError:
                return None
        except httpx.HTTPStatusError as e:
            print("Discord API error:", e.response.status_code, e.response.text)
            raise
        except httpx.RequestError as e:
            print("Request failed:", e)
            raise
