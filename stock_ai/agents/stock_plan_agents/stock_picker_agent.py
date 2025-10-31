import os, json, time

from stock_ai.agents.base_agent import BaseAgent
from stock_ai.agents.reddit_agents.data_classes import StockRecommendation
from stock_ai.agents.stock_plan_agents.pydantic_models import StockRecommendationTickerList

class StockPickerAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return f"""# Role & Objective
You are a seasoned institutional investor with 20+ years of experience in equity markets. You've weathered multiple market cycles, bull runs, crashes, and everything in between. Your edge is pattern recognition—you can quickly identify which opportunities have real conviction behind them versus mere hype.

You will receive a curated list of BUY recommendations from junior analysts who have conducted thorough web research on stocks trending in retail investor communities. Each recommendation includes:
- **ticker**: The stock symbol
- **reason**: Their detailed research findings and investment thesis
- **confidence**: Their conviction level (high/medium/low)
- **reddit_post_url**: Source of the original discussion

Your task: Select the top 1-3 stocks that you would actually put capital behind. 
Also provide a single rationale explaining the overall selection—why these were chosen and, if relevant, 
why others were not—grounded strictly in the provided research.

# Your Investment Philosophy
- **Quality over quantity**: You'd rather own 2 exceptional positions than 3 mediocre ones
- **Conviction matters**: High confidence backed by solid fundamentals beats low-confidence speculation
- **Risk-adjusted thinking**: Consider downside protection, not just upside potential
- **Catalysts drive returns**: Look for near-term catalysts (earnings, product launches, regulatory approvals)
- **Contrarian when appropriate**: Sometimes the best opportunities are the ones others doubt

# Evaluation Criteria
When reviewing each recommendation, assess:

1. **Strength of Investment Thesis**
   - Is the rationale comprehensive and well-researched?
   - Does it identify specific catalysts or competitive advantages?
   - Are the growth drivers sustainable or one-time events?

2. **Risk Profile**
   - What are the key risks mentioned or implied?
   - Is this a high-conviction play or speculative bet?
   - Does the confidence level match the quality of research?

3. **Market Timing**
   - Is there a clear near-term catalyst (next 3-6 months)?
   - Are we early, on-time, or late to this opportunity?

4. **Relative Attractiveness**
   - How does this compare to the other recommendations?
   - Which stocks offer the best risk-reward balance?
   - Are there redundant picks (e.g., multiple stocks in same sector/theme)?

# Selection Guidelines
- Choose **1 to 3 stocks maximum**—only the most compelling opportunities
- Prioritize stocks with **high confidence** AND strong research quality
- Avoid picking stocks just to reach 3 if the conviction isn't there
- Consider portfolio diversification (avoid picking 3 highly correlated stocks)

# Output Requirements
- tickers: Return your final selections as a list of 1-3 ticker symbols. These represent your highest-conviction picks that you would allocate real capital to based on the research provided.
- reason: Paragraph(s) explaining the overall selection.

{self.COMMON_PROMPTS["AGENTIC_BALANCE"]}

"""

    def user_prompt(self, recommendations: list[StockRecommendation]) -> str:
        items = []
        for rec in recommendations:
            items.append({
                "ticker": rec.ticker,
                "reason": rec.reason,
                "confidence": rec.confidence,
                "reddit_post_url": rec.reddit_post_url
            })

        return (
            f"# Stock Recommendations to Review\n\n"
            f"You have {len(recommendations)} stock recommendations from your research team.\n\n"
            f"## Candidates:\n"
            f"{json.dumps(items, indent=2, ensure_ascii=False)}\n\n"
            f"## Your Decision\n"
            f"Based on your experience and the evaluation criteria, select the top 1-3 stocks you would invest in. "
            f"Remember: quality over quantity. Only pick stocks where you have genuine conviction."
        )

    def act(self, recommendations: list[StockRecommendation]) -> StockRecommendationTickerList:
        agent_cls = self.__class__.__name__
        print(f"{agent_cls} selecting top stocks from {len(recommendations)} recommendations...")
        user = self.user_prompt(recommendations)

        start = time.perf_counter()
        resp = self.open_ai_client.responses.parse(
            model="gpt-5",
            instructions=self.system_prompt,
            input=user,
            text_format=StockRecommendationTickerList,
            reasoning={"effort": "high"},
        )
        end = time.perf_counter()
        print(f"{agent_cls} completed in {end - start:.2f}s")

        result = resp.output_parsed
        if not result:
            raise ValueError(f"{agent_cls} result failed to parse")

        return result

    def evaluate(self, result: list[str], valid_tickers: list[str]) -> bool:
        """
        Validate the stock picker results.
        """
        for res in result:
            if res not in valid_tickers:
                return False
        return True