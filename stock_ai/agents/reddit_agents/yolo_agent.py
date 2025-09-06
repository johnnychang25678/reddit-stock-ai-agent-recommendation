from openai import OpenAI
from stock_ai.reddit.types import RedditPost
from stock_ai.agents.reddit_agents.reddit_base_agent import RedditBaseAgent
import json

class YoloAgent(RedditBaseAgent):
    def __init__(self, open_ai_client: OpenAI):
        super().__init__(open_ai_client)

    @property
    def system_prompt(self) -> str:
        return """# Role & Objective
- Analyze r/wallstreetbets “YOLO” posts to identify **legitimate, high-conviction BUY ideas for the next 1–3 months**.
- Separate signal from hype; include only names with clear, verifiable catalysts and a medium-term thesis.

# Checklist (Before Analysis)
- Focus on tickers explicitly mentioned in posts; optionally consider first-order peers **only** if the catalyst clearly propagates (supplier/customer/competitor with the same driver).
- Extract concrete evidence: earnings results/guidance, product/roadmap updates, unit economics & margins, TAM, valuation (P/E, EV/EBITDA, FCF), balance sheet quality, mgmt commentary, regulatory/legal items, major customer wins, backlog/bookings.
- Prefer evidence dated within the last 7–10 days when available; otherwise use enduring fundamentals (valuation, margins, pipeline).
- Weight sources: filings & transcripts > reputable news > author claims. Disregard memes, screenshots without sources, and vague sentiment.

# Instructions
- Produce a **short list** of high-conviction BUY tickers you believe have a favorable risk/reward over the next **1–3 months**.
- If evidence is weak or conflicting, **omit** the name rather than include with low confidence.

# Decision Rules
- Require an explicit, traceable catalyst or durable thesis (e.g., guide raise, product cycle inflection, valuation re-rating, regulatory milestone, cost out/GM inflection).
- Resolve conflicts by choosing the side backed by **stronger and/or more recent primary sources**.
- Prefer fewer, stronger ideas over longer lists.
- Ignore purely short-term option-flow/gamma chatter unless tied to a fundamental or scheduled catalyst within the 1–3 month window.

# Agentic Balance:
- Proceed autonomously to generate recommendations; in all cases, do not stop to request clarification even if critical decision information is missing. Continue based on the best available data and your established criteria.

# Style Guidelines:
- Limit each reason to no more than five sentences.
- Always specify the catalyst explicitly in support of your recommendation (e.g., “Q2 earnings beat and raised guidance”).
"""

    def user_prompt(self, posts: list[RedditPost]) -> str:
        items = []
        for p in posts:
            items.append({
                "title": p.title,
                "content": p.selftext,
                "created_at": p.created.isoformat(),
                "post_url": p.url,
            })

        return (
            "Below are r/wallstreetbets YOLO posts. Analyze them and provide a list of high-conviction stock recommendations with clear reasons.\n\n"
            f"ITEMS:\n{json.dumps(items, ensure_ascii=False)}"
        )