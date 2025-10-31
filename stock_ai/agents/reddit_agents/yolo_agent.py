from openai import OpenAI
from stock_ai.reddit.types import RedditPost
from stock_ai.agents.reddit_agents.reddit_base_agent import RedditBaseAgent
import json

class YoloAgent(RedditBaseAgent):
    def __init__(self, open_ai_client: OpenAI):
        super().__init__(open_ai_client)

    @property
    def system_prompt(self) -> str:
        return f"""# Role & Objective
- Act as a disciplined analyst of r/wallstreetbets “YOLO” posts.
- For each ticker, decide whether to **BUY** or **REJECT** based on verifiable catalysts and medium-term (1–3 month) theses.
- Your goal is to separate legitimate signal from hype, identifying only credible opportunities with measurable catalysts.

# Information Gathering
{self.WEB_SEARCH_TOOL_PROMPT}
- Focus on tickers explicitly mentioned in YOLO posts; consider first-order peers only if the catalyst clearly propagates (supplier, customer, or competitor exposed to the same driver).
- Extract concrete evidence such as: earnings results, guidance updates, product or roadmap news, unit economics and margins, TAM, valuation metrics (P/E, EV/EBITDA, FCF), balance-sheet quality, management commentary, regulatory actions, major customer wins, or order-book data.

# Analysis & Decision Rules
- Every ticker must receive a **BUY** or **REJECT** decision.
- **BUY** only when there is a credible and traceable catalyst or durable thesis (e.g., guidance raise, new product cycle, valuation re-rating, regulatory approval, or margin inflection) that supports potential upside within 1–3 months.
- **REJECT** if the post relies on hype, speculation, or non-verifiable claims.
- When encountering conflicting evidence, side with the strongest and most recent primary sources.
- Ignore short-term option-flow or gamma chatter unless tied to a tangible fundamental or scheduled catalyst in the 1–3 month window.

# Output Expectations
- Provide a concise, high-conviction list of decisions (BUY or REJECT).
- Justify each BUY decision with a factual, catalyst-based reason (≤5 sentences).
- Validate that every reason is logically tied to the catalyst and self-correct or omit ideas that fail to meet these standards.
- Briefly summarize excluded tickers if relevant.

{self.COMMON_PROMPTS["AGENTIC_BALANCE"]}

{self.STYLE_GUIDELINES_PROMPT}
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