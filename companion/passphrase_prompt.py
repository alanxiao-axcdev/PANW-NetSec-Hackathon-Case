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
    generate_passphrase_hash,
    verify_passphrase_hash,
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

    # Generate and store passphrase hash
    from companion.security.passphrase import generate_passphrase_hash
    passphrase_hash = generate_passphrase_hash(passphrase)
    
    # Save hash to config
    cfg = load_config()
    cfg.passphrase_hash = passphrase_hash
    from companion.config import save_config
    save_config(cfg)
    
    # Mark as set and cache in session
    mark_passphrase_set()
    session = get_session()
    session.set_passphrase(passphrase)

    console.print("\n[green]✓ Passphrase configured successfully![/green]\n")

    return passphrase


def get_passphrase(prompt_text: str = "Enter passphrase") -> str:
    """Get passphrase from user, using cache if available.

    Handles first-time setup if needed and verifies passphrase on subsequent use.

    Args:
        prompt_text: Custom prompt text (default: "Enter passphrase")

    Returns:
        Passphrase (from cache or user input)

    Raises:
        KeyboardInterrupt: If user cancels
        ValueError: If max attempts exceeded
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

    # Load config to get stored hash
    cfg = load_config()
    
    # If no hash stored (legacy install), do first-time setup
    if not cfg.passphrase_hash:
        console.print("\n[yellow]⚠️  Passphrase verification not configured.[/yellow]")
        console.print("[dim]Setting up passphrase verification for security...[/dim]\n")
        return setup_first_passphrase()

    # Prompt for passphrase with verification
    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        passphrase = Prompt.ask(prompt_text, password=True)
        
        # Verify passphrase
        from companion.security.passphrase import verify_passphrase_hash
        if verify_passphrase_hash(passphrase, cfg.passphrase_hash):
            # Success - cache for session
            session.set_passphrase(passphrase)
            logger.debug("Passphrase verified successfully")
            return passphrase
        
        # Failed verification
        if attempt < max_attempts:
            console.print(f"\n[red]❌ Incorrect passphrase ({attempt}/{max_attempts} attempts)[/red]")
            console.print("[dim]Try again...[/dim]\n")
        else:
            console.print(f"\n[red]❌ Incorrect passphrase ({max_attempts}/{max_attempts} attempts)[/red]")
            console.print("[red]Maximum attempts exceeded.[/red]\n")
            raise ValueError("Maximum passphrase attempts exceeded")
    
    # Should never reach here but defensive
    raise ValueError("Passphrase verification failed")

