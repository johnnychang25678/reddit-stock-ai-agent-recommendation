"""Daily performance tracking workflow.

This workflow runs daily (Tuesday-Friday) to:
1. Update position prices with current market data
2. Create daily performance snapshot
3. Send Discord notification with portfolio status

Skips Monday since weekly trade workflow runs on Monday.
"""

from stock_ai.yahoo_finance.yahoo_finance_client import YahooFinanceClient
from stock_ai.workflows.persistence.sql_alchemy_persistence import SqlAlchemyPersistence
from stock_ai.workflows.workflow_base import StepFn, StepFns, Step, Workflow
from stock_ai.workflows.common.utils import idempotency_check
from stock_ai.workflows.common.common_step_fns import s_insert_run_metadata
from stock_ai.notifiers.discord.trade_notifier import send_trade_summary_to_discord

from sqlalchemy import text
from datetime import datetime, timezone


# Configuration
DEFAULT_PORTFOLIO_NAME = "weekly_trade_bot"


def s_update_position_prices(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Step 1: Update all position prices with current market data.
    
    Fetches current prices for all tickers in the portfolio and updates
    positions table with latest prices and unrealized P&L.
    """
    # NOTE: we don't need idempotency check here since prices can change daily
    # and also if we run this after-hours, the prices will be the same.

    # 1. Get portfolio
    portfolio_rows = persistence.query(
        text("SELECT * FROM portfolios WHERE name = :name"),
        {"name": DEFAULT_PORTFOLIO_NAME}
    )
    
    if not portfolio_rows or len(portfolio_rows) == 0:
        print(f"Portfolio '{DEFAULT_PORTFOLIO_NAME}' not found")
        return

    portfolio_id = portfolio_rows[0].id
    
    # 2. Get all current positions
    positions_rows = persistence.query(
        text("SELECT * FROM positions WHERE portfolio_id = :portfolio_id"),
        {"portfolio_id": portfolio_id}
    )

    if not positions_rows or len(positions_rows) == 0:
        print("No positions to update")
        return

    # 3. Fetch current prices
    yf_client = YahooFinanceClient()
    tickers = [pos.ticker for pos in positions_rows]
    prices = yf_client.get_current_prices_batch(tickers)
    
    print(f"Fetched prices for {len(prices)} tickers")

    # 4. Update each position with current price
    for pos in positions_rows:
        ticker = pos.ticker
        current_price = prices.get(ticker)
        
        if not current_price or current_price != current_price:  # Check for NaN
            print(f"Warning: No valid price for {ticker}, keeping previous price")
            continue

        # Calculate unrealized P&L
        unrealized_pnl = (current_price - pos.avg_entry_price) * pos.quantity
        
        # Update position
        text_clause = text(
            "UPDATE positions SET "
            "current_price = :current_price, "
            "unrealized_pnl = :unrealized_pnl, "
            "updated_at = :updated_at "
            "WHERE id = :id"
        )
        persistence.write(text_clause, {
            "id": pos.id,
            "current_price": current_price,
            "unrealized_pnl": unrealized_pnl,
            "updated_at": datetime.now(timezone.utc),
        })

    print(f"Updated prices for {len(positions_rows)} positions")


def s_create_performance_snapshot(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Step 2: Create daily performance snapshot.
    
    Calculates current portfolio metrics and stores them in performance_snapshots table.
    """
    # 1. Get portfolio
    portfolio_rows = persistence.query(
        text("SELECT * FROM portfolios WHERE name = :name"),
        {"name": DEFAULT_PORTFOLIO_NAME}
    )
    
    if not portfolio_rows or len(portfolio_rows) == 0:
        print(f"Portfolio '{DEFAULT_PORTFOLIO_NAME}' not found")
        return

    portfolio = portfolio_rows[0]
    portfolio_id = portfolio.id
    cash_balance = portfolio.cash_balance
    initial_capital = portfolio.initial_capital

    # 2. Get all positions to calculate total value
    positions_rows = persistence.query(
        text("SELECT * FROM positions WHERE portfolio_id = :portfolio_id"),
        {"portfolio_id": portfolio_id}
    )

    # Calculate positions market value and unrealized P&L
    positions_value = 0.0
    total_unrealized_pnl = 0.0
    
    for pos in positions_rows:
        positions_value += pos.current_price * pos.quantity
        total_unrealized_pnl += pos.unrealized_pnl if pos.unrealized_pnl else 0.0

    # 3. Get realized P&L from all trades
    trades_rows = persistence.query(
        text("SELECT SUM(realized_pnl) as total_realized_pnl FROM trades WHERE portfolio_id = :portfolio_id"),
        {"portfolio_id": portfolio_id}
    )
    total_realized_pnl = trades_rows[0].total_realized_pnl if trades_rows and trades_rows[0].total_realized_pnl else 0.0

    # 4. Calculate portfolio metrics
    total_value = cash_balance + positions_value
    total_pnl = total_realized_pnl + total_unrealized_pnl
    roi_percent = (total_pnl / initial_capital) * 100 if initial_capital > 0 else 0.0

    # 5. Track S&P 500 benchmark
    yf_client = YahooFinanceClient()
    sp500_snapshot = yf_client.get_yf_snapshot("^GSPC")
    sp500_current = sp500_snapshot.price

    # Get initial S&P 500 value from first snapshot
    text_clause = text(
        "SELECT sp500_initial_value FROM performance_snapshots "
        "WHERE portfolio_id = :portfolio_id "
        "ORDER BY created_at ASC LIMIT 1"
    )
    initial_sp500_rows = persistence.query(text_clause, {"portfolio_id": portfolio_id})

    if initial_sp500_rows and len(initial_sp500_rows) > 0:
        sp500_initial = initial_sp500_rows[0].sp500_initial_value
    else:
        # First snapshot, use current S&P 500 as initial
        sp500_initial = sp500_current

    sp500_return_percent = ((sp500_current - sp500_initial) / sp500_initial) * 100 if sp500_initial > 0 else 0.0
    alpha = roi_percent - sp500_return_percent

    # 6. Create performance snapshot
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
    
    # 7. Update portfolio total_value
    text_clause = text(
        "UPDATE portfolios SET "
        "total_value = :total_value, "
        "updated_at = :updated_at "
        "WHERE id = :id"
    )
    persistence.write(text_clause, {
        "id": portfolio_id,
        "total_value": total_value,
        "updated_at": datetime.now(timezone.utc),
    })

    print(f"Created performance snapshot: Total Value=${total_value:.2f}, P&L=${total_pnl:.2f}, ROI={roi_percent:.2f}%")
    print(f"S&P 500 performance: {sp500_return_percent:.2f}%, Alpha: {alpha:.2f}%")


def s_notify_discord(persistence: SqlAlchemyPersistence, run_id: str) -> None:
    """Step 3: Send daily performance notification to Discord.
    
    Sends a summary of portfolio performance with no trades (empty list).
    """
    # Get portfolio
    portfolio_rows = persistence.query(
        text("SELECT * FROM portfolios WHERE name = :name"),
        {"name": DEFAULT_PORTFOLIO_NAME}
    )
    
    if not portfolio_rows or len(portfolio_rows) == 0:
        print(f"Portfolio '{DEFAULT_PORTFOLIO_NAME}' not found")
        return

    portfolio = portfolio_rows[0]
    portfolio_id = portfolio.id

    # Get latest performance snapshot
    snapshot_rows = persistence.query(
        text("SELECT * FROM performance_snapshots WHERE run_id = :run_id AND portfolio_id = :portfolio_id"),
        {"run_id": run_id, "portfolio_id": portfolio_id}
    )
    
    snapshot = snapshot_rows[0] if snapshot_rows and len(snapshot_rows) > 0 else None

    if not snapshot:
        print("No performance snapshot found for notification")
        return

    # Get current positions
    positions_rows = persistence.query(
        text("SELECT * FROM positions WHERE portfolio_id = :portfolio_id"),
        {"portfolio_id": portfolio_id}
    )

    send_trade_summary_to_discord(
        trades=[],  # No trades on daily update
        snapshot=snapshot,
        portfolio=portfolio,
        positions=list(positions_rows),  # Include current positions
        run_id=run_id,
        is_trade=False
    )

    print("Sent daily performance notification to Discord")


def init_workflow(run_id: str, persistence: SqlAlchemyPersistence) -> Workflow:
    """Initialize daily performance workflow.
    
    Args:
        run_id: Format should be DAILY_PERF_YYYYMMDD
        persistence: Database persistence layer
        
    Returns:
        Configured workflow instance
    """
    daily_performance_workflow = Workflow(
        run_id=run_id,
        persistence=persistence,
        steps=[
            Step("insert run metadata", StepFns(functions=[s_insert_run_metadata])),
            Step("update position prices", StepFns(functions=[s_update_position_prices])),
            Step("create performance snapshot", StepFns(functions=[s_create_performance_snapshot])),
            Step("notify discord", StepFns(functions=[s_notify_discord])),
        ]
    )
    return daily_performance_workflow
