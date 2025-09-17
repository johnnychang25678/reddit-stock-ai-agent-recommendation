from stock_ai.reddit.reddit_scraper import RedditPost
import statistics
from collections import Counter

class AfterScrapeFilter:
    def _get_quantiles(self, data:list[int] | list[float]) -> list[float]:
        if not data:
            return [0.0, 0.0, 0.0]
        if len(data) < 2:
            return [statistics.median(data)] * 3
        return statistics.quantiles(data, n=4)

    def __call__(self, posts:dict[str, list[RedditPost]]) -> dict[str, list[RedditPost]]:
        """
        Filter posts after scraping based on flair-specific criteria.

        For flair NEWS: keep all,
        For flair DD keep score >= q1 and upvote_ratio >= q1
        For flair YOLO keep score >= q3 and upvote_ratio >= q3
        """
        print("Applying after-scrape filtering...")

        filtered:dict[str, list[RedditPost]] = {}
        for flair, post_list in posts.items():
            if flair not in filtered:
                filtered[flair] = []

            scores = [post.score for post in post_list]
            upvote_ratios = [post.upvote_ratio for post in post_list]

            scores_quantiles = self._get_quantiles(scores)
            q1_score = scores_quantiles[0]
            q3_score = scores_quantiles[2]
            print(f"Flair: {flair}, Q1 Score: {q1_score}, Q3 Score: {q3_score}")

            upvote_ratios_quantiles = self._get_quantiles(upvote_ratios)
            q1_upvote_ratio = upvote_ratios_quantiles[0]
            q3_upvote_ratio = upvote_ratios_quantiles[2]
            print(f"Flair: {flair}, Q1 Upvote Ratio: {q1_upvote_ratio}, Q3 Upvote Ratio: {q3_upvote_ratio}")

            for post in post_list:
                if flair == "News":
                    filtered[flair].append(post)
                elif flair == "DD":
                    if post.score >= q1_score and post.upvote_ratio >= q1_upvote_ratio:
                        filtered[flair].append(post)
                elif flair == "YOLO":
                    if post.score >= q3_score and post.upvote_ratio >= q3_upvote_ratio:
                        filtered[flair].append(post)
        # count by flair
        print(f"After filtering, posts: {Counter({k: len(v) for k, v in filtered.items()})}")
        return filtered


