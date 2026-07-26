"""Shared helpers for reading a GTFS feed from a directory or ZIP archive."""

from __future__ import annotations

from pathlib import Path
from zipfile import ZipFile

import pandas as pd


def read_gtfs_table(feed: str | Path, filename: str, **kwargs) -> pd.DataFrame:
    """Read a CSV table from an unpacked GTFS directory or a GTFS ZIP file."""
    feed = Path(feed)
    if feed.is_dir():
        table = feed / filename
        if not table.exists():
            raise FileNotFoundError(f"GTFS table not found: {table}")
        return pd.read_csv(table, **kwargs)

    if feed.is_file() and feed.suffix.lower() == ".zip":
        with ZipFile(feed) as archive:
            matches = [name for name in archive.namelist() if Path(name).name == filename]
            if not matches:
                raise FileNotFoundError(f"{filename} not found in {feed}")
            with archive.open(matches[0]) as table:
                return pd.read_csv(table, **kwargs)

    raise FileNotFoundError(f"GTFS feed must be a directory or ZIP file: {feed}")


def ensure_parent(path: str | Path) -> Path:
    """Create an output file's parent directory and return the path."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    return path
