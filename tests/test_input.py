from __future__ import annotations

import csv
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dendroviz.api import DendrogramGenerator
from dendroviz.errors import ValidationError


def write_csv(rows: list[dict[str, str]], headers: list[str] | None = None) -> Path:
    directory = Path(tempfile.mkdtemp())
    path = directory / "tree.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=headers or ["id", "parent", "label", "order"])
        writer.writeheader()
        writer.writerows(rows)
    return path


def write_newick(contents: str) -> Path:
    directory = Path(tempfile.mkdtemp())
    path = directory / "tree.nwk"
    path.write_text(contents, encoding="utf-8")
    return path


class FakeClade:
    def __init__(self, name: str | None = None, clades: list["FakeClade"] | None = None) -> None:
        self.name = name
        self.clades = clades or []


class FakeTree:
    def __init__(self, root: FakeClade) -> None:
        self.root = root


class LoadTreeCsvTests(unittest.TestCase):
    def test_loads_valid_tree(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "0"},
                {"id": "child_b", "parent": "root", "label": "Child B", "order": "1"},
                {"id": "child_a", "parent": "root", "label": "Child A", "order": "0"},
            ]
        )

        tree = generator.load_tree_csv(path)

        self.assertEqual(tree.root.node_id, "root")
        self.assertEqual([node.node_id for node in tree.nodes], ["root", "child_a", "child_b"])

    def test_rejects_wrong_headers(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [{"name": "root"}],
            headers=["name"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_duplicate_ids(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "0"},
                {"id": "root", "parent": "", "label": "Other Root", "order": "1"},
            ]
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_missing_parents(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "0"},
                {"id": "child", "parent": "ghost", "label": "Child", "order": "0"},
            ]
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_multiple_roots(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [
                {"id": "root_a", "parent": "", "label": "Root A", "order": "0"},
                {"id": "root_b", "parent": "", "label": "Root B", "order": "1"},
            ]
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_cycle(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [
                {"id": "root", "parent": "child", "label": "Root", "order": "0"},
                {"id": "child", "parent": "root", "label": "Child", "order": "0"},
            ]
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_non_numeric_order(self) -> None:
        generator = DendrogramGenerator()
        path = write_csv(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "a"},
            ]
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_loads_newick_tree_with_soft_dependency(self) -> None:
        generator = DendrogramGenerator()
        path = write_newick("(ignored);")
        fake_tree = FakeTree(
            FakeClade(
                "Root",
                [
                    FakeClade("Child B"),
                    FakeClade("Child A"),
                ],
            )
        )
        fake_phylo = types.SimpleNamespace(read=mock.Mock(return_value=fake_tree))
        fake_bio = types.SimpleNamespace(Phylo=fake_phylo)

        with mock.patch.dict(sys.modules, {"Bio": fake_bio}):
            tree = generator.load_tree(path, input_format="newick")

        self.assertEqual(tree.root.label, "Root")
        self.assertEqual([node.label for node in tree.nodes], ["Root", "Child B", "Child A"])
        fake_phylo.read.assert_called_once_with(str(path), "newick")

    def test_newick_requires_biopython_when_requested(self) -> None:
        generator = DendrogramGenerator()
        path = write_newick("(a,b)root;")

        original_import = __import__

        def raising_import(name: str, globals: object = None, locals: object = None, fromlist: tuple[str, ...] = (), level: int = 0) -> object:
            if name == "Bio":
                raise ImportError("No module named Bio")
            return original_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=raising_import):
            with self.assertRaises(ImportError):
                generator.load_tree(path, input_format="newick")
