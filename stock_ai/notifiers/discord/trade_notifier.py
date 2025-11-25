"""Discord notifier for weekly trade bot."""

from stock_ai.notifiers.discord.discord_client import DiscordClient
import time
import os


def _format_trade(trade) -> str:
    """Format a single trade for Discord display.

    Args:
        trade: Trade ORM object with attributes: ticker, action, quantity, price, reason, realized_pnl
    """
    ticker = trade.ticker
    action = trade.action
    quantity = trade.quantity
    price = trade.price
    reason = trade.reason
    realized_pnl = trade.realized_pnl

    if action == "BUY":
        emoji = "🟢"
        total = quantity * price
        line = f"{emoji} **{action}** {quantity} {ticker} @ ${price:.2f} (Total: ${total:.2f})"
    elif action == "SELL":
        emoji = "🔴"
        pnl_str = f"${realized_pnl:.2f}" if realized_pnl is not None else "N/A"
        pnl_emoji = "📈" if realized_pnl and realized_pnl > 0 else "📉"
        line = f"{emoji} **{action}** {quantity} {ticker} @ ${price:.2f} {pnl_emoji} P&L: {pnl_str}"
    elif action == "HOLD":
        emoji = "⏸️"
        line = f"{emoji} **{action}** {ticker} @ ${price:.2f}"
    else:
        emoji = "❓"
        line = f"{emoji} **{action}** {ticker}"

    if reason and action != "HOLD":  # Skip reason for HOLD to save space
        # Truncate long reasons
        if len(reason) > 150:
            reason = reason[:147] + "..."
        line += f"\n   ↳ {reason}"

    return line


def _format_performance_summary(snapshot, portfolio) -> str:
    """Format performance metrics for Discord.

    Args:
        snapshot: PerformanceSnapshot ORM object or None
        portfolio: Portfolio ORM object or None
    """
    if not snapshot or not portfolio:
        return "Performance metrics not available"

    total_value = snapshot.total_value
    total_pnl = snapshot.total_pnl
    roi_percent = snapshot.roi_percent
    sp500_return = snapshot.sp500_cumulative_return_percent
    alpha = snapshot.alpha
    cash_balance = snapshot.cash_balance
    initial_capital = portfolio.initial_capital

    # Determine emoji based on performance
    roi_emoji = "📈" if roi_percent >= 0 else "📉"
    alpha_emoji = "🎯" if alpha and alpha > 0 else "⚠️"

    lines = [
        "## 📊 Performance Summary",
        f"**Total Value:** ${total_value:.2f}",
        f"**Cash Balance:** ${cash_balance:.2f}",
        f"**Initial Capital:** ${initial_capital:.2f}",
        f"**Total P&L:** {roi_emoji} ${total_pnl:.2f}",
        f"**ROI:** {roi_emoji} {roi_percent:.2f}%",
        f"**S&P 500 Return:** {sp500_return:.2f}%",
        f"**Alpha:** {alpha_emoji} {alpha:.2f}%",
    ]

    return "\n".join(lines)


def send_trade_summary_to_discord(trades: list, snapshot, portfolio, run_id: str):
    """Send trade summary and performance metrics to Discord.

    Args:
        trades: List of Trade ORM objects
        snapshot: PerformanceSnapshot ORM object or None
        portfolio: Portfolio ORM object or None
        run_id: Workflow run identifier
    """
    webhook_urls = os.getenv("DISCORD_WEBHOOK_URL_TEST", "")
    if not webhook_urls:
        print("DISCORD_WEBHOOK_URL_TEST not set, skipping Discord notification")
        return

    webhook_urls_list = [url.strip() for url in webhook_urls.split(",") if url.strip()]

    for url in webhook_urls_list:
        discord_client = DiscordClient(url)
        date_str = time.strftime("%Y-%m-%d", time.localtime())

        # Build header
        header = f"# 🤖 Weekly Trade Bot - {date_str}"

        # Group trades by action
        buys = [t for t in trades if t.action == "BUY"]
        sells = [t for t in trades if t.action == "SELL"]
        holds = [t for t in trades if t.action == "HOLD"]

        # Format trades
        trade_sections = []

        if buys:
            buy_lines = [f"## 🟢 New Positions ({len(buys)})"]
            buy_lines.extend([_format_trade(t) for t in buys])
            trade_sections.append("\n".join(buy_lines))

        if sells:
            sell_lines = [f"## 🔴 Closed Positions ({len(sells)})"]
            sell_lines.extend([_format_trade(t) for t in sells])
            trade_sections.append("\n".join(sell_lines))

        if holds:
            hold_lines = [f"## ⏸️ Held Positions ({len(holds)})"]
            hold_lines.extend([_format_trade(t) for t in holds])
            trade_sections.append("\n".join(hold_lines))

        if not trade_sections:
            trade_sections.append("No trades executed this week.")

        # Performance summary
        performance = _format_performance_summary(snapshot, portfolio)

        # Combine all sections
        MAX_DISCORD_LENGTH = 2000

        # Try to fit everything in one message
        content = "\n\n".join([header] + trade_sections + [performance]).strip()

        if len(content) <= MAX_DISCORD_LENGTH:
            # Fits in one message
            discord_client.send_message(content)
        else:
            # Need to split across multiple messages

            # Send header + performance first
            first_message = "\n\n".join([header, performance]).strip()
            discord_client.send_message(first_message)

            # Send trade sections
            for section in trade_sections:
                if len(section) <= MAX_DISCORD_LENGTH:
                    discord_client.send_message(section)
                else:
                    # If a single section is too long, split it further
                    # This is rare but handle it gracefully
                    lines = section.split("\n")
                    current_batch = [lines[0]]  # Keep the section header
                    current_length = len(lines[0])

                    for line in lines[1:]:
                        line_length = len(line) + 1  # +1 for newline

                        if current_length + line_length > MAX_DISCORD_LENGTH:
                            # Send current batch
                            discord_client.send_message("\n".join(current_batch))
                            current_batch = [lines[0]]  # Start new batch with header
                            current_length = len(lines[0])

                        current_batch.append(line)
                        current_length += line_length

                    # Send remaining batch
                    if len(current_batch) > 1:  # More than just the header
                        discord_client.send_message("\n".join(current_batch))

        print(f"Sent trade summary to Discord webhook")
