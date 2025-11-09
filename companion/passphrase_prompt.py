"""Passphrase prompting utilities for CLI.

Handles prompting user for passphrase with session caching and
first-run passphrase setup.
"""

import logging
from pathlib import Path

from rich.console import Console
from rich.prompt import Prompt

from companion.config import load_config
from companion.security.passphrase import (
    PassphraseStrength,
    check_passphrase_strength,
    is_passphrase_acceptable,
)
from companion.session import get_session

logger = logging.getLogger(__name__)
console = Console()


def _passphrase_marker_file() -> Path:
    """Get path to passphrase setup marker file.

    Returns:
        Path to marker file indicating passphrase has been set
    """
    config = load_config()
    return config.data_directory / ".passphrase_set"


def is_passphrase_set() -> bool:
    """Check if passphrase has been configured.

    Returns:
        True if passphrase setup is complete
    """
    return _passphrase_marker_file().exists()


def mark_passphrase_set() -> None:
    """Mark passphrase as configured."""
    marker = _passphrase_marker_file()
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.touch()
    logger.debug("Marked passphrase as set")


def setup_first_passphrase() -> str:
    """Guide user through first-time passphrase setup.

    Returns:
        New passphrase

    Raises:
        KeyboardInterrupt: If user cancels
    """
    console.print("\n[bold cyan]🔒 Passphrase Setup[/bold cyan]")
    console.print("\nCreate a strong passphrase to encrypt your journal entries:")
    console.print("  • [green]Minimum 12 characters[/green] (16+ recommended)")
    console.print("  • [green]Use varied characters[/green] (letters, numbers, symbols)")
    console.print("  • [green]Make it memorable[/green] (e.g., 'my-secure-journal-2025!')")
    console.print("\n[yellow]⚠️  Important: There is NO password recovery.[/yellow]")
    console.print("[yellow]   If you forget this passphrase, your entries are LOST.[/yellow]\n")

    while True:
        passphrase = Prompt.ask("Create passphrase", password=True)

        # Check strength
        score = check_passphrase_strength(passphrase)

        # Display strength feedback
        if score.strength == PassphraseStrength.WEAK:
            console.print(f"[yellow]⚠️  Weak passphrase (score: {score.score}/100)[/yellow]")
            for suggestion in score.feedback:
                console.print(f"  • {suggestion}")
        elif score.strength == PassphraseStrength.MEDIUM:
            console.print(f"[yellow]Medium strength (score: {score.score}/100)[/yellow]")
            for suggestion in score.feedback[:3]:
                console.print(f"  • {suggestion}")
        else:
            console.print(
                f"[green]✓ {score.strength.value.replace('_', ' ').title()} "
                f"passphrase (score: {score.score}/100)[/green]"
            )
            console.print(f"  Entropy: {score.entropy_bits:.1f} bits\n")

        # Check if acceptable
        acceptable, reason = is_passphrase_acceptable(passphrase)
        if not acceptable:
            console.print(f"[red]❌ Passphrase rejected: {reason}[/red]\n")
            continue

        # Warn if weak but acceptable
        if score.strength == PassphraseStrength.WEAK:
            console.print("\n[yellow]This passphrase is weak.[/yellow]")
            retry = Prompt.ask("Use it anyway? (yes/no)", default="no")
            if retry.lower() != "yes":
                console.print("[dim]Let's try a stronger passphrase...\n[/dim]")
                continue

        break

    # Confirm passphrase
    confirm = Prompt.ask("Confirm passphrase", password=True)

    if passphrase != confirm:
        console.print("\n[red]❌ Passphrases don't match.[/red]")
        console.print("[yellow]Please start over.[/yellow]\n")
        return setup_first_passphrase()

    # Mark as set and cache in session
    mark_passphrase_set()
    session = get_session()
    session.set_passphrase(passphrase)

    console.print("\n[green]✓ Passphrase configured successfully![/green]\n")

    return passphrase


def get_passphrase(prompt_text: str = "Enter passphrase") -> str:
    """Get passphrase from user, using cache if available.

    Handles first-time setup if needed.

    Args:
        prompt_text: Custom prompt text (default: "Enter passphrase")

    Returns:
        Passphrase (from cache or user input)

    Raises:
        KeyboardInterrupt: If user cancels
    """
    session = get_session()

    # Check cache first
    if session.has_passphrase():
        passphrase = session.get_passphrase()
        if passphrase:
            logger.debug("Using cached passphrase")
            return passphrase

    # First-time setup
    if not is_passphrase_set():
        return setup_first_passphrase()

    # Prompt for passphrase
    passphrase = Prompt.ask(prompt_text, password=True)

    # Cache for session
    session.set_passphrase(passphrase)

    return passphrase
