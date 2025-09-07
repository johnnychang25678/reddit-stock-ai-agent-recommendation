from dotenv import load_dotenv
from stock_ai.workflows.reddit_stock_workflow import reddit_stock_workflow
import os
import time

def main():
    s = time.perf_counter()
    res = reddit_stock_workflow.run()
    e = time.perf_counter()
    print(f"Workflow completed in {e - s:.2f} seconds.")
    print(res["final_recommendations"])
    os.makedirs("debug", exist_ok=True)
    os.makedirs("debug/result", exist_ok=True)
    # write final recommendations as json
    import json
    with open(f"debug/result/final_recommendations_{int(time.time())}.json","w",encoding="utf-8") as f:
        json.dump(res["final_recommendations"], f, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    load_dotenv()
    main()
