from dotenv import load_dotenv
from stock_ai.workflows.reddit_stock_workflow import reddit_stock_workflow
import time

def main():
    s = time.perf_counter()
    res = reddit_stock_workflow.run()
    e = time.perf_counter()
    print(f"Workflow completed in {e - s:.2f} seconds.")
    print(res["final_recommendations"])


if __name__ == "__main__":
    load_dotenv()
    main()
