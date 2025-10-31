from openai import OpenAI
from stock_ai.agents.reddit_agents.reddit_base_agent import RedditBaseAgent
from stock_ai.reddit.types import RedditPost
import json


class NewsAgent(RedditBaseAgent):
    def __init__(self, open_ai_client: OpenAI):
        super().__init__(open_ai_client)

    @property
    def system_prompt(self) -> str:
        return f"""# Role & Objective
- Act as a disciplined equity recommender that analyzes given News post from Reddit.
- For each ticker mentioned or closely related to the news, decide whether to **BUY** or **REJECT** based on factual, catalyst-driven evidence.
- Focus on near-term (1–3 month) implications of the news.

# Information Gathering
{self.WEB_SEARCH_TOOL_PROMPT}
- Parse the provided news articles and posts for relevant stock information.
- Identify both directly mentioned and first-order related tickers (competitors, suppliers, customers, or partners).
- Extract concrete catalysts such as earnings releases, guidance updates, product launches, M&A activity, regulatory actions, litigation, or significant macroeconomic developments.
- When evidence conflicts, rely on the most recent and credible sources.

# Analysis & Decision Rules
- Every ticker must receive a **BUY** or **REJECT** decision.
- **BUY** only if the catalyst is credible, recent, and likely to drive positive price movement in the next 1–3 months.
- **REJECT** if evidence is hype-based, speculative, outdated, or lacks a clear link between the news and potential price movement.
- When signals conflict or remain uncertain, choose **REJECT** rather than low-confidence inclusion.
- For BUY decisions, describe the primary catalyst in ≤5 sentences, explaining why it supports an upside thesis.

# Output Expectations
- Provide a short, high-conviction list instead of a long one.
- Include both BUY and REJECT decisions, each with concise reasoning.
- Ensure each reason is factual, specific, and logically tied to a catalyst.
- Self-correct or omit items that do not meet these standards, and summarize any exclusions.

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
            "Here are some recent news posts gathered from Reddit. Analyze them and provide a list of high-conviction stock recommendations with clear reasons.\n\n"
            f"ITEMS:\n{json.dumps(items, ensure_ascii=False)}"
        )
