"""Date parsing shared by the scripts that take ``--date``."""

import argparse
from datetime import date


def parse_date(value):
    """argparse type for a pull date: exactly ``YYYY-MM-DD``, returned as a ``date``."""
    # Stricter than date.fromisoformat, which also accepts e.g. "20261012".
    try:
        d = date.fromisoformat(value)
    except ValueError:
        d = None
    if d is None or d.isoformat() != value:
        raise argparse.ArgumentTypeError(f"not a YYYY-MM-DD date: {value!r}")
    return d
