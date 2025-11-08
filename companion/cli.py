"""Command-line interface for Companion journaling application.

Provides intuitive CLI commands for writing, viewing, and analyzing journal entries.
Uses Rich for beautiful terminal output.
"""

import asyncio
import logging
import sys
from datetime import date, datetime, timedelta

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt

from companion import analyzer, config, journal, summarizer
from companion.models import JournalEntry
from companion.monitoring import dashboard, health
from companion.security.audit import decrypt_audit_log, verify_audit_log_integrity
from companion.security.passphrase import (
    PassphraseStrength,
    check_passphrase_strength,
    is_passphrase_acceptable,
)

logger = logging.getLogger(__name__)
console = Console()


def _display_greeting() -> None:
    """Display time-appropriate greeting."""
    hour = datetime.now().hour

    if hour < 12:
        greeting = "Good morning! ☀️"
    elif hour < 18:
        greeting = "Good afternoon! 🌤️"
    else:
        greeting = "Good evening! 🌙"

    console.print(f"\n{greeting}\n", style="bold cyan")


def _first_run_wizard() -> None:
    """Run first-time setup wizard if needed."""
    cfg = config.load_config()

    if cfg.first_run_complete:
        return

    console.print(Panel.fit(
        "[bold cyan]Welcome to Companion! 👋[/bold cyan]\n\n"
        "I'm your private journaling companion.\n"
        "Let's get you set up (this takes about 5 seconds).",
        border_style="cyan"
    ))

    console.print("\n📁 Creating your journal space...", style="dim")
    config.initialize_directories()

    console.print("✅ All set! Your journal is ready.\n", style="bold green")

    # Passphrase setup (informational only for MVP - actual encryption setup happens on first write)
    console.print("[bold cyan]🔒 Passphrase Security[/bold cyan]")
    console.print("\nYour journal entries will be encrypted. When you write your first entry,")
    console.print("you'll create a strong passphrase. Here's what makes a strong passphrase:\n")
    console.print("  • [green]Minimum 12 characters[/green] (16+ recommended)")
    console.print("  • [green]Use varied characters[/green] (letters, numbers, symbols)")
    console.print("  • [green]Avoid common passwords[/green] (we check against breach databases)")
    console.print("  • [green]Make it memorable[/green] (e.g., 'my-secure-journal-2025!')\n")

    # Mark first run complete
    cfg.first_run_complete = True
    config.save_config(cfg)

    console.print("[dim]Press Enter to continue...[/dim]")
    input()


def _format_entry_summary(entry: JournalEntry) -> str:
    """Format entry for list display.

    Args:
        entry: Journal entry to format

    Returns:
        Formatted string with timestamp, preview, and metadata
    """
    timestamp_str = entry.timestamp.strftime("%Y-%m-%d %H:%M")

    # Get first line as preview (up to 50 chars)
    content_preview = entry.content.split('\n')[0][:50]
    if len(entry.content) > 50:
        content_preview += "..."

    # Sentiment indicator
    sentiment_emoji = {
        "positive": "😊",
        "neutral": "😐",
        "negative": "😔"
    }
    sentiment_icon = sentiment_emoji.get(
        entry.sentiment.label if entry.sentiment else "neutral",
        "💭"
    )

    # Theme list
    themes_str = ", ".join(entry.themes[:3]) if entry.themes else "No themes"

    return (
        f"[cyan]{timestamp_str}[/cyan]  {sentiment_icon}  {content_preview}\n"
        f"[dim]    Themes: {themes_str} • {entry.word_count} words[/dim]"
    )


@click.group(invoke_without_command=True)
@click.pass_context
def main(ctx: click.Context) -> None:
    """Companion - Your empathetic journaling companion.

    Run without commands to start writing a new entry.
    """
    # Run first-time setup if needed
    _first_run_wizard()

    # If no subcommand, default to write
    if ctx.invoked_subcommand is None:
        ctx.invoke(write)


