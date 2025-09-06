from stock_ai.reddit.reddit_scraper import RedditScraper
from stock_ai.reddit.post_scrape_filter import AfterScrapeFilter
from dotenv import load_dotenv
from stock_ai.agents.reddit_agents.news_agent import NewsAgent
from stock_ai.agents.reddit_agents.dd_agent import DDAgent
from stock_ai.agents.reddit_agents.yolo_agent import YoloAgent
from stock_ai.yahoo_finance.yahoo_finance_client import YahooFinanceClient
from stock_ai.agents.stock_plan_agents.portfolio_planner_agent import PortfolioPlannerAgent
from openai import OpenAI
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


    open_ai_client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
    # send news to news agent for stock recommendations
    news_agent = NewsAgent(open_ai_client)
    news = filtered_posts["News"]
    recommendations = news_agent.act(news)
    print("Stock Recommendations:")
    print(recommendations.model_dump_json(indent=2))

    # send DD to DD agent for stock recommendations
    # dd_agent = DDAgent(open_ai_client)
    # dd_posts = filtered_posts["DD"]
    # dd_recommendations = dd_agent.act(dd_posts)
    # print("DD Stock Recommendations:")
    # print(dd_recommendations.model_dump_json(indent=2))

    # send YOLO to YOLO agent for stock recommendations
    # yolo_agent = YoloAgent(open_ai_client)
    # yolo_posts = filtered_posts["YOLO"]
    # yolo_recommendations = yolo_agent.act(yolo_posts)
    # print("YOLO Stock Recommendations:")
    # print(yolo_recommendations.model_dump_json(indent=2))
    # Example of using YahooFinanceClient
    yf_client = YahooFinanceClient()
    snapshots = []
    for rec in recommendations.recommendations:
        print(f"Fetching snapshot for {rec.ticker}...")
        snapshot = yf_client.get_yf_snapshot(rec.ticker)
        snapshots.append(snapshot)
    
    stock_plan_agent = PortfolioPlannerAgent(open_ai_client)
    trade_plans = stock_plan_agent.act(snapshots)
    print("Trade Plans:")
    print(trade_plans.model_dump_json(indent=2))

if __name__ == "__main__":
    load_dotenv()
    main()
