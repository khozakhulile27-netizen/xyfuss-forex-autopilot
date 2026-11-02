import json
from pathlib import Path

from xyfuss_forex_autopilot.profit_allocation import (
    PaperWithdrawalAdapter,
    ProfitAllocationManager,
    UnsupportedWithdrawalAdapter,
)


def allocator(tmp_path, adapter=None):
    return ProfitAllocationManager(tmp_path / "profit.jsonl", adapter or UnsupportedWithdrawalAdapter())


def allocate(manager, profit_id="profit-1", net_profit=3000.0):
    return manager.record_realized_net_profit(
        profit_id,
        net_profit,
        broker_balance=10000.0,
        available_margin=9000.0,
        required_open_position_margin=1000.0,
        automatic_withdrawal_enabled=True,
    )


def test_realized_profit_threshold_is_net_of_costs_and_fees(tmp_path):
    manager = ProfitAllocationManager(tmp_path / "profit.jsonl", PaperWithdrawalAdapter())
    result = manager.record_realized_net_profit(
        "profit-1", 3100.0, trading_costs=50.0, fees=50.0,
        broker_balance=10000.0, available_margin=9000.0, required_open_position_margin=1000.0,
        automatic_withdrawal_enabled=True,
    )
    assert result["verified_net_profit"] == 3000.0
    assert result["allocation"]["status"] == "completed"
    assert manager.status()["trading_capital_allocated"] == 1500.0


def test_unrealized_and_duplicate_profit_are_not_allocated(tmp_path):
    manager = allocator(tmp_path, PaperWithdrawalAdapter())
    unrealized = manager.record_realized_net_profit(
        "open-1", 3000.0, closed_trade=False,
        broker_balance=10000.0, available_margin=9000.0, required_open_position_margin=1000.0,
    )
    duplicate = allocate(manager)
    duplicate_again = allocate(manager)
    assert unrealized["status"] == "rejected"
    assert duplicate["allocation"]["status"] == "completed"
    assert duplicate_again["status"] == "duplicate"


def test_withdrawal_failure_is_auditable_and_capital_is_retained(tmp_path):
    manager = allocator(tmp_path, PaperWithdrawalAdapter(failure=True))
    result = allocate(manager)
    assert result["allocation"]["status"] == "capital_allocated_withdrawal_failed"
    assert manager.status()["trading_capital_allocated"] == 1500.0
    ledger = Path(tmp_path / "profit.jsonl").read_text()
    assert '"event":"withdrawal_failed"' in ledger


def test_unsupported_withdrawal_requests_manual_action(tmp_path):
    manager = allocator(tmp_path)
    result = allocate(manager)
    assert result["allocation"]["status"] == "allocation_completed_manual_withdrawal_required"
    assert manager.status()["personal_withdrawals"] == 0.0


def test_allocation_defers_without_available_margin(tmp_path):
    manager = allocator(tmp_path, PaperWithdrawalAdapter())
    result = manager.record_realized_net_profit(
        "profit-1", 3000.0,
        broker_balance=10000.0, available_margin=3000.0, required_open_position_margin=1000.0,
        automatic_withdrawal_enabled=True,
    )
    assert result["allocation"]["status"] == "deferred"


def test_ledger_survives_restart(tmp_path):
    path = tmp_path / "profit.jsonl"
    first = ProfitAllocationManager(path, PaperWithdrawalAdapter())
    allocate(first)
    restarted = ProfitAllocationManager(path, PaperWithdrawalAdapter())
    assert restarted.status()["allocation_count"] == 1
    assert restarted.status()["trading_capital_allocated"] == 1500.0