@main.command()
def write() -> None:
    """Write a new journal entry.

    Opens an interactive session for writing. Entry will be automatically
    analyzed for sentiment and themes when saved.
    """
    _display_greeting()

    console.print("What's on your mind today?\n", style="dim")
    console.print("[dim](Type your entry below. Press Ctrl+D when done, Ctrl+C to cancel)[/dim]\n")

    # Get multi-line input
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        # User pressed Ctrl+D to finish
        pass
    except KeyboardInterrupt:
        # User pressed Ctrl+C to cancel
        console.print("\n\n[yellow]Entry cancelled.[/yellow]")
        sys.exit(0)

    content = '\n'.join(lines).strip()

    if not content:
        console.print("\n[yellow]Empty entry not saved.[/yellow]")
        return

    # Create entry
    word_count = len(content.split())
    entry = JournalEntry(
        content=content,
        word_count=word_count,
        duration_seconds=0,  # Not tracking duration in MVP
    )

    # Save entry
    with console.status("[cyan]Saving entry..."):
        journal.save_entry(entry)

    console.print(f"\n✓ Entry saved ({word_count} words)", style="green")

    # Analyze in background (async)
    console.print("\n[dim]Analyzing...[/dim]")

    try:
        # Run async analysis
        async def analyze_entry() -> tuple[JournalEntry, str]:
            sentiment = await analyzer.analyze_sentiment(entry.content)
            themes = await analyzer.extract_themes(entry.content)

            # Update entry with analysis
            entry.sentiment = sentiment
            entry.themes = [theme.name for theme in themes[:5]]
            journal.save_entry(entry)

            # Format themes
            themes_str = ", ".join(entry.themes) if entry.themes else "None detected"
            return entry, themes_str

        analyzed_entry, themes_str = asyncio.run(analyze_entry())

        # Display analysis
        console.print(f"\nSentiment: [cyan]{analyzed_entry.sentiment.label.title()}[/cyan]", style="dim")  # type: ignore
        console.print(f"Themes: [cyan]{themes_str}[/cyan]\n", style="dim")

    except Exception as e:
        logger.error("Analysis failed: %s", e)
        console.print("\n[yellow]Note: Analysis could not be completed[/yellow]", style="dim")

    console.print("See you next time! 💚\n", style="bold green")


@main.command()
@click.option('--limit', default=10, help='Number of entries to show')
@click.option('--date', type=str, help='Specific date (YYYY-MM-DD)')
def list_entries(limit: int, date: str | None) -> None:
    """List recent journal entries.

    Shows recent entries with timestamps, previews, and metadata.
    """
    try:
        if date:
            # Parse date and get entries for that day
            target_date = datetime.strptime(date, "%Y-%m-%d").date()
            entries = journal.get_entries_by_date_range(target_date, target_date)
        else:
            # Get recent entries
            entries = journal.get_recent_entries(limit=limit)

        if not entries:
            console.print("\n[yellow]No entries found.[/yellow]\n")
            return

        # Display header
        console.print("\n[bold cyan]Your Journal Entries[/bold cyan]")
        console.print("─" * 60, style="dim")
        console.print()

        # Display each entry
        for entry in entries:
            console.print(_format_entry_summary(entry))
            console.print()

        # Display footer
        console.print("─" * 60, style="dim")
        console.print(f"[dim]Showing {len(entries)} entries[/dim]\n")

    except ValueError as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to list entries: %s", e)
        console.print(f"\n[red]Error loading entries: {e}[/red]\n")
        sys.exit(1)


@main.command()
@click.argument('entry_id')
def show(entry_id: str) -> None:
    """Show a specific journal entry.

    ENTRY_ID: Entry identifier (timestamp or UUID)
    """
    try:
        entry = journal.get_entry(entry_id)

        # Format timestamp
        timestamp_str = entry.timestamp.strftime("%B %d, %Y at %I:%M %p")

        # Display entry
        console.print()
        console.print(f"[bold cyan]Entry from {timestamp_str}[/bold cyan]")
        console.print("─" * 60, style="dim")
        console.print()
        console.print(entry.content)
        console.print()
        console.print("─" * 60, style="dim")

        # Display metadata
        if entry.sentiment:
            console.print(f"Sentiment: [cyan]{entry.sentiment.label.title()}[/cyan]", style="dim")

        if entry.themes:
            themes_str = ", ".join(entry.themes)
            console.print(f"Themes: [cyan]{themes_str}[/cyan]", style="dim")

        console.print(f"Word count: [cyan]{entry.word_count}[/cyan]", style="dim")
        console.print()

    except FileNotFoundError:
        console.print(f"\n[red]Entry not found: {entry_id}[/red]\n")
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to show entry: %s", e)
        console.print(f"\n[red]Error loading entry: {e}[/red]\n")
        sys.exit(1)


