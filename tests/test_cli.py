from __future__ import annotations

import csv
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


def write_input_csv() -> tuple[Path, Path]:
    directory = Path(tempfile.mkdtemp())
    input_path = directory / "input.csv"
    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "parent", "label", "order"])
        writer.writerow(["root", "", "Root", "0"])
        writer.writerow(["child", "root", "Child", "0"])
    return directory, input_path


def write_input_newick() -> tuple[Path, Path]:
    directory = Path(tempfile.mkdtemp())
    input_path = directory / "input.nwk"
    input_path.write_text("(child)root;", encoding="utf-8")
    return directory, input_path


class CliTests(unittest.TestCase):
    def test_cli_build_command(self) -> None:
        directory, input_path = write_input_csv()
        output_csv = directory / "out.csv"
        output_svg = directory / "out.svg"
        env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}

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
            env=env,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertTrue(output_csv.exists())
        self.assertTrue(output_svg.exists())
        self.assertIn("Generated", completed.stdout)

    def test_cli_requires_an_output(self) -> None:
        _, input_path = write_input_csv()
        env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}

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
            env=env,
        )

        self.assertNotEqual(completed.returncode, 0)

    def test_cli_accepts_newick_input_format_flag(self) -> None:
        _, input_path = write_input_newick()
        env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}

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
            env=env,
        )

        self.assertNotEqual(completed.returncode, 0)
        self.assertIn("BioPython", completed.stderr)

    def test_cli_accepts_font_size_flag(self) -> None:
        directory, input_path = write_input_csv()
        output_svg = directory / "out.svg"
        env = {"PYTHONPATH": str(Path(__file__).resolve().parents[1] / "src")}

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
            env=env,
        )

        self.assertEqual(completed.returncode, 0, completed.stderr)
        self.assertIn('font-size="20.000"', output_svg.read_text(encoding="utf-8"))
