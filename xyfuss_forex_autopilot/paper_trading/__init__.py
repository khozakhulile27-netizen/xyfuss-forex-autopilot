from __future__ import annotations


class Backtester:
    """Simple historical simulation engine used for development testing."""

    def run(self, trades: list[dict], starting_balance: float = 10000.0) -> dict:
        balance = starting_balance
        net_profit = 0.0
        wins = 0
        losses = 0

        for trade in trades:
            pnl = float(trade.get("pnl", 0.0))
            outcome = trade.get("outcome", "loss")
            if outcome == "win":
                wins += 1
            else:
                losses += 1
            balance += pnl
            net_profit += pnl

        win_rate = (wins / len(trades)) * 100.0 if trades else 0.0
        return {
            "starting_balance": starting_balance,
            "final_balance": round(balance, 2),
            "net_profit": round(net_profit, 2),
            "wins": wins,
            "losses": losses,
            "win_rate": round(win_rate, 2),
        }