@main.command()
@click.option('--period', type=click.Choice(['week', 'month']), default='week', help='Summary period')
def summary(period: str) -> None:
    """Generate summary of journal entries.

    Creates an AI-powered summary with themes, patterns, and insights.
    """
    try:
        # Calculate date range
        end_date = date.today()
        if period == 'week':
            start_date = end_date - timedelta(days=7)
        else:  # month
            start_date = end_date - timedelta(days=30)

        # Get entries
        console.print(f"\n[cyan]Loading {period} entries...[/cyan]")
        entries = journal.get_entries_by_date_range(start_date, end_date)

        if not entries:
            console.print(f"\n[yellow]No entries found for the past {period}.[/yellow]\n")
            return

        console.print(f"[dim]Found {len(entries)} entries[/dim]\n")

        # Generate summary
        with console.status(f"[cyan]Generating {period} summary..."):
            summary_obj = asyncio.run(
                summarizer.generate_summary(entries, period)  # type: ignore
            )

        # Display summary
        console.print()
        console.print(Panel.fit(
            f"[bold cyan]{period.title()} Summary[/bold cyan]\n"
            f"[dim]{summary_obj.start_date} to {summary_obj.end_date}[/dim]",
            border_style="cyan"
        ))
        console.print()

        # Stats
        console.print(f"[bold]📊 This {period}:[/bold] {summary_obj.entry_count} entries\n")

        # Dominant themes
        if summary_obj.dominant_themes:
            console.print("[bold]Dominant Themes:[/bold]")
            for theme in summary_obj.dominant_themes:
                console.print(f"  • {theme}")
            console.print()

        # Emotional trend
        if summary_obj.emotional_trend:
            console.print("[bold]Emotional Journey:[/bold]")
            console.print(f"  {summary_obj.emotional_trend}\n")

        # Insights
        if summary_obj.insights:
            console.print("[bold]Key Insights:[/bold]")
            for insight in summary_obj.insights:
                console.print(f"  • {insight}")
            console.print()

    except ValueError as e:
        console.print(f"\n[red]Error: {e}[/red]\n")
        sys.exit(1)
    except Exception as e:
        logger.error("Failed to generate summary: %s", e)
        console.print(f"\n[red]Error generating summary: {e}[/red]\n")
        sys.exit(1)


@main.command()
def health_check() -> None:
    """Show system health status.

    Displays health checks for AI model, storage, and system resources.
    """
    try:
        console.print("\n[bold cyan]Companion Health Check[/bold cyan]")
        console.print("─" * 60, style="dim")
        console.print()

        # Run health checks
        cfg = config.load_config()
        data_dir = cfg.data_directory

        checks = [
            health.check_model_loaded(),
            health.check_storage_accessible(data_dir),
            health.check_disk_space(data_dir),
            health.check_memory_available(),
        ]

        # Display results
        all_ok = True
        for check in checks:
            if check.status == "OK":
                icon = "✅"
                style = "green"
            elif check.status == "DEGRADED":
                icon = "⚠️"
                style = "yellow"
                all_ok = False
            else:  # DOWN
                icon = "❌"
                style = "red"
                all_ok = False

            console.print(f"{icon} [{style}]{check.component.title()}:[/{style}] {check.message}")

        console.print()
        console.print("─" * 60, style="dim")

        if all_ok:
            console.print("\n[bold green]Overall Status: ✅ HEALTHY[/bold green]\n")
        else:
            console.print("\n[bold yellow]Overall Status: ⚠️ DEGRADED[/bold yellow]\n")

    except Exception as e:
        logger.error("Health check failed: %s", e)
        console.print(f"\n[red]Error running health check: {e}[/red]\n")
        sys.exit(1)


