from functools import lru_cache
from openai import OpenAI
import os
from stock_ai.reddit.reddit_scraper import RedditScraper


@lru_cache(maxsize=1)
def get_openai_client() -> OpenAI:
    api_key = os.getenv("OPENAI_API_KEY")
    return OpenAI(api_key=api_key)


@lru_cache(maxsize=1)
def get_reddit_scraper() -> RedditScraper:
    return RedditScraper(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT"),
    )