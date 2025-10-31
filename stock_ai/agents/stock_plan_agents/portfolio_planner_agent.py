import os, json, time

from stock_ai.agents.base_agent import BaseAgent
from stock_ai.agents.stock_plan_agents.pydantic_models import TradePlans
from stock_ai.yahoo_finance.types import StockSnapshot

class PortfolioPlannerAgent(BaseAgent):
    @property
    def system_prompt(self) -> str:
        return f"""# Role & Objective
- You are a cautious, compliance-friendly trading planner.
- You will be given a BUY candidate, or multiple candidates, and market snapshots (price, SMAs, ATR, 52w levels, RSI),
produce practical one trade plan for each candidate with entries, stops, take-profits, time horizons (days to hold), and a brief rationale.


# Guidelines
- Aim for risk:reward >= 2.0 on TP1 when feasible.
- Reasonable entries: pullbacks to SMA20/50, breakouts above recent resistance, or near-range re-tests.
- Stops: below recent swing low or 1.5-2.5x ATR below entry (whichever is more protective).
- Take profits: logical resistance zones (recent highs, 52w levels) or multiples of ATR (2x-3x).
- If data is thin or volatile, widen stops or lower confidence.
- Time horizon: 20-90 days by default (stretch to 120-180 for slower names).
- If a name looks overextended (RSI>70) and far above SMAs, suggest pullback entry or skip.

{self.COMMON_PROMPTS["AGENTIC_BALANCE"]}

"""

    def user_prompt(self, snapshots: list[StockSnapshot]) -> str:
        items = []
        for s in snapshots:
            if s.error:
                print(f"Skipping {s.ticker} due to error: {s.error}")
                continue
            items.append({
                "ticker": s.ticker,
                "price": s.price,
                "sma20": s.sma20,
                "sma50": s.sma50,
                "sma200": s.sma200,
                "atr14": s.atr14,
                "high_52w": s.high_52w,
                "low_52w": s.low_52w,
                "rsi14": s.rsi14,
                "asof": s.asof
            })

        return (
            "\n\nMarket snapshots of stock tickers:\n" +
            json.dumps(items, ensure_ascii=False)
        )

    def act(self, ticker_snapshots: list[StockSnapshot], remove_dup_tickers: bool = True) -> TradePlans:
        agent_cls = self.__class__.__name__
        print(f"{agent_cls} generating trade plans...")
        user = self.user_prompt(ticker_snapshots)

        start = time.perf_counter()
        resp = self.open_ai_client.responses.parse(
            model="gpt-5",
            instructions=self.system_prompt,
            input=user,
            text_format=TradePlans,
            reasoning={"effort": "medium"},
        )
        end = time.perf_counter()
        print(f"{agent_cls} completed in {end - start:.2f}s")

        result = resp.output_parsed
        if not result:
            raise ValueError(f"{agent_cls} result failed to parse")
        
        # a fallback in case the LLM returns multiple plans for the same ticker
        if remove_dup_tickers:
            seen = set()
            unique_plans = []
            for plan in result.plans:
                if plan.ticker not in seen:
                    seen.add(plan.ticker)
                    unique_plans.append(plan)
            result.plans = unique_plans

        return result
    
    def evaluate(self, result: TradePlans, **kwargs) -> TradePlans:
        return result
