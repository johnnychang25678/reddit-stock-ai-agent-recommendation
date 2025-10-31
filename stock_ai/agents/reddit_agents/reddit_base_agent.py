from stock_ai.agents.base_agent import BaseAgent
from stock_ai.reddit.types import RedditPost
from stock_ai.agents.reddit_agents.pydantic_models import StockRecommendation, StockRecommendations
import time

class RedditBaseAgent(BaseAgent):
    """Base class for agents that analyze Reddit posts and provide stock recommendations.
    Sub-classes implement system_prompt and user_prompt methods.
    Shared act method to interact with OpenAI API and handle responses.
    """

    WEB_SEARCH_TOOL_PROMPT: str = """When analyzing posts, always perform a brief web search for each ticker to verify recent catalysts, earnings news, or filings before forming a recommendation.
Collect as much relevant information as possible from diverse sources. 
"""
    STYLE_GUIDELINES_PROMPT: str = """# Style
- Limit each reason to two paragraphs.
- If you pick a ticker that was indirectly mentioned (e.g., a supplier or competitor), clearly explain the linkage in the reason.
- Explicitly specify the catalyst (e.g., “FDA approval of new product X” or “Q3 revenue beat and guidance raise”)."""

    def act(self, posts: list[RedditPost]) -> StockRecommendations:
        agent_cls_name = self.__class__.__name__
        print(f"{agent_cls_name} acting on posts...")
        user_prompt = self.user_prompt(posts)
        start = time.perf_counter()
        resp = self.open_ai_client.responses.parse(
            model="gpt-5",
            instructions=self.system_prompt,
            input=user_prompt,
            text_format=StockRecommendations,
            reasoning={"effort": "medium"},
            # include=["web_search_call.action.sources"],
            tools=[{"type": "web_search"}],
        )
        end = time.perf_counter()
        print(f"{agent_cls_name} act() completed in {end - start:.2f} seconds.")
        # print(resp.output)

        # print(f"\nWeb Searches Performed:")
        # web_searches = [item for item in resp.output if item.type == 'web_search_call']
        # for i, search in enumerate(web_searches, 1):
        #     print(f"\n  Search {i}:")
        #     print(f"    Query: {search.action.query}")
        #     print(f"    Status: {search.status}")
        #     if hasattr(search.action, 'sources') and search.action.sources:
        #         print(f"    Sources: {len(search.action.sources)}")
        #         for src in search.action.sources:
        #             print(f"      - {src.url}")

        result = resp.output_parsed
        if not result:
            raise ValueError(f"{agent_cls_name} result failed to parse")

        return result

    def evaluate(self, result: StockRecommendations, actual_reddit_post_url: str) -> StockRecommendations:
        out = StockRecommendations(recommendations=[])
        for rec in result.recommendations:
            rec_copy = StockRecommendation(
                ticker=rec.ticker,
                decision=rec.decision,
                reason=rec.reason,
                confidence=rec.confidence,
                reddit_post_url=actual_reddit_post_url
            )
            out.recommendations.append(rec_copy)
        return out