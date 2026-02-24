"""
CLI entry point for llm-spend.
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

import click
from rich.console import Console

from llm_spend.pricing import PRICING
from llm_spend.reporter import (
    console,
    list_models,
    report_by_file,
    report_by_function,
    report_by_label,
    report_by_model,
    report_summary,
)
from llm_spend.store import SpendStore

_store = SpendStore()
err_console = Console(stderr=True)


@click.group()
@click.version_option(package_name="llm-spend")
def main() -> None:
    """Track your AI API costs per file, function, and feature."""


# ------------------------------------------------------------------
# report
# ------------------------------------------------------------------


@main.command()
@click.option(
    "--by",
    "group_by",
    type=click.Choice(["file", "function", "model", "label"], case_sensitive=False),
    default="model",
    show_default=True,
    help="Group results by this dimension.",
)
@click.option(
    "--days",
    default=30,
    show_default=True,
    type=int,
    help="Include calls from the last N days.",
)
def report(group_by: str, days: int) -> None:
    """Show a cost breakdown report."""
    if group_by == "file":
        data = _store.get_by_file(days=days)
        report_by_file(data)
    elif group_by == "function":
        data = _store.get_by_function(days=days)
        report_by_function(data)
    elif group_by == "label":
        data = _store.get_by_label(days=days)
        report_by_label(data)
    else:
        data = _store.get_by_model(days=days)
        report_by_model(data)

    if not data:
        console.print("[dim]No records found for the selected period.[/dim]")


# ------------------------------------------------------------------
# summary
# ------------------------------------------------------------------


@main.command()
@click.option("--days", default=30, show_default=True, type=int)
def summary(days: int) -> None:
    """Show a quick total + top consumers panel."""
    total = _store.get_total(days=days)
    files = _store.get_by_file(days=days)
    models = _store.get_by_model(days=days)

    top_file = files[0]["file"] if files else "(none)"
    top_model = models[0]["model"] if models else "(none)"
    report_summary(total, top_file=top_file, top_model=top_model, days=days)


# ------------------------------------------------------------------
# clear
# ------------------------------------------------------------------


@main.command()
@click.option(
    "--days",
    default=None,
    type=int,
    help="Clear records older than N days.  Omit to clear ALL records.",
)
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
def clear(days: Optional[int], yes: bool) -> None:
    """Delete stored call logs."""
    if days is None:
        msg = "This will delete ALL call records."
    else:
        msg = f"This will delete records older than {days} days."

    if not yes:
        click.confirm(f"{msg}  Continue?", abort=True)

    deleted = _store.clear(days=days)
    console.print(f"[green]Deleted {deleted} record(s).[/green]")


# ------------------------------------------------------------------
# export
# ------------------------------------------------------------------


@main.command()
@click.option(
    "--format",
    "fmt",
    type=click.Choice(["csv", "json"], case_sensitive=False),
    default="csv",
    show_default=True,
)
@click.option("--output", "-o", default=None, help="Output file path.")
def export(fmt: str, output: Optional[str]) -> None:
    """Export call logs to CSV or JSON."""
    if output is None:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        output = f"llm_spend_{ts}.{fmt}"

    if fmt == "csv":
        count = _store.export_csv(output)
    else:
        count = _store.export_json(output)

    console.print(f"[green]Exported {count} record(s) to {output}[/green]")


# ------------------------------------------------------------------
# models
# ------------------------------------------------------------------


@main.command()
def models() -> None:
    """List all supported models with their pricing."""
    list_models(PRICING)
