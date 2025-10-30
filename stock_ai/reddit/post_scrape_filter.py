from stock_ai.reddit.reddit_scraper import RedditPost
import statistics
import random
from collections import Counter

class AfterScrapeFilter:
    def _get_quantiles(self, data: list[int] | list[float]) -> list[float]:
        """Calculate Q1, Q2 (median), Q3 quantiles."""
        if not data:
            return [0.0, 0.0, 0.0]
        if len(data) < 3:
            return [statistics.median(data)] * 3
        return statistics.quantiles(data, n=4)

    def _select_top_and_random_q2(self, post_list: list[RedditPost], flair: str) -> list[RedditPost]:
        """
        Select top 1 by score + 1 random from top 50% (excluding the #1).
        This balances quality with discovery of underrated posts.
        """
        if not post_list:
            return []
        
        # Sort by score descending
        posts_sorted = sorted(post_list, key=lambda p: p.score or 0, reverse=True)
        
        # Always take top 1
        selected = [posts_sorted[0]]
        top_title = posts_sorted[0].title[:50] + "..." if len(posts_sorted[0].title) > 50 else posts_sorted[0].title
        print(f"  [{flair}] Top post: '{top_title}' (score: {posts_sorted[0].score})")
        
        # Select 1 random from top 50% (excluding the #1 post)
        if len(posts_sorted) >= 3:
            scores = [p.score or 0 for p in posts_sorted]
            quantiles = self._get_quantiles(scores)
            median = quantiles[1]  # 50th percentile (median)
            
            # Get posts above median, excluding the top 1
            top_50_percent = [p for p in posts_sorted[1:] if (p.score or 0) >= median]
            
            if top_50_percent:
                random_pick = random.choice(top_50_percent)
                selected.append(random_pick)
            else:
                print(f"  [{flair}] No posts in top 50% range (median: {median:.0f})")
        else:
            print(f"  [{flair}] Not enough posts for top 50% selection (need >= 3, got {len(posts_sorted)})")
        
        return selected

    def __call__(self, posts: dict[str, list[RedditPost]]) -> dict[str, list[RedditPost]]:
        """
        Filter posts after scraping:
        - Select top 1 by score per flair
        - Select 1 random from top 50% (above median, excluding #1) per flair
        
        Result: Max 2 posts per flair (top quality + exploratory discovery)
        """
        print("Applying after-scrape filtering (top 1 + top 50% random)...")

        filtered: dict[str, list[RedditPost]] = {}
        for flair, post_list in posts.items():
            if not post_list:
                filtered[flair] = []
                continue
            
            filtered[flair] = self._select_top_and_random_q2(post_list, flair)
        
        print(f"After filtering, posts: {Counter({k: len(v) for k, v in filtered.items()})}")
        return filtered