@main.command()
def metrics() -> None:
    """Show performance metrics dashboard.

    Displays real-time metrics including latency, memory usage, and cache performance.
    """
    try:
        dashboard.display_metrics_dashboard()
    except Exception as e:
        logger.error("Failed to display metrics: %s", e)
        console.print(f"\n[red]Error displaying metrics: {e}[/red]\n")
        sys.exit(1)


@main.command("rotate-keys")
def rotate_keys_cmd() -> None:
    """Rotate encryption keys for all journal entries.

    This command will:
    1. Prompt for current and new passphrases
    2. Create a backup of all encrypted entries
    3. Re-encrypt all entries with the new passphrase
    4. Update rotation metadata

    This limits exposure if your passphrase is compromised.
    """
    from datetime import timedelta

    from rich.prompt import Prompt

    from companion.security.encryption import (
        get_rotation_metadata,
        rotate_keys,
        save_rotation_metadata,
    )

    console.print("\n[yellow]⚠️  Key Rotation[/yellow]")
    console.print("This will re-encrypt all journal entries with a new passphrase.")
    console.print("This limits exposure if your passphrase is compromised.\n")

    # Get current passphrase
    old_pass = Prompt.ask("Current passphrase", password=True)

    # Get new passphrase with strength checking
    while True:
        new_pass = Prompt.ask("New passphrase", password=True)

        # Check strength
        score = check_passphrase_strength(new_pass)

        # Display strength feedback
        if score.strength == PassphraseStrength.WEAK:
            console.print(f"[yellow]⚠️  Weak passphrase (score: {score.score}/100)[/yellow]")
            for suggestion in score.feedback:
                console.print(f"  • {suggestion}")
        elif score.strength == PassphraseStrength.MEDIUM:
            console.print(f"[yellow]Medium strength (score: {score.score}/100)[/yellow]")
            for suggestion in score.feedback[:3]:  # Show top 3 suggestions
                console.print(f"  • {suggestion}")
        else:
            console.print(f"[green]✓ {score.strength.value.replace('_', ' ').title()} passphrase (score: {score.score}/100)[/green]")
            console.print(f"  Entropy: {score.entropy_bits:.1f} bits\n")

        # Check if acceptable
        acceptable, reason = is_passphrase_acceptable(new_pass)
        if not acceptable:
            console.print(f"[red]❌ Passphrase rejected: {reason}[/red]\n")
            continue

        # Warn if weak but acceptable
        if score.strength == PassphraseStrength.WEAK:
            if not click.confirm("\nThis passphrase is weak. Use it anyway?", default=False):
                console.print("[dim]Let's try a stronger passphrase...\n[/dim]")
                continue

        break

    # Confirm new passphrase
    confirm = Prompt.ask("Confirm new passphrase", password=True)

    if new_pass != confirm:
        console.print("[red]❌ Passphrases don't match. Aborted.[/red]")
        sys.exit(1)

    # Get paths
    cfg = config.load_config()
    entries_dir = cfg.data_directory / "entries"
    backup_dir = cfg.data_directory / f"backup_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}"

    if not entries_dir.exists():
        console.print("[yellow]⚠️  No entries directory found. Nothing to rotate.[/yellow]")
        sys.exit(0)

    # Show backup location
    console.print(f"\n[dim]Creating backup: {backup_dir}[/dim]")

    # Rotate
    with console.status("[bold green]Rotating keys..."):
        result = rotate_keys(old_pass, new_pass, entries_dir, backup_dir)

    # Show results
    console.print()
    if result.success:
        console.print("[green]✓ Rotation complete[/green]")
        console.print(f"  Entries rotated: {result.entries_rotated}")
        console.print(f"  Duration: {result.duration_seconds:.1f} seconds")
        console.print(f"  Backup: {backup_dir}")

        # Update rotation metadata
        now = datetime.now()
        next_due = now + timedelta(days=90)
        metadata = get_rotation_metadata(cfg.data_directory)
        total = metadata.total_rotations + 1 if metadata else 1

        from companion.models import RotationMetadata

        new_metadata = RotationMetadata(
            last_rotation=now,
            rotation_interval_days=90,
            next_rotation_due=next_due,
            total_rotations=total,
        )
        save_rotation_metadata(new_metadata, cfg.data_directory)

        console.print(f"\n[dim]Next rotation due: {next_due.strftime('%Y-%m-%d')} (90 days)[/dim]")
    else:
        console.print("[red]❌ Rotation failed[/red]")
        console.print(f"  Entries rotated: {result.entries_rotated}")
        console.print(f"  Entries failed: {result.entries_failed}")
        for error in result.errors[:5]:
            console.print(f"  - {error}")
        if len(result.errors) > 5:
            console.print(f"  ... and {len(result.errors) - 5} more errors")
        sys.exit(1)


