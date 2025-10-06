from datetime import datetime
from dataclasses import dataclass

import stock_ai.db.models.reddit_post
import stock_ai.db.models.reddit_filterd_post


@dataclass
class RedditPost:
    reddit_id: str
    flair: str
    title: str
    selftext: str
    score: int
    num_comments: int
    upvote_ratio: float
    created: datetime
    url: str

    @classmethod
    def from_orm(cls, orm_obj: stock_ai.db.models.reddit_post.RedditPost | 
                 stock_ai.db.models.reddit_filterd_post.RedditFilteredPost) -> "RedditPost":
        return cls(
            reddit_id=orm_obj.reddit_id,
            flair=orm_obj.flair,
            title=orm_obj.title,
            selftext=orm_obj.selftext,
            score=orm_obj.score,
            num_comments=orm_obj.num_comments,
            upvote_ratio=orm_obj.upvote_ratio,
            created=orm_obj.created,
            url=orm_obj.url,
        )