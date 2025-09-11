from dotenv import load_dotenv
from stock_ai.workflows.persistence.in_memory import InMemoryPersistence
from stock_ai.workflows.reddit_stock_workflow import init_workflow
import time
# import os
# import json
# from stock_ai.notifiers.discord.reddit_stock_notifier import send_stock_recommendations_to_discord
# with open("debug/result/final_recommendations_1757219552.json","r",encoding="utf-8") as f:
#     rec = json.load(f)
#     send_stock_recommendations_to_discord(rec)

def main():
    s = time.perf_counter()
    persistence = InMemoryPersistence()
    res = init_workflow("my_run_id", persistence).run()
    e = time.perf_counter()
    print(f"Workflow completed in {e - s:.2f} seconds.")
    pass


if __name__ == "__main__":
    load_dotenv()
    main()
