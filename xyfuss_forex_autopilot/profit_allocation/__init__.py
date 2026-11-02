from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any, Protocol


class WithdrawalAdapter(Protocol):
    def withdraw(self, amount: float, currency: str, reference: str) -> dict[str, Any]:
        ...


class PaperWithdrawalAdapter:
    """Simulates withdrawal outcomes; it never contacts a real broker."""

    def __init__(self, failure: bool = False):
        self.failure = failure

    def withdraw(self, amount: float, currency: str, reference: str) -> dict[str, Any]:
        if self.failure:
            return {"status": "failed", "reference": reference, "reason": "Simulated broker failure."}
        return {"status": "success", "reference": reference, "amount": amount, "currency": currency}


class UnsupportedWithdrawalAdapter:
    def withdraw(self, amount: float, currency: str, reference: str) -> dict[str, Any]:
        return {"status": "unsupported", "reference": reference, "reason": "Automatic withdrawals are unsupported."}


class ProfitAllocationManager:
    """Allocate verified closed-trade net profit to capital and personal withdrawal."""

    threshold = 3000.0
    personal_amount = 1500.0
    capital_amount = 1500.0

    def __init__(
        self,
        ledger_path: str | Path = "data/profit_allocation.jsonl",
        withdrawal_adapter: WithdrawalAdapter | None = None,
        currency: str = "ZAR",
    ):
        self.ledger_path = Path(ledger_path)
        self.ledger_path.parent.mkdir(parents=True, exist_ok=True)
        self.withdrawal_adapter = withdrawal_adapter or UnsupportedWithdrawalAdapter()
        self.currency = currency
        self._lock = Lock()
        self._state: dict[str, Any] = {
            "processed_profit_ids": [],
            "processed_withdrawal_references": [],
            "realized_net_profit": 0.0,
            "progress": 0.0,
            "withdrawals": 0.0,
            "trading_capital": 0.0,
            "allocations": [],
        }
        self._load_state()

    def _append_record(self, record: dict[str, Any]) -> None:
        record["recorded_at"] = datetime.now(timezone.utc).isoformat()
        line = json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n"
        with self.ledger_path.open("a", encoding="utf-8") as handle:
            handle.write(line)
            handle.flush()
            os.fsync(handle.fileno())

    def _load_state(self) -> None:
        if not self.ledger_path.exists():
            return
        for line in self.ledger_path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            record = json.loads(line)
            event = record.get("event")
            if event == "profit_recorded":
                self._state["processed_profit_ids"].append(record["profit_id"])
                self._state["realized_net_profit"] = float(record["cumulative_realized_net_profit"])
                self._state["progress"] = float(record["allocation_progress"])
            elif event == "allocation_completed":
                self._state["allocations"].append(record["allocation_id"])
                self._state["trading_capital"] = float(record["cumulative_trading_capital"])
                self._state["progress"] = max(0.0, float(self._state["progress"]) - self.threshold)
            elif event == "withdrawal_succeeded":
                self._state["withdrawals"] = float(record["cumulative_personal_withdrawals"])
                self._state["processed_withdrawal_references"].append(record["reference"])

    def status(self) -> dict[str, Any]:
        with self._lock:
            return {
                "threshold": self.threshold,
                "realized_net_profit": self._round(self._state["realized_net_profit"]),
                "remaining_toward_threshold": self._round(max(0.0, self.threshold - self._state["progress"])),
                "personal_withdrawals": self._round(self._state["withdrawals"]),
                "trading_capital_allocated": self._round(self._state["trading_capital"]),
                "allocation_count": len(self._state["allocations"]),
            }

    @staticmethod
    def _round(value: float) -> float:
        return round(float(value), 2)

    def record_realized_net_profit(
        self,
        profit_id: str,
        net_profit: float,
        trading_costs: float = 0.0,
        fees: float = 0.0,
        closed_trade: bool = True,
        *,
        broker_balance: float,
        available_margin: float,
        required_open_position_margin: float,
        automatic_withdrawal_enabled: bool = False,
    ) -> dict[str, Any]:
        with self._lock:
            profit_id = str(profit_id).strip()
            if not profit_id:
                raise ValueError("profit_id is required.")
            if profit_id in self._state["processed_profit_ids"]:
                return {"status": "duplicate", "profit_id": profit_id}
            if not closed_trade:
                return {"status": "rejected", "reason": "Unrealised profit is not eligible for allocation."}

            gross_or_net = float(net_profit)
            costs = max(0.0, float(trading_costs))
            fees = max(0.0, float(fees))
            verified_net_profit = gross_or_net - costs - fees
            new_total = float(self._state["realized_net_profit"]) + verified_net_profit
            progress = max(0.0, float(self._state["progress"]) + verified_net_profit)
            result: dict[str, Any] = {
                "status": "recorded",
                "profit_id": profit_id,
                "verified_net_profit": self._round(verified_net_profit),
                "cumulative_realized_net_profit": self._round(new_total),
                "allocation_progress": self._round(progress),
            }
            self._state["processed_profit_ids"].append(profit_id)
            self._state["realized_net_profit"] = self._round(new_total)
            self._state["progress"] = self._round(progress)
            record = {
                "event": "profit_recorded",
                "profit_id": profit_id,
                "verified_net_profit": result["verified_net_profit"],
                "trading_costs": costs,
                "fees": fees,
                "closed_trade": True,
                "cumulative_realized_net_profit": self._state["realized_net_profit"],
                "allocation_progress": self._state["progress"],
            }
            self._append_record(record)

            if progress >= self.threshold:
                allocation = self._allocate_threshold(
                    profit_id,
                    broker_balance=broker_balance,
                    available_margin=available_margin,
                    required_open_position_margin=required_open_position_margin,
                    automatic_withdrawal_enabled=automatic_withdrawal_enabled,
                )
                result["allocation"] = allocation
                if allocation["status"] != "deferred":
                    excess = progress - self.threshold
                    self._state["progress"] = self._round(excess)
            return result

    def _allocate_threshold(
        self,
        source_profit_id: str,
        *,
        broker_balance: float,
        available_margin: float,
        required_open_position_margin: float,
        automatic_withdrawal_enabled: bool,
    ) -> dict[str, Any]:
        if broker_balance < self.threshold:
            return self._defer(source_profit_id, "Broker balance is below the allocated amount.")
        if available_margin < required_open_position_margin + self.personal_amount + self.capital_amount:
            return self._defer(source_profit_id, "Available margin cannot safely cover withdrawal and open-position requirements.")

        allocation_id = f"allocation-{len(self._state['allocations']) + 1:08d}"
        if allocation_id in self._state["allocations"]:
            return {"status": "duplicate", "allocation_id": allocation_id}

        self._append_record({
            "event": "allocation_completed",
            "allocation_id": allocation_id,
            "source_profit_id": source_profit_id,
            "personal_amount": self.personal_amount,
            "trading_capital_amount": self.capital_amount,
            "currency": self.currency,
            "cumulative_trading_capital": self._round(self._state["trading_capital"] + self.capital_amount),
        })
        self._state["allocations"].append(allocation_id)
        self._state["trading_capital"] = self._round(self._state["trading_capital"] + self.capital_amount)

        if not automatic_withdrawal_enabled:
            self._append_record({
                "event": "withdrawal_manual_required",
                "allocation_id": allocation_id,
                "amount": self.personal_amount,
                "currency": self.currency,
                "reason": "Automatic withdrawal must be explicitly enabled and supported by the broker.",
            })
            return {"status": "allocation_completed_manual_withdrawal_required", "allocation_id": allocation_id, "manual_withdrawal_amount": self.personal_amount}

        reference = f"withdrawal-{allocation_id}"
        if reference in self._state["processed_withdrawal_references"]:
            return {"status": "duplicate", "reference": reference, "allocation_id": allocation_id}
        outcome = self.withdrawal_adapter.withdraw(self.personal_amount, self.currency, reference)
        if outcome["status"] == "success":
            self._append_record({
                "event": "withdrawal_succeeded",
                "allocation_id": allocation_id,
                "reference": reference,
                "amount": self.personal_amount,
                "currency": self.currency,
                "cumulative_personal_withdrawals": self._round(self._state["withdrawals"] + self.personal_amount),
            })
            self._state["processed_withdrawal_references"].append(reference)
            self._state["withdrawals"] = self._round(self._state["withdrawals"] + self.personal_amount)
            return {"status": "completed", "allocation_id": allocation_id, "withdrawal": outcome}

        if outcome["status"] == "unsupported":
            self._append_record({
                "event": "withdrawal_manual_required",
                "allocation_id": allocation_id,
                "reference": reference,
                "amount": self.personal_amount,
                "currency": self.currency,
                "reason": outcome.get("reason", "Automatic withdrawals are unsupported."),
            })
            return {
                "status": "allocation_completed_manual_withdrawal_required",
                "allocation_id": allocation_id,
                "withdrawal": outcome,
            }

        self._append_record({
            "event": "withdrawal_failed",
            "allocation_id": allocation_id,
            "reference": reference,
            "amount": self.personal_amount,
            "currency": self.currency,
            "reason": outcome.get("reason", "Withdrawal failed."),
        })
        return {"status": "capital_allocated_withdrawal_failed", "allocation_id": allocation_id, "withdrawal": outcome}

    def _defer(self, source_profit_id: str, reason: str) -> dict[str, Any]:
        self._append_record({"event": "allocation_deferred", "source_profit_id": source_profit_id, "reason": reason})
        return {"status": "deferred", "reason": reason}
