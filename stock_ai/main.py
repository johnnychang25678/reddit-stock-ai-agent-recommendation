from dotenv import load_dotenv
from stock_ai.workflows.reddit_stock_workflow import reddit_stock_workflow
from stock_ai.notifiers.discord.discord_client import DiscordClient
from stock_ai.notifiers.discord.embed_builder import build_embed
import os
import time
import json

def main():
    data = None
    # read from my sample json file
    # with open("debug/result/final_recommendations_1757212818.json", "r", encoding="utf-8") as f:
    #     data = json.load(f)

    # s = time.perf_counter()
    # res = reddit_stock_workflow.run()
    # e = time.perf_counter()
    # print(f"Workflow completed in {e - s:.2f} seconds.")
    # print(res["final_recommendations"])
    # data = res["final_recommendations"]

    if not data:
        print("No data, nothing happened")
        return

    # write final recommendations as json
    os.makedirs("debug", exist_ok=True)
    os.makedirs("debug/result", exist_ok=True)
    with open(f"debug/result/final_recommendations_{int(time.time())}.json","w",encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    # send to discord
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL_TEST")
    discord_client = DiscordClient(webhook_url)
    
    week_str = time.strftime("%Y-%m-%d", time.localtime(time.time() - 7*24*3600))
    discord_client.send_message(
        f"""
        ## Stock AI Recommendations for week of {week_str}

        ### Legend for Trading Plan fields:

    - Entry: The price at which the trader enters the position.
    - Stop: The price at which the trader will exit the position to prevent further losses.
    - Targets: The prices at which the trader plans to take profits.
    - Horizon: The time frame for the trade.
    - R/R: The risk-to-reward ratio of the trade. (e.g., 1.5 means potential reward is 1.5 times the risk taken)
    """
    )

    for ticker, info in data.items():
        embed = build_embed(ticker, info)
        discord_client.send_embed(embed)
        time.sleep(0.5)


if __name__ == "__main__":
    load_dotenv()
    main()
