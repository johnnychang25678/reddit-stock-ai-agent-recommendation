from dotenv import load_dotenv
from stock_ai.workflows.reddit_stock_workflow import reddit_stock_workflow

def main():
    res = reddit_stock_workflow.run()
    print(res)

if __name__ == "__main__":
    load_dotenv()
    main()
