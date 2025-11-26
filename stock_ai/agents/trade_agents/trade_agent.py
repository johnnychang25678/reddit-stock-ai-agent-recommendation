import json
import time
from stock_ai.agents.base_agent import BaseAgent
from stock_ai.agents.trade_agents.pydantic_models import TradeDecisions


class TradeAgent(BaseAgent):
    """Trade agent that makes BUY/SELL/HOLD/DO_NOTHING decisions."""

    @property
    def system_prompt(self) -> str:
        return f"""# Role & Objective
You are a seasoned, pragmatic trading agent managing a retail stock portfolio.

Your job is to review:
- Stock recommendations from stock analysis experts
- Current portfolio state (cash balance and existing positions)
- Current market prices

Then decide BUY, SELL, HOLD, or DO_NOTHING for each ticker.

# Trading Guidelines

## Position Sizing
- Allocate approximately 15-25% of available cash per new BUY position
- Don't over-concentrate in a single stock (max 30% of total portfolio value)
- Calculate exact share quantities based on current market price

## BUY Decisions
- BUY recommended stocks with strong upside potential based on the experts' reasons and confidence levels
- Only BUY if you have sufficient cash available
- Consider recommendation confidence ("high" is more favorable than "low")
- Consider diversification - don't buy too many positions at once

## SELL Decisions
- SELL existing positions if:
  - You need to free up cash for better opportunities
  - Position has significant unrealized gains (take profits)
  - Position has significant unrealized losses (cut losses)

## HOLD Decisions
- HOLD existing positions that still have positive outlook
- HOLD if the stock appears in current recommendations and is performing reasonably

## DO_NOTHING Decisions
- DO_NOTHING if there is insufficient data or unclear market conditions
- DO_NOTHING if no action is warranted based on current analysis

## Risk Management
- Be conservative with cash - don't deploy all cash at once
- Maintain at least 20-30% cash buffer for flexibility
- Don't trade if market conditions are unclear or data is missing

{self.COMMON_PROMPTS["AGENTIC_BALANCE"]}

# Output Format
Return a structured list of trade decisions with:
- ticker: Stock symbol
- action: "BUY", "SELL", "HOLD", or "DO_NOTHING"
- quantity: Number of shares (0 for HOLD)
- reason: Brief explanation (1-2 sentences)
"""

    def user_prompt(
        self,
        recommendations: list[dict],
        prices: dict[str, float],
        portfolio_cash: float,
        existing_positions: list[dict]
    ) -> str:
        """
        Args:
            recommendations: List of dicts with keys: ticker, reason, confidence
            prices: Dict mapping ticker -> current_price
            portfolio_cash: Available cash balance
            existing_positions: List of dicts with keys: ticker, quantity, avg_entry_price, current_price, unrealized_pnl
        """
        # Format recommendations
        recs_data = []
        for rec in recommendations:
            recs_data.append({
                "ticker": rec.get("ticker"),
                "reason": rec.get("reason"),
                "confidence": rec.get("confidence"),
            })

        # Format existing positions with P&L
        positions_data = []
        total_position_value = 0.0
        for pos in existing_positions:
            market_value = pos.get("quantity", 0) * pos.get("current_price", 0.0)
            total_position_value += market_value
            positions_data.append({
                "ticker": pos.get("ticker"),
                "quantity": pos.get("quantity"),
                "avg_entry_price": pos.get("avg_entry_price"),
                "current_price": pos.get("current_price"),
                "market_value": market_value,
                "unrealized_pnl": pos.get("unrealized_pnl"),
            })

        portfolio_total = portfolio_cash + total_position_value

        prompt = f"""# Portfolio State
- Cash Balance: ${portfolio_cash:.2f}
- Total Position Value: ${total_position_value:.2f}
- Total Portfolio Value: ${portfolio_total:.2f}

# Existing Positions ({len(positions_data)} positions)
{json.dumps(positions_data, indent=2) if positions_data else "No existing positions"}

# New Recommendations ({len(recs_data)} recommendations)
{json.dumps(recs_data, indent=2)}

# Current Market Prices
{json.dumps(prices, indent=2)}

---

Based on the above data, make your BUY/SELL/HOLD/DO_NOTHING decisions for this week.
Consider both new recommendations and existing positions.
"""
        return prompt

    def act(
        self,
        recommendations: list[dict],
        prices: dict[str, float],
        portfolio_cash: float,
        existing_positions: list[dict]
    ) -> TradeDecisions:
        """Generate trade decisions based on inputs.

        Returns:
            TradeDecisions object with list of decisions
        """
        agent_cls = self.__class__.__name__
        print(f"{agent_cls} analyzing portfolio and generating trade decisions...")

        user_prompt = self.user_prompt(recommendations, prices, portfolio_cash, existing_positions)

        start = time.perf_counter()
        resp = self.open_ai_client.responses.parse(
            model="gpt-5",
            instructions=self.system_prompt,
            input=user_prompt,
            text_format=TradeDecisions,
            reasoning={"effort": "medium"},
        )
        end = time.perf_counter()
        print(f"{agent_cls} completed in {end - start:.2f}s")

        result = resp.output_parsed
        if not result:
            raise ValueError(f"{agent_cls} result failed to parse")

        print(f"{agent_cls} generated {len(result.decisions)} trade decisions")
        return result

    def evaluate(self, result: TradeDecisions, portfolio_cash: float) -> bool:
        """Basic validation of trade decisions.

        Args:
            result: TradeDecisions to validate
            portfolio_cash: Available cash

        Returns:
            True if valid, False otherwise
        """
        for decision in result.decisions:
            if decision.action == "BUY":
                # We'll validate exact costs in the execution step with real prices
                # Here just do basic sanity checks
                if decision.quantity <= 0:
                    print(f"Warning: BUY decision for {decision.ticker} has invalid quantity {decision.quantity}")
                    return False

        # Basic sanity check passed
        return True
