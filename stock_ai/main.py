from dotenv import load_dotenv
from stock_ai.workflows.reddit_stock_workflow import reddit_stock_workflow
import time
# import os
# import json
# from stock_ai.notifiers.discord.reddit_stock_notifier import send_stock_recommendations_to_discord
# with open("debug/result/final_recommendations_1757219552.json","r",encoding="utf-8") as f:
#     rec = json.load(f)
#     send_stock_recommendations_to_discord(rec)

def main():
    s = time.perf_counter()
    res = reddit_stock_workflow.run()
    e = time.perf_counter()
    print(f"Workflow completed in {e - s:.2f} seconds.")
    print(res["final_recommendations"])


if __name__ == "__main__":
    load_dotenv()
    main()
