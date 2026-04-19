from __future__ import annotations

import subprocess
import sys
import unittest
from pathlib import Path

from tests.helpers import write_csv_file, write_text_file


def write_input_csv() -> tuple[Path, Path]:
    """Write a small CSV input tree for CLI tests."""
    return write_csv_file(
        [
            ["root", "", "Root", "0"],
            ["child", "root", "Child", "0"],
        ],
        headers=["id", "parent", "label", "order"],
        filename="input.csv",
    )


def write_input_newick() -> tuple[Path, Path]:
    """Write a small Newick input tree for CLI tests."""
    return write_text_file("(child)root;", filename="input.nwk")


class CliTests(unittest.TestCase):
    def test_cli_build_command(self) -> None:
        """Run the build command end to end."""
        directory, input_path = write_input_csv()
        output_csv = directory / "out.csv"
        output_svg = directory / "out.svg"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dendroviz.cli",
                "build",
                str(input_path),
                "--tree-layout",
                "vertical",
                "--line-style",
                "straight",
                "--output-csv",
                str(output_csv),
                "--output-svg",
                str(output_svg),
                "--show-labels",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(output_csv.exists())
        self.assertTrue(output_svg.exists())
        self.assertIn("Generated", completed.stdout)

    def test_cli_requires_an_output(self) -> None:
        """Reject builds that do not request any output artifact."""
        _, input_path = write_input_csv()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dendroviz.cli",
                "build",
                str(input_path),
                "--tree-layout",
                "vertical",
                "--line-style",
                "straight",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(completed.returncode, 0)

    def test_cli_accepts_newick_input_format_flag(self) -> None:
        """Accept the Newick input-format flag and surface missing dependency errors."""
        _, input_path = write_input_newick()

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dendroviz.cli",
                "build",
                str(input_path),
                "--input-format",
                "newick",
                "--tree-layout",
                "vertical",
                "--line-style",
                "straight",
                "--output-csv",
                str(input_path.with_suffix(".out.csv")),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("BioPython", completed.stderr)

    def test_cli_accepts_font_size_flag(self) -> None:
        """Accept the font-size flag and apply it to SVG output."""
        directory, input_path = write_input_csv()
        output_svg = directory / "out.svg"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dendroviz.cli",
                "build",
                str(input_path),
                "--tree-layout",
                "vertical",
                "--line-style",
                "straight",
                "--output-svg",
                str(output_svg),
                "--show-labels",
                "--font-size",
                "20",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('font-size="20.000"', output_svg.read_text(encoding="utf-8"))
