from stock_ai.agents.base_agent import BaseAgent
from openai import OpenAI
from stock_ai.reddit.types import RedditPost
from datetime import datetime
from stock_ai.agents.pydantic_models import StockRecommendations
import json
import time



class NewsAgent(BaseAgent):
    def __init__(self, open_ai_client: OpenAI):
        super().__init__(open_ai_client)

    @property
    def system_prompt(self) -> str:
        return """Role and Objective:
        - Act as a decisive equity recommender, delivering high-conviction stock recommendations based on given news articles.

Checklist (before analysis):
- Parse posts and news for relevant stock information.
- Extract directly mentioned and first-order related tickers.
- Identify and evaluate concrete catalysts from recent events.
- Prioritize strongest catalysts and manage conflicting signals.
- Formulate concise, explicit recommendations with clear reasoning.

Instructions:
- Analyze posts and news articles about stocks.
- Identify tickers that are directly mentioned or first-order related (including competitors, suppliers, customers, and partners).
- Offer the tickers that you believe have the highest likelihood of a positive price move in the next 1-3 months.

Decision Rules:
- Prioritize recommendations tied to specific, concrete catalysts such as earnings, guidance updates, product launches, M&A activity, regulatory actions, litigation, or significant macroeconomic events.
- Give preference to catalysts that have occurred within the last 7–10 days when date information is available.
- When encountering conflicting signals, choose the position backed by the more recent or stronger catalyst and explain your reasoning.
- Avoid recommendations based on vague hype; only include names with an identified and explicit catalyst.
- Prefer a smaller number of high-confidence recommendations over larger lists of weaker suggestions.

Agentic Balance:
- Proceed autonomously to generate recommendations; in all cases, do not stop to request clarification even if critical decision information is missing. Continue based on the best available data and your established criteria.

Style Guidelines:
- Limit each reason to no more than five sentences.
- Always specify the catalyst explicitly in support of your recommendation (e.g., “Q2 earnings beat and raised guidance”).
"""

    def user_prompt(self, posts: list[RedditPost]) -> str:
        items = []
        for p in posts:
            items.append({
                "title": p.title,
                "content": p.selftext,
                "created_at": p.created.isoformat() if isinstance(p.created, datetime) else str(p.created),
            })

        return (
            "Here are some recent news posts gathered from Reddit. Analyze them and provide a list of high-conviction stock recommendations with clear reasons.\n\n"
            f"ITEMS:\n{json.dumps(items, ensure_ascii=False)}"
        )


    def act(self, posts: list[RedditPost]) -> StockRecommendations:
        print("NewsAgent acting on posts...")
        user_prompt = self.user_prompt(posts)
        start = time.perf_counter()
        resp = self.open_ai_client.responses.parse(
            model="gpt-5",
            instructions=self.system_prompt,
            input=user_prompt,
            text_format=StockRecommendations,
            reasoning={"effort": "medium"},
        )
        end = time.perf_counter()
        print(f"NewsAgent act() completed in {end - start:.2f} seconds.")

        print("Raw response:", resp)

        result = resp.output_parsed

        # write system promt, user prompt, and response to a single file for debugging
        with open(f"news_agent_debug_{int(time.time())}.txt", "w", encoding="utf-8") as f:
            f.write("SYSTEM PROMPT:\n")
            f.write(self.system_prompt)
            f.write("\n\nUSER PROMPT:\n")
            f.write(user_prompt)
            f.write("\n\nRESPONSE:\n")
            # Convert Pydantic model to dict for JSON serialization
            result_dict = result.model_dump() if hasattr(result, "model_dump") else result.dict()
            f.write(json.dumps(result_dict, ensure_ascii=False, indent=2))

        return resp.output_parsed

