"""Migration script to rename entry files from timestamp_uuid.json to uuid.json.

This script migrates existing journal entries from the old filename format
(YYYYMMDD_HHMMSS_uuid.json) to the new privacy-preserving format (uuid.json).
"""

import logging
import re
from pathlib import Path

from companion.config import load_config

logger = logging.getLogger(__name__)

# Pattern to match old filename format: YYYYMMDD_HHMMSS_uuid.json
OLD_FILENAME_PATTERN = re.compile(r"^\d{8}_\d{6}_([a-f0-9-]{36})\.json$")


def migrate_entry_filenames(entries_dir: Path, dry_run: bool = False) -> tuple[int, int]:
    """Migrate entry filenames from timestamp_uuid.json to uuid.json format.

    Args:
        entries_dir: Directory containing entry files
        dry_run: If True, only report what would be done without making changes

    Returns:
        Tuple of (files_migrated, files_skipped)

    Example:
        >>> from pathlib import Path
        >>> entries = Path(".companion/data/entries")
        >>> migrated, skipped = migrate_entry_filenames(entries, dry_run=True)
        >>> print(f"Would migrate {migrated} files, skip {skipped}")
    """
    if not entries_dir.exists():
        logger.warning("Entries directory does not exist: %s", entries_dir)
        return 0, 0

    migrated = 0
    skipped = 0

    for file_path in entries_dir.glob("*.json"):
        match = OLD_FILENAME_PATTERN.match(file_path.name)

        if not match:
            # Already in new format or different naming scheme
            logger.debug("Skipping file (not old format): %s", file_path.name)
            skipped += 1
            continue

        # Extract UUID from filename
        uuid = match.group(1)
        new_filename = f"{uuid}.json"
        new_path = entries_dir / new_filename

        if new_path.exists():
            logger.warning("Target file already exists, skipping: %s", new_filename)
            skipped += 1
            continue

        if dry_run:
            logger.info("[DRY RUN] Would rename: %s -> %s", file_path.name, new_filename)
        else:
            try:
                file_path.rename(new_path)
                logger.info("Migrated: %s -> %s", file_path.name, new_filename)
            except Exception as e:
                logger.error("Failed to migrate %s: %s", file_path.name, e)
                skipped += 1
                continue

        migrated += 1

    return migrated, skipped


def main(dry_run: bool = False) -> None:
    """Run migration on configured data directory.

    Args:
        dry_run: If True, only report what would be done
    """
    config = load_config()
    entries_dir = config.data_directory / "entries"

    logger.info("Starting filename migration (dry_run=%s)", dry_run)
    logger.info("Entries directory: %s", entries_dir)

    migrated, skipped = migrate_entry_filenames(entries_dir, dry_run=dry_run)

    if dry_run:
        logger.info("DRY RUN complete: would migrate %d files, skip %d files", migrated, skipped)
    else:
        logger.info("Migration complete: migrated %d files, skipped %d files", migrated, skipped)


if __name__ == "__main__":
    import sys

    # Simple CLI
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("Running in DRY RUN mode (no actual changes)")
    else:
        print("WARNING: This will rename entry files. Ctrl+C to cancel, Enter to continue...")
        input()

    main(dry_run=dry_run)
