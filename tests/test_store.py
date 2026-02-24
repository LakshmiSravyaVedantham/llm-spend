"""Tests for llm_spend.store."""

from pathlib import Path

import pytest

from llm_spend.store import SpendStore


@pytest.fixture()
def store(tmp_path: Path) -> SpendStore:
    """Return a SpendStore backed by a temp directory."""
    return SpendStore(db_path=tmp_path / "test_spend.db")


class TestLogCall:
    def test_log_call_stores_record(self, store: SpendStore):
        row_id = store.log_call(
            provider="openai",
            model="gpt-4o",
            label="test-label",
            file="test_file.py",
            function="test_func",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.0075,
            duration_ms=123.4,
        )
        assert row_id is not None
        assert row_id >= 1

    def test_log_call_retrievable(self, store: SpendStore):
        store.log_call(
            provider="anthropic",
            model="claude-sonnet-4",
            label="classify",
            file="classifier.py",
            function="classify_text",
            input_tokens=2000,
            output_tokens=100,
            cost_usd=0.0075,
            duration_ms=200.0,
        )
        calls = store.get_all_calls(days=1)
        assert len(calls) == 1
        assert calls[0]["model"] == "claude-sonnet-4"
        assert calls[0]["label"] == "classify"


class TestGetByFile:
    def test_aggregates_by_file(self, store: SpendStore):
        for _ in range(3):
            store.log_call(
                provider="openai",
                model="gpt-4o",
                label="x",
                file="myfile.py",
                function="fn",
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.01,
                duration_ms=50.0,
            )
        store.log_call(
            provider="openai",
            model="gpt-4o",
            label="x",
            file="other.py",
            function="fn2",
            input_tokens=500,
            output_tokens=200,
            cost_usd=0.005,
            duration_ms=30.0,
        )

        rows = store.get_by_file(days=1)
        assert len(rows) == 2

        # Top file by cost should be myfile.py (3 * 0.01 = 0.03)
        assert rows[0]["file"] == "myfile.py"
        assert rows[0]["calls"] == 3
        assert rows[0]["cost_usd"] == pytest.approx(0.03, rel=1e-6)


class TestGetTotal:
    def test_sums_correctly(self, store: SpendStore):
        for i in range(5):
            store.log_call(
                provider="openai",
                model="gpt-4o",
                label=None,
                file=None,
                function=None,
                input_tokens=1000,
                output_tokens=500,
                cost_usd=0.01,
                duration_ms=10.0,
            )
        total = store.get_total(days=1)
        assert total["total_calls"] == 5
        assert total["total_cost"] == pytest.approx(0.05, rel=1e-6)
        assert total["total_input"] == 5000
        assert total["total_output"] == 2500

    def test_empty_store_returns_zeros(self, store: SpendStore):
        total = store.get_total(days=30)
        assert total["total_calls"] == 0
        assert total["total_cost"] == 0.0


class TestClear:
    def test_clear_all(self, store: SpendStore):
        for _ in range(4):
            store.log_call(
                provider="openai",
                model="gpt-4o",
                label=None,
                file=None,
                function=None,
                input_tokens=100,
                output_tokens=50,
                cost_usd=0.001,
                duration_ms=5.0,
            )
        deleted = store.clear()
        assert deleted == 4
        total = store.get_total(days=1)
        assert total["total_calls"] == 0

    def test_clear_by_days_removes_old_records(self, store: SpendStore):
        """Records inserted now should NOT be deleted when clearing >0 days old records."""
        store.log_call(
            provider="openai",
            model="gpt-4o",
            label=None,
            file=None,
            function=None,
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            duration_ms=5.0,
        )
        # Clearing records older than 7 days should keep the just-inserted record
        deleted = store.clear(days=7)
        assert deleted == 0
        total = store.get_total(days=1)
        assert total["total_calls"] == 1


class TestExportCsv:
    def test_export_csv(self, store: SpendStore, tmp_path: Path):
        store.log_call(
            provider="openai",
            model="gpt-4o",
            label="test",
            file="f.py",
            function="g",
            input_tokens=100,
            output_tokens=50,
            cost_usd=0.001,
            duration_ms=5.0,
        )
        out = str(tmp_path / "export.csv")
        count = store.export_csv(out)
        assert count == 1
        assert Path(out).exists()
        content = Path(out).read_text()
        assert "gpt-4o" in content
