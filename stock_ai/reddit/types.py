from datetime import datetime
from dataclasses import dataclass

@dataclass
class RedditPost:
    title: str
    selftext: str
    score: int
    comments: int
    upvote_ratio: float
    created: datetime
    url: str

