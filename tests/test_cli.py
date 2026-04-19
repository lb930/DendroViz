from __future__ import annotations

import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
from pathlib import Path
from unittest import mock

from tests.helpers import write_csv_file, write_json_file, write_text_file


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

    def test_cli_emits_logging_when_requested(self) -> None:
        """Emit structured logs when the log level is raised."""
        directory, input_path = write_input_csv()
        output_csv = directory / "out.csv"

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
                "--log-level",
                "INFO",
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn("INFO:dendroviz.api:Generating tree...", completed.stderr)
        self.assertIn("INFO:dendroviz.cli:Building dendrogram", completed.stderr)
        self.assertIn("INFO:dendroviz.api:Generating tree", completed.stderr)
        self.assertIn("INFO:dendroviz.export:Writing CSV export", completed.stderr)

    def test_cli_logs_unexpected_errors(self) -> None:
        """Log unexpected failures instead of swallowing them."""
        _, input_path = write_input_csv()

        stderr = StringIO()
        stdout = StringIO()
        with mock.patch(
            "dendroviz.cli.DendrogramGenerator.generate_tree",
            side_effect=RuntimeError("boom"),
        ):
            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = __import__("dendroviz.cli", fromlist=["main"]).main(
                    [
                        "build",
                        str(input_path),
                        "--tree-layout",
                        "vertical",
                        "--line-style",
                        "straight",
                        "--output-csv",
                        str(input_path.with_suffix(".out.csv")),
                        "--log-level",
                        "INFO",
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertEqual(stdout.getvalue(), "")
        self.assertIn("Unexpected error while building dendrogram", stderr.getvalue())
        self.assertIn("RuntimeError: boom", stderr.getvalue())

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

    def test_cli_accepts_json_input_format_flag(self) -> None:
        """Accept the JSON input-format flag."""
        directory, input_path = write_json_file(
            [
                {"id": "root", "parent": None, "label": "Root", "order": 0},
                {"id": "child", "parent": "root", "label": "Child", "order": 0},
            ],
            filename="input.json",
        )
        output_svg = directory / "out.svg"

        completed = subprocess.run(
            [
                sys.executable,
                "-m",
                "dendroviz.cli",
                "build",
                str(input_path),
                "--input-format",
                "json",
                "--tree-layout",
                "vertical",
                "--line-style",
                "straight",
                "--output-svg",
                str(output_svg),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(output_svg.exists())

    def test_cli_can_write_json_output(self) -> None:
        """Write rendered JSON output from the CLI."""
        directory, input_path = write_input_csv()
        output_json = directory / "render.json"

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
                "--output-json",
                str(output_json),
            ],
            check=False,
            capture_output=True,
            text=True,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(output_json.exists())

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