@main.command()
@click.option('--decrypt', is_flag=True, help='Decrypt and view audit log')
@click.option('--verify', is_flag=True, help='Verify audit log integrity')
@click.option('--limit', default=20, help='Number of recent events to display')
def audit(decrypt: bool, verify: bool, limit: int) -> None:
    """View security audit log.

    Encrypted audit logs require passphrase for viewing or verification.
    """
    cfg = config.load_config()
    audit_file = cfg.data_directory / "audit.log"

    if not audit_file.exists():
        console.print("[yellow]No audit log found[/yellow]")
        return

    if verify:
        passphrase = Prompt.ask("Enter passphrase", password=True)
        console.print("\n[cyan]Verifying audit log integrity...[/cyan]")

        integrity_ok, tampered = verify_audit_log_integrity(audit_file, passphrase)

        if integrity_ok:
            console.print("[green]✓ Audit log integrity verified - no tampering detected[/green]\n")
        else:
            console.print("[red]⚠️  TAMPERING DETECTED![/red]")
            console.print("\nCompromised entries:")
            for entry in tampered:
                console.print(f"  [red]- {entry}[/red]")
            console.print()
        return

    if decrypt:
        passphrase = Prompt.ask("Enter passphrase", password=True)
        console.print("\n[cyan]Decrypting audit log...[/cyan]\n")

        events = decrypt_audit_log(audit_file, passphrase)

        if not events:
            console.print("[yellow]No audit events found or decryption failed[/yellow]")
            return

        console.print(f"[bold cyan]Security Audit Log[/bold cyan] (Last {limit} events)\n")
        console.print("─" * 80)

        # Display last N events
        for event in events[-limit:]:
            timestamp = event.get('timestamp', 'unknown')[:19]  # Strip timezone
            event_type = event.get('event_type', 'unknown').upper()

            # Format based on event type
            if event_type == 'MODEL_INFERENCE':
                duration = event.get('duration_ms', 0)
                model = event.get('model_name', 'unknown')
                console.print(f"[cyan]{timestamp}[/cyan]  {event_type:20s}  Duration: {duration:.1f}ms  Model: {model}")
            elif event_type == 'DATA_ACCESS':
                operation = event.get('operation', 'unknown')
                entry_count = event.get('entry_count', 0)
                console.print(f"[cyan]{timestamp}[/cyan]  {event_type:20s}  {operation}: {entry_count} entries")
            elif event_type == 'SECURITY_EVENT':
                subtype = event.get('subtype', 'unknown')
                severity = event.get('severity', 'info')
                severity_color = {'info': 'green', 'warning': 'yellow', 'error': 'red', 'critical': 'red bold'}.get(severity, 'white')
                console.print(f"[cyan]{timestamp}[/cyan]  {event_type:20s}  [{severity_color}]{subtype}[/{severity_color}]")
            else:
                console.print(f"[cyan]{timestamp}[/cyan]  {event_type}")

        console.print("─" * 80)
        console.print(f"\n[dim]Total events: {len(events)}[/dim]\n")
        return

    # Default: show plaintext audit log if not encrypted
    console.print("\n[yellow]Use --decrypt to view encrypted logs or --verify to check integrity[/yellow]\n")


@main.command()
def version() -> None:
    """Show Companion version information."""
    console.print("\n[bold cyan]Companion v0.1.0[/bold cyan]")
    console.print("[dim]Your empathetic journaling companion[/dim]\n")


if __name__ == '__main__':
    main()
