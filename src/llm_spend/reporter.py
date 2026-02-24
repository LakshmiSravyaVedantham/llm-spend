"""
Rich-powered report formatting for llm-spend.
"""

from __future__ import annotations

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()


def _cost_str(cost: float) -> str:
    return f"${cost:.4f}"


def report_by_file(data: list[dict[str, Any]]) -> None:
    """Print a Rich table: File | Calls | Input Tokens | Output Tokens | Cost."""
    table = Table(title="Cost by File", show_lines=False, header_style="bold cyan")
    table.add_column("File", style="white", no_wrap=False)
    table.add_column("Calls", justify="right", style="yellow")
    table.add_column("Input Tokens", justify="right", style="blue")
    table.add_column("Output Tokens", justify="right", style="blue")
    table.add_column("Cost (USD)", justify="right", style="green")

    for row in data:
        table.add_row(
            str(row.get("file", "(unknown)")),
            str(row.get("calls", 0)),
            f"{row.get('input_tokens', 0):,}",
            f"{row.get('output_tokens', 0):,}",
            _cost_str(row.get("cost_usd", 0.0)),
        )

    console.print(table)


def report_by_function(data: list[dict[str, Any]]) -> None:
    """Print a Rich table: Function | File | Calls | Input Tokens | Output Tokens | Cost."""
    table = Table(title="Cost by Function", show_lines=False, header_style="bold cyan")
    table.add_column("Function", style="white")
    table.add_column("File", style="dim white", no_wrap=False)
    table.add_column("Calls", justify="right", style="yellow")
    table.add_column("Input Tokens", justify="right", style="blue")
    table.add_column("Output Tokens", justify="right", style="blue")
    table.add_column("Cost (USD)", justify="right", style="green")

    for row in data:
        table.add_row(
            str(row.get("function", "(unknown)")),
            str(row.get("file", "(unknown)")),
            str(row.get("calls", 0)),
            f"{row.get('input_tokens', 0):,}",
            f"{row.get('output_tokens', 0):,}",
            _cost_str(row.get("cost_usd", 0.0)),
        )

    console.print(table)


def report_by_model(data: list[dict[str, Any]]) -> None:
    """Print a Rich table: Model | Provider | Calls | Input Tokens | Output Tokens | Cost."""
    table = Table(title="Cost by Model", show_lines=False, header_style="bold cyan")
    table.add_column("Model", style="white")
    table.add_column("Provider", style="magenta")
    table.add_column("Calls", justify="right", style="yellow")
    table.add_column("Input Tokens", justify="right", style="blue")
    table.add_column("Output Tokens", justify="right", style="blue")
    table.add_column("Cost (USD)", justify="right", style="green")

    for row in data:
        table.add_row(
            str(row.get("model", "(unknown)")),
            str(row.get("provider", "(unknown)")),
            str(row.get("calls", 0)),
            f"{row.get('input_tokens', 0):,}",
            f"{row.get('output_tokens', 0):,}",
            _cost_str(row.get("cost_usd", 0.0)),
        )

    console.print(table)


def report_by_label(data: list[dict[str, Any]]) -> None:
    """Print a Rich table: Label | Calls | Input Tokens | Output Tokens | Cost."""
    table = Table(title="Cost by Label", show_lines=False, header_style="bold cyan")
    table.add_column("Label", style="white")
    table.add_column("Calls", justify="right", style="yellow")
    table.add_column("Input Tokens", justify="right", style="blue")
    table.add_column("Output Tokens", justify="right", style="blue")
    table.add_column("Cost (USD)", justify="right", style="green")

    for row in data:
        table.add_row(
            str(row.get("label", "(unlabeled)")),
            str(row.get("calls", 0)),
            f"{row.get('input_tokens', 0):,}",
            f"{row.get('output_tokens', 0):,}",
            _cost_str(row.get("cost_usd", 0.0)),
        )

    console.print(table)


def report_summary(
    total: dict[str, Any],
    top_file: str,
    top_model: str,
    days: int = 30,
) -> None:
    """Print a summary panel."""
    cost = total.get("total_cost", 0.0)
    calls = total.get("total_calls", 0)
    inp = total.get("total_input", 0)
    out = total.get("total_output", 0)

    lines = [
        f"[bold green]Total Spend:[/bold green]   [yellow]${cost:.4f}[/yellow]",
        f"[bold]Total Calls:[/bold]   {calls:,}",
        f"[bold]Input Tokens:[/bold]  {inp:,}",
        f"[bold]Output Tokens:[/bold] {out:,}",
        "",
        f"[bold]Top File:[/bold]      [cyan]{top_file}[/cyan]",
        f"[bold]Top Model:[/bold]     [magenta]{top_model}[/magenta]",
    ]

    panel = Panel(
        "\n".join(lines),
        title=f"LLM Spend Summary (last {days} days)",
        border_style="green",
        expand=False,
    )
    console.print(panel)


def list_models(pricing: dict[str, dict[str, float]]) -> None:
    """Print a Rich table of all known models and their pricing."""
    from llm_spend.pricing import detect_provider

    table = Table(
        title="Supported Models & Pricing (per 1M tokens)",
        show_lines=False,
        header_style="bold cyan",
    )
    table.add_column("Model", style="white")
    table.add_column("Provider", style="magenta")
    table.add_column("Input $/1M", justify="right", style="blue")
    table.add_column("Output $/1M", justify="right", style="green")

    for model, prices in sorted(pricing.items()):
        table.add_row(
            model,
            detect_provider(model),
            f"${prices['input']:.4f}",
            f"${prices['output']:.4f}",
        )

    console.print(table)
