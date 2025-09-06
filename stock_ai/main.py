from stock_ai.reddit.reddit_scraper import RedditScraper
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from dotenv import load_dotenv
import os

def main():
    reddit_scraper = RedditScraper(
        client_id=os.getenv("REDDIT_CLIENT_ID"),
        client_secret=os.getenv("REDDIT_CLIENT_SECRET"),
        user_agent=os.getenv("REDDIT_USER_AGENT")
    )
    FLAIRS_WANT = {"News", "DD", "YOLO"}
    CUT_OFF_DAYS = 7
    SUBREDDIT_NAME = "wallstreetbets"

    posts = reddit_scraper.scrape(
        subreddit_name=SUBREDDIT_NAME,
        flairs_want=FLAIRS_WANT,
        skip_empty_selftext=True,
        cut_off_days=CUT_OFF_DAYS,
    )

    after_scrape_filter = AfterScrapeFilter()
    filtered_posts = after_scrape_filter(posts)
    print("Filtered Posts:")
    for flair, post_list in filtered_posts.items():
        print(f"Flair: {flair}, Number of Posts: {len(post_list)}")
        for post in post_list:
            print(f"  - Title: {post.title}, Score: {post.score}, Upvote Ratio: {post.upvote_ratio}")  



if __name__ == "__main__":
    load_dotenv()
    main()
