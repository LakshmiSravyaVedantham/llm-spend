"""Tests for llm_spend.reporter."""

from io import StringIO
from unittest.mock import patch

import pytest
from rich.console import Console

from llm_spend import reporter as reporter_module
from llm_spend.pricing import PRICING
from llm_spend.reporter import (
    list_models,
    report_by_file,
    report_by_function,
    report_by_label,
    report_by_model,
    report_summary,
)

# ---------------------------------------------------------------------------
# Sample data fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def sample_file_data():
    return [
        {
            "file": "src/summarizer.py",
            "calls": 10,
            "input_tokens": 50000,
            "output_tokens": 10000,
            "cost_usd": 0.275,
        },
        {
            "file": "src/classifier.py",
            "calls": 5,
            "input_tokens": 20000,
            "output_tokens": 5000,
            "cost_usd": 0.10,
        },
    ]


@pytest.fixture()
def sample_function_data():
    return [
        {
            "function": "summarize_article",
            "file": "src/summarizer.py",
            "calls": 10,
            "input_tokens": 50000,
            "output_tokens": 10000,
            "cost_usd": 0.275,
        },
    ]


@pytest.fixture()
def sample_model_data():
    return [
        {
            "model": "gpt-4o",
            "provider": "openai",
            "calls": 15,
            "input_tokens": 70000,
            "output_tokens": 15000,
            "cost_usd": 0.325,
        },
    ]


@pytest.fixture()
def sample_label_data():
    return [
        {
            "label": "summarize",
            "calls": 10,
            "input_tokens": 50000,
            "output_tokens": 10000,
            "cost_usd": 0.275,
        },
    ]


@pytest.fixture()
def sample_total():
    return {
        "total_cost": 0.375,
        "total_calls": 15,
        "total_input": 70000,
        "total_output": 15000,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _capture_report(fn, *args, **kwargs) -> str:
    """Run a reporter function with a wide captured console and return text output."""
    buf = StringIO()
    # Use a wide console (width=300) so Rich does not truncate cell values.
    test_console = Console(file=buf, highlight=False, markup=False, width=300)
    with patch.object(reporter_module, "console", test_console):
        fn(*args, **kwargs)
    return buf.getvalue()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestReportByFile:
    def test_renders_without_error(self, sample_file_data):
        output = _capture_report(report_by_file, sample_file_data)
        assert "src/summarizer.py" in output
        assert "src/classifier.py" in output

    def test_shows_cost(self, sample_file_data):
        output = _capture_report(report_by_file, sample_file_data)
        assert "0.2750" in output

    def test_empty_data_renders(self):
        output = _capture_report(report_by_file, [])
        assert output is not None  # should not raise


class TestReportByFunction:
    def test_renders_without_error(self, sample_function_data):
        output = _capture_report(report_by_function, sample_function_data)
        assert "summarize_article" in output

    def test_shows_file_column(self, sample_function_data):
        output = _capture_report(report_by_function, sample_function_data)
        assert "src/summarizer.py" in output


class TestReportByModel:
    def test_renders_without_error(self, sample_model_data):
        output = _capture_report(report_by_model, sample_model_data)
        assert "gpt-4o" in output

    def test_shows_provider(self, sample_model_data):
        output = _capture_report(report_by_model, sample_model_data)
        assert "openai" in output

    def test_empty_data_renders(self):
        output = _capture_report(report_by_model, [])
        assert output is not None


class TestReportByLabel:
    def test_renders_without_error(self, sample_label_data):
        output = _capture_report(report_by_label, sample_label_data)
        assert "summarize" in output


class TestReportSummary:
    def test_renders_without_error(self, sample_total):
        output = _capture_report(
            report_summary,
            sample_total,
            top_file="src/summarizer.py",
            top_model="gpt-4o",
            days=30,
        )
        assert "0.3750" in output
        assert "gpt-4o" in output

    def test_shows_top_file(self, sample_total):
        output = _capture_report(
            report_summary,
            sample_total,
            top_file="myfeature.py",
            top_model="gpt-4o",
        )
        assert "myfeature.py" in output


class TestListModels:
    def test_renders_all_known_models(self):
        output = _capture_report(list_models, PRICING)
        for model in PRICING:
            assert model in output

    def test_shows_pricing_columns(self):
        output = _capture_report(list_models, PRICING)
        # Should contain at least one price value from the table
        assert "$" in output
