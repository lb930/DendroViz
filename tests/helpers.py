from __future__ import annotations

import csv
import json
import tempfile
from collections.abc import Sequence
from pathlib import Path


def make_temp_dir() -> Path:
    """Create a temporary directory and return it as a path."""
    return Path(tempfile.mkdtemp())


def write_csv_file(
    rows: Sequence[Sequence[str]],
    *,
    headers: Sequence[str],
    filename: str = "tree.csv",
) -> tuple[Path, Path]:
    """Write a CSV file with positional rows and return its directory and path."""
    directory = make_temp_dir()
    path = directory / filename
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(list(headers))
        writer.writerows(rows)
    return directory, path


def write_csv_dict_file(
    rows: Sequence[dict[str, str]],
    *,
    headers: Sequence[str],
    filename: str = "tree.csv",
) -> tuple[Path, Path]:
    """Write a CSV file with mapping rows and return its directory and path."""
    directory = make_temp_dir()
    path = directory / filename
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)
    return directory, path


def write_text_file(contents: str, *, filename: str) -> tuple[Path, Path]:
    """Write a text file and return its directory and path."""
    directory = make_temp_dir()
    path = directory / filename
    path.write_text(contents, encoding="utf-8")
    return directory, path


def write_json_file(contents: object, *, filename: str = "tree.json") -> tuple[Path, Path]:
    """Write a JSON file and return its directory and path."""
    directory = make_temp_dir()
    path = directory / filename
    path.write_text(json.dumps(contents), encoding="utf-8")
    return directory, path
