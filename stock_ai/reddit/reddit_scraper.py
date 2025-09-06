from typing import Any, Iterator
from datetime import datetime, timedelta, timezone
import praw
from stock_ai.reddit.types import RedditPost

class RedditScraper:
    def __init__(self, client_id, client_secret, user_agent):
        self.reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )

    def _get_subreddit_posts(self, subreddit_name:str, limit=1000) -> Iterator[Any]:
        """Fetches new posts from a specified subreddit.

        :returns: Iterator of posts
        """
        subreddit = self.reddit.subreddit(subreddit_name)
        return subreddit.new(limit=limit)

    def scrape(self, 
               subreddit_name:str,
               flairs_want:set[str]=None,
               skip_empty_selftext:bool=True,
               cut_off_days=7, 
               limit=1000) -> dict[str, list[RedditPost]]:
        """Scrapes posts from a subreddit based on specified criteria.

        :param subreddit_name: Name of the subreddit to scrape from.
        :param flairs_want: Set of flairs to filter posts by. If None, all flairs are included.
        :param skip_empty_selftext: If True, skips posts with empty selftext.
        :param cut_off_days: Only includes posts from the last 'cut_off_days' days.
        :param limit: Maximum number of posts to fetch.

        :returns: Dictionary mapping flairs to lists of RedditPost objects.
        """
        print(f"Scraping r/{subreddit_name} for posts with flairs {flairs_want}, skipping empty selftext: {skip_empty_selftext}, cut off days: {cut_off_days}, limit: {limit}")
        posts = self._get_subreddit_posts(subreddit_name, limit=limit)
        collect:dict[str, list[dict[str, Any]]] = {}
        cutoff = datetime.now(timezone.utc) - timedelta(days=cut_off_days)

        for post in posts:
            created = datetime.fromtimestamp(post.created_utc, tz=timezone.utc)
            # only care about first cut_off_days posts
            if created < cutoff:
                break 

            flair = post.link_flair_text
            if flairs_want and flair not in flairs_want:
                continue

            if skip_empty_selftext and len(post.selftext) == 0:
                continue

            # print("====================================")
            # print("FLAIR:", flair)
            # print({
            #     "title": post.title,
            #     "score": post.score,            # net upvotes
            #     "comments": post.num_comments,  # total comments
            #     "upvote_ratio": post.upvote_ratio,
            #     "created": datetime.fromtimestamp(post.created_utc),
            # })

            if flair not in collect:
                collect[flair] = []

            reddit_post = RedditPost(
                title=post.title,
                selftext=post.selftext,
                score=post.score,
                comments=post.num_comments,
                upvote_ratio=post.upvote_ratio,
                created=datetime.fromtimestamp(post.created_utc),
                url=post.url
            )

            collect[flair].append(reddit_post)

        print(f"Scraped {sum(len(v) for v in collect.values())} posts from r/{subreddit_name}") 

        return collect