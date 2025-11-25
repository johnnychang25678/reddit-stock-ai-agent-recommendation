"""Weekly trade bot workflow - Simplified version.

This workflow:
1. Prepares trade inputs (recommendations + prices + portfolio state)
2. Calls TradeAgent to decide + executes trades atomically
3. Sends Discord notification
"""

from stock_ai.agents.trade_agents.trade_agent import TradeAgent
from stock_ai.yahoo_finance.yahoo_finance_client import YahooFinanceClient
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.workflow_base import StepFn, StepFns, Step, Workflow
from stock_ai.workflows.common.api_clients import get_openai_client
from stock_ai.workflows.common.utils import idempotency_check
from stock_ai.workflows.common.common_step_fns import s_insert_run_metadata
from stock_ai.notifiers.discord.trade_notifier import send_trade_summary_to_discord
from stock_ai.workflows.run_id_generator import RunIdType
from stock_ai.agents.stock_plan_agents.data_classes import FinalRecommendation

from sqlalchemy import text
from datetime import datetime, timezone
import math


# Configuration
DEFAULT_PORTFOLIO_NAME = "weekly_trade_bot"
DEFAULT_INITIAL_CAPITAL = 10000.00


def s_prepare_trade_inputs(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Step 1: Prepare all inputs for the trade agent.

    This step:
    - Fetches final recommendations from reddit workflow
    - Fetches current market prices for those tickers
    - Fetches portfolio state (cash balance, existing positions)
    - Stores everything needed for the agent step
    """
    if idempotency_check(persistence, run_id, "trade_inputs"):
        print(f"Trade inputs already prepared for run_id {run_id}, skipping")
        return

    # 1. Get final recommendations from most recent reddit workflow run
    # stock_trade_run_id = RunIdType.REDDIT_STOCK_RECOMMENDATION.value + "_" + run_id.split("_")[-1]
    # final_recs = persistence.get("final_recommendations", run_id=stock_trade_run_id)
    test_run_id = RunIdType.TEST_RUN.value + "_" + run_id.split("_")[-1]
    final_recs = persistence.get("final_recommendations", run_id=test_run_id)


    if not final_recs or len(final_recs) == 0:
        print("No final recommendations found, workflow will exit early")
        return

    rec_tickers = [rec.ticker for rec in final_recs]

    print(f"Preparing trade inputs for {rec_tickers}...")


    # 2. Get or create portfolio
    text_clause = text("SELECT * FROM portfolios WHERE name = :name")
    existing = persistence.query(text_clause, {"name": DEFAULT_PORTFOLIO_NAME})

    if not existing or len(existing) == 0:
        print(f"Creating new portfolio '{DEFAULT_PORTFOLIO_NAME}'...")
        row = {
            "name": DEFAULT_PORTFOLIO_NAME,
            "cash_balance": DEFAULT_INITIAL_CAPITAL,
            "total_value": DEFAULT_INITIAL_CAPITAL,
            "initial_capital": DEFAULT_INITIAL_CAPITAL,
            "last_update_run_id": run_id,
        }
        persistence.set("portfolios", [row])
        print(f"Created portfolio with ${DEFAULT_INITIAL_CAPITAL:.2f} initial capital")

        # Reload portfolio
        existing = persistence.query(text_clause, {"name": DEFAULT_PORTFOLIO_NAME})

    portfolio = existing[0]
    portfolio_id = portfolio.id
    cash_balance = portfolio.cash_balance


    # 3. Get existing positions
    text_clause = text("SELECT * FROM positions WHERE portfolio_id = :portfolio_id")
    positions_rows = persistence.query(text_clause, {"portfolio_id": portfolio_id})

    # 4. Fetch current market prices for the recommended tickers and existing positions
    yf_client = YahooFinanceClient()
    prices = {}

    for ticker in rec_tickers:
        print(f"Fetching current price for {ticker}")
        current_price = yf_client.get_current_price(ticker)
        if not math.isnan(current_price):
            prices[ticker] = current_price
        else:
            print(f"Warning: Could not fetch price for {ticker}")
    for pos in positions_rows:
        if pos.ticker not in prices:
            print(f"Fetching current price for existing position {pos.ticker}")
            current_price = yf_client.get_current_price(pos.ticker)
            if not math.isnan(current_price):
                prices[pos.ticker] = current_price
            else:
                print(f"Warning: Could not fetch price for {pos.ticker}")

    # Update existing positions with current prices
    for pos in positions_rows:
        if pos.ticker in prices:
            current_price = prices[pos.ticker]
            unrealized_pnl = (current_price - pos.avg_entry_price) * pos.quantity

            # Update position
            text_clause = text(
                "UPDATE positions SET current_price = :current_price, "
                "unrealized_pnl = :unrealized_pnl, updated_at = :updated_at "
                "WHERE id = :id"
            )
            persistence.write(text_clause, {
                "id": pos.id,
                "current_price": current_price,
                "unrealized_pnl": unrealized_pnl,
                "updated_at": datetime.now(timezone.utc),
            })

    # Reload positions with updated prices
    positions_rows = persistence.query(
        text("SELECT * FROM positions WHERE portfolio_id = :portfolio_id"), 
        {"portfolio_id": portfolio_id})

    # 5. Store prepared inputs
    recs_list = []
    for rec in final_recs:
        recs_list.append({
            "ticker": rec.ticker,
            "reason": rec.reason,
            "confidence": rec.confidence,
            "reddit_post_url": rec.reddit_post_url,
            "final_recommendation_id": rec.id,
        })

    positions_list = []
    for pos in positions_rows:
        positions_list.append({
            "ticker": pos.ticker,
            "quantity": pos.quantity,
            "avg_entry_price": pos.avg_entry_price,
            "current_price": pos.current_price,
            "unrealized_pnl": pos.unrealized_pnl,
        })

    # Store prepared inputs in database
    trade_input_row = {
        "run_id": run_id,
        "has_data": True,
        "portfolio_id": portfolio_id,
        "portfolio_cash": cash_balance,
        "recommendations_json": recs_list,
        "prices_json": prices,
        "positions_json": positions_list,
    }
    
    persistence.set("trade_inputs", [trade_input_row])

    print(f"Prepared trade inputs: {len(recs_list)} recommendations, {len(prices)} prices, {len(positions_list)} positions")


def s_trade_decision_and_execute(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Step 2: Agent makes decisions and executes trades atomically.

    This step:
    - Calls TradeAgent to make BUY/SELL/HOLD decisions
    - Immediately executes all trades
    - Updates positions, portfolio, and creates performance snapshot
    - All DB updates happen in this single step for atomicity
    """
    if idempotency_check(persistence, run_id, "trades"):
        print(f"Trades already executed for run_id {run_id}, skipping")
        return

    # 1. Load prepared inputs
    trade_inputs = persistence.get("trade_inputs", run_id=run_id)
    if not trade_inputs or len(trade_inputs) == 0:
        print("No trade inputs found, skipping trade execution")
        return

    input_data = trade_inputs[0]

    if not input_data.has_data:
        print("Trade inputs indicate no data available, skipping")
        return

    portfolio_id = input_data.portfolio_id
    portfolio_cash = input_data.portfolio_cash
    recommendations = input_data.recommendations_json
    prices = input_data.prices_json
    existing_positions = input_data.positions_json

    print(f"Loaded inputs: cash=${portfolio_cash:.2f}, {len(recommendations)} recs, {len(existing_positions)} positions")

    # 2. Call TradeAgent to make decisions
    openai = get_openai_client()
    trade_agent = TradeAgent(openai)

    decisions = trade_agent.act(
        recommendations=recommendations,
        prices=prices,
        portfolio_cash=portfolio_cash,
        existing_positions=existing_positions
    )

    # Validate decisions
    if not trade_agent.evaluate(decisions, portfolio_cash):
        print("Trade decisions failed validation, aborting execution")
        return

    print(f"Agent generated {len(decisions.decisions)} decisions")

    # 3. Execute trades atomically
    trades = []
    # this map will be used as a final state of positions after all trades
    # will delete all positions in db and recreate based on this map
    positions_by_ticker = {pos["ticker"]: pos for pos in existing_positions}
    cash_balance = portfolio_cash

    for decision in decisions.decisions:
        ticker = decision.ticker
        action = decision.action
        quantity = decision.quantity
        reason = decision.reason
        current_price = prices.get(ticker)

        if not current_price:
            print(f"Warning: No price available for {ticker}, skipping")
            continue

        # Find recommendation for linking
        rec = next((r for r in recommendations if r["ticker"] == ticker), None)
        final_rec_id = rec["final_recommendation_id"] if rec else None

        if action == "BUY":
            # Execute BUY
            total_cost = quantity * current_price

            if total_cost > cash_balance:
                print(f"Insufficient cash for BUY {quantity} {ticker} (need ${total_cost:.2f}, have ${cash_balance:.2f}), skipping")
                continue

            trade = {
                "portfolio_id": portfolio_id,
                "run_id": run_id,
                "ticker": ticker,
                "action": "BUY",
                "quantity": quantity,
                "price": current_price,
                "total_cost": total_cost,
                "reason": reason,
                "realized_pnl": None,
                "final_recommendation_id": final_rec_id,
            }
            trades.append(trade)

            cash_balance -= total_cost

            # Create or update position
            if ticker in positions_by_ticker:
                # Add to existing position
                pos = positions_by_ticker[ticker]
                new_quantity = pos["quantity"] + quantity
                new_avg_entry = ((pos["avg_entry_price"] * pos["quantity"]) + (current_price * quantity)) / new_quantity
                pos["quantity"] = new_quantity
                pos["avg_entry_price"] = new_avg_entry
                pos["current_price"] = current_price
                pos["unrealized_pnl"] = (current_price - new_avg_entry) * new_quantity
            else:
                # New position
                positions_by_ticker[ticker] = {
                    "ticker": ticker,
                    "quantity": quantity,
                    "avg_entry_price": current_price,
                    "current_price": current_price,
                    "unrealized_pnl": 0.0,
                }

            print(f"BUY {quantity} {ticker} @ ${current_price:.2f} = ${total_cost:.2f}")

        elif action == "SELL":
            # Execute SELL
            if ticker not in positions_by_ticker:
                print(f"Warning: Cannot SELL {ticker}, no position exists")
                continue

            pos = positions_by_ticker[ticker]
            sell_quantity = min(quantity, pos["quantity"])  # Can't sell more than we have

            total_proceeds = sell_quantity * current_price
            realized_pnl = (current_price - pos["avg_entry_price"]) * sell_quantity

            trade = {
                "portfolio_id": portfolio_id,
                "run_id": run_id,
                "ticker": ticker,
                "action": "SELL",
                "quantity": sell_quantity,
                "price": current_price,
                "total_cost": total_proceeds,
                "reason": reason,
                "realized_pnl": realized_pnl,
                "final_recommendation_id": None,
            }
            trades.append(trade)

            cash_balance += total_proceeds

            # Update or remove position
            if sell_quantity >= pos["quantity"]:
                # Sold entire position
                del positions_by_ticker[ticker]
            else:
                # Partial sell
                pos["quantity"] -= sell_quantity
                pos["unrealized_pnl"] = (current_price - pos["avg_entry_price"]) * pos["quantity"]

            print(f"SELL {sell_quantity} {ticker} @ ${current_price:.2f} = ${total_proceeds:.2f}, P&L: ${realized_pnl:.2f}")

        elif action == "HOLD":
            # Just log HOLD, position already updated in prepare step
            if ticker in positions_by_ticker:
                pos = positions_by_ticker[ticker]
                trade = {
                    "portfolio_id": portfolio_id,
                    "run_id": run_id,
                    "ticker": ticker,
                    "action": "HOLD",
                    "quantity": 0,
                    "price": current_price,
                    "total_cost": 0.0,
                    "reason": reason,
                    "realized_pnl": None,
                    "final_recommendation_id": None,
                }
                trades.append(trade)
                print(f"HOLD {pos['quantity']} {ticker} @ ${current_price:.2f}")

    # 4. Persist all trades
    if trades:
        persistence.set("trades", trades)
        print(f"Persisted {len(trades)} trades")

    # 5. Update positions in DB
    # Delete all positions for this portfolio and recreate
    text_clause = text("DELETE FROM positions WHERE portfolio_id = :portfolio_id")
    persistence.write(text_clause, {"portfolio_id": portfolio_id})

    if positions_by_ticker:
        positions_to_create = []
        for pos in positions_by_ticker.values():
            positions_to_create.append({
                "portfolio_id": portfolio_id,
                "ticker": pos["ticker"],
                "quantity": pos["quantity"],
                "avg_entry_price": pos["avg_entry_price"],
                "current_price": pos["current_price"],
                "unrealized_pnl": pos["unrealized_pnl"],
            })
        persistence.set("positions", positions_to_create)
        print(f"Updated {len(positions_to_create)} positions")

    # 6. Update portfolio metrics
    positions_value = sum(pos["current_price"] * pos["quantity"] for pos in positions_by_ticker.values())
    total_value = cash_balance + positions_value

    text_clause = text(
        "UPDATE portfolios SET cash_balance = :cash_balance, "
        "total_value = :total_value, last_update_run_id = :run_id, updated_at = :updated_at "
        "WHERE id = :portfolio_id"
    )
    persistence.write(text_clause, {
        "portfolio_id": portfolio_id,
        "cash_balance": cash_balance,
        "total_value": total_value,
        "run_id": run_id,
        "updated_at": datetime.now(timezone.utc),
    })

    print(f"Portfolio updated: Cash=${cash_balance:.2f}, Positions=${positions_value:.2f}, Total=${total_value:.2f}")

    # 7. Track S&P 500 benchmark
    yf_client = YahooFinanceClient()
    sp500_snapshot = yf_client.get_yf_snapshot("^GSPC")
    sp500_current = sp500_snapshot.price

    # 8. Create performance snapshot
    text_clause = text("SELECT * FROM portfolios WHERE id = :portfolio_id")
    portfolio = persistence.query(text_clause, {"portfolio_id": portfolio_id})[0]

    initial_capital = portfolio.initial_capital
    total_pnl = total_value - initial_capital
    roi_percent = (total_pnl / initial_capital) * 100

    # Get initial S&P 500 value
    text_clause = text(
        "SELECT sp500_initial_value FROM performance_snapshots "
        "WHERE portfolio_id = :portfolio_id "
        "ORDER BY created_at ASC LIMIT 1"
    )
    initial_sp500_rows = persistence.query(text_clause, {"portfolio_id": portfolio_id})

    if initial_sp500_rows and len(initial_sp500_rows) > 0:
        sp500_initial = initial_sp500_rows[0].sp500_initial_value
    else:
        sp500_initial = sp500_current

    sp500_return_percent = ((sp500_current - sp500_initial) / sp500_initial) * 100 if sp500_initial > 0 else 0.0
    alpha = roi_percent - sp500_return_percent

    snapshot_row = {
        "portfolio_id": portfolio_id,
        "run_id": run_id,
        "total_value": total_value,
        "cash_balance": cash_balance,
        "total_pnl": total_pnl,
        "roi_percent": roi_percent,
        "sp500_initial_value": sp500_initial,
        "sp500_current_value": sp500_current,
        "sp500_cumulative_return_percent": sp500_return_percent,
        "alpha": alpha,
    }

    persistence.set("performance_snapshots", [snapshot_row])

    print(f"Performance: ROI={roi_percent:.2f}%, S&P500={sp500_return_percent:.2f}%, Alpha={alpha:.2f}%")


def s_notify_discord(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Step 3: Send trade summary and performance to Discord."""
    # Get trades
    trades = persistence.get("trades", run_id=run_id)

    # Get performance snapshot
    snapshots = persistence.get("performance_snapshots", run_id=run_id)
    snapshot = snapshots[0] if snapshots else None

    # Get portfolio
    text_clause = text("SELECT * FROM portfolios WHERE name = :name")
    portfolio_rows = persistence.query(text_clause, {"name": DEFAULT_PORTFOLIO_NAME})
    portfolio = portfolio_rows[0] if portfolio_rows else None

    # Send to Discord
    send_trade_summary_to_discord(
        trades=trades,
        snapshot=snapshot,
        portfolio=portfolio,
        run_id=run_id
    )


def init_workflow(run_id: str, persistence: SqlAlchemyPersistence) -> Workflow:
    """Initialize the simplified weekly trade workflow."""
    weekly_trade_workflow = Workflow(
        run_id=run_id,
        persistence=persistence,
        steps=[
            Step("insert run metadata", StepFns(functions=[s_insert_run_metadata])),
            Step("prepare trade inputs", StepFns(functions=[s_prepare_trade_inputs])),
            Step("trade decision and execute", StepFns(functions=[s_trade_decision_and_execute])),
            Step("notify discord", StepFns(functions=[s_notify_discord])),
        ]
    )
    return weekly_trade_workflow
