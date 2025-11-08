"""Terminal dashboard for metrics display."""

import logging
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

logger = logging.getLogger(__name__)
console = Console()


def display_health_status(health_results: dict) -> None:
    """Display health check results in terminal.
    
    Args:
        health_results: Dict of component -> HealthStatus
    """
    table = Table(title="Companion Health Status")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Message")
    
    for component, status in health_results.items():
        status_style = {
            "OK": "green",
            "DEGRADED": "yellow",
            "DOWN": "red"
        }.get(status.status, "white")
        
        table.add_row(
            component,
            f"[{status_style}]{status.status}[/{status_style}]",
            status.message
        )
    
    console.print(table)


def display_metrics_dashboard(metrics_data: dict) -> None:
    """Display performance metrics dashboard.
    
    Args:
        metrics_data: Dict with metrics (latency, memory, cache, etc.)
    """
    # Create dashboard panel
    dashboard = Panel(
        "[bold cyan]Companion Performance Dashboard[/bold cyan]\n\n"
        "[yellow]Note:[/yellow] Full metrics tracking coming in future version.\n"
        "Currently showing basic operational status.",
        title="Metrics",
        border_style="blue"
    )
    console.print(dashboard)
    
    # For MVP, show simple stats if available
    if metrics_data:
        table = Table()
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        for key, value in metrics_data.items():
            table.add_row(key, str(value))
        
        console.print(table)
