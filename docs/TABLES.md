# Database Tables

This document explains what each database table is for, based on the ORM models in `stock_ai/db/models`.

## run_metadata
Tracks workflow runs so steps can be idempotent and auditable.
- `run_id`: unique identifier for a workflow run, used as a join key across tables.
- `description`: optional notes about the run.
- `created_at`/`updated_at`: timestamps for run tracking.

## reddit_posts
Raw Reddit posts scraped from r/wallstreetbets before any filtering.
- `run_id`: the scrape run this post belongs to.
- `reddit_id`, `flair`, `title`, `selftext`, `score`, `num_comments`, `upvote_ratio`, `created`, `url`: raw post metadata.

## reddit_filtered_posts
Subset of `reddit_posts` after the post-filtering step (top post + one random from top 50% by score per flair).
- Same columns as `reddit_posts`.
- Used to limit which posts get analyzed by the agents.

## news_recommendations
BUY recommendations produced by the News agent.
- `run_id`: links to a reddit workflow run.
- `ticker`, `reason`, `confidence`, `reddit_post_url`: agent output for a given ticker.

## dd_recommendations
BUY recommendations produced by the DD (due diligence) agent.
- Same schema as `news_recommendations`.

## yolo_recommendations
BUY recommendations produced by the YOLO agent.
- Same schema as `news_recommendations`.

## final_recommendations
Top 1–3 picks selected by the Stock Picker agent after merging all agent recommendations.
- `run_id`: the reddit workflow run.
- `ticker`, `reason`, `confidence`, `reddit_post_url`: final, curated picks.
- Used as inputs to the weekly trade workflow.

## financial_snapshots
Market snapshot data (price + technicals) for tickers at a specific time.
- `run_id`: the workflow run that created the snapshot.
- `ticker`, `price`, `sma20`, `sma50`, `sma200`, `atr14`, `high_52w`, `low_52w`, `rsi14`, `asof`.
- Note: modeled but not referenced by current workflows; likely intended for the portfolio planning agent.

## portfolio_plans
Per‑ticker trade plan outputs (entry, stop, take‑profit, time horizon).
- `run_id`: the workflow run that created the plan.
- `ticker`, `entry_price`, `stop_loss`, `take_profits`, `time_horizon_days`, `risk_reward`, `rationale`.
- Note: modeled but not referenced by current workflows.

## portfolios
Simulated trading account(s).
- `name`: human‑readable portfolio name.
- `cash_balance`, `total_value`, `initial_capital`.
- `last_update_run_id`: last trade run that updated this portfolio.

## positions
Open holdings for a portfolio (one row per ticker).
- `portfolio_id`: portfolio owning the position.
- `ticker`, `quantity`, `avg_entry_price`, `current_price`, `unrealized_pnl`.
- Rows are deleted when a position is fully closed.

## trades
Historical trade log of all BUY/SELL/HOLD/DO_NOTHING decisions.
- `portfolio_id`, `run_id`, `ticker`, `action`, `quantity`, `price`, `total_cost`.
- `reason`: agent rationale.
- `realized_pnl`: populated for SELL trades.
- `final_recommendation_id`: link to the originating final recommendation if the action is BUY.

## trade_inputs
Prepared inputs to the Trade agent for a given weekly trade run.
- `run_id`: unique trade run ID.
- `has_data`: flags runs where no recommendations were found.
- `portfolio_id`, `portfolio_cash`.
- `recommendations_json`: serialized final recommendations.
- `prices_json`: current price snapshot used for the trade decision.
- `positions_json`: serialized current positions.

## performance_snapshots
Portfolio performance snapshots with S&P 500 benchmark comparison.
- `portfolio_id`, `run_id`.
- `total_value`, `cash_balance`, `total_pnl`, `roi_percent`.
- `sp500_initial_value`, `sp500_current_value`, `sp500_cumulative_return_percent`, `alpha`.
