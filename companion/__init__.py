"""Companion - Privacy-preserving AI journaling companion.

A secure, scalable journaling application showcasing production-ready
AI security infrastructure.

Built for Palo Alto Networks R&D NetSec Hackathon.
"""

__version__ = "0.1.0"
__author__ = "Your Name"
__email__ = "your.email@example.com"

# Public API exports
from companion.models import (
    JournalEntry,
    Sentiment,
    Theme,
    Summary,
    AnalysisResult,
    Config,
)

__all__ = [
    "JournalEntry",
    "Sentiment",
    "Theme",
    "Summary",
    "AnalysisResult",
    "Config",
    "__version__",
]
