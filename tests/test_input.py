from __future__ import annotations

import pathlib
import sys
import types
import unittest
from io import StringIO
from types import ModuleType
from unittest import mock

from dendroviz.api import DendrogramGenerator
from dendroviz.errors import ValidationError
from tests.helpers import write_csv_dict_file, write_json_file, write_text_file


class FakeClade:
    def __init__(self, name: str | None = None, clades: list["FakeClade"] | None = None) -> None:
        """Create a lightweight fake clade for Newick tests."""
        self.name = name
        self.clades = clades or []


class FakeTree:
    def __init__(self, root: FakeClade) -> None:
        """Create a lightweight fake tree for Newick tests."""
        self.root = root


class LoadTreeCsvTests(unittest.TestCase):
    def test_loads_valid_tree(self) -> None:
        """Load a valid CSV tree and preserve node ordering."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "0"},
                {"id": "child_b", "parent": "root", "label": "Child B", "order": "1"},
                {"id": "child_a", "parent": "root", "label": "Child A", "order": "0"},
            ],
            headers=["id", "parent", "label", "order"],
        )

        tree = generator.load_tree_csv(path)

        self.assertEqual(tree.root.node_id, "root")
        self.assertEqual([node.node_id for node in tree.nodes], ["root", "child_a", "child_b"])

    def test_rejects_wrong_headers(self) -> None:
        """Reject CSV files whose headers do not match the schema."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [{"name": "root"}],
            headers=["name"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_duplicate_ids(self) -> None:
        """Reject duplicate node ids in CSV input."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "0"},
                {"id": "root", "parent": "", "label": "Other Root", "order": "1"},
            ],
            headers=["id", "parent", "label", "order"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_missing_parents(self) -> None:
        """Reject CSV rows that reference missing parents."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "0"},
                {"id": "child", "parent": "ghost", "label": "Child", "order": "0"},
            ],
            headers=["id", "parent", "label", "order"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_multiple_roots(self) -> None:
        """Reject CSV input with more than one root row."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [
                {"id": "root_a", "parent": "", "label": "Root A", "order": "0"},
                {"id": "root_b", "parent": "", "label": "Root B", "order": "1"},
            ],
            headers=["id", "parent", "label", "order"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_cycle(self) -> None:
        """Reject CSV input that forms a cycle."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [
                {"id": "root", "parent": "child", "label": "Root", "order": "0"},
                {"id": "child", "parent": "root", "label": "Child", "order": "0"},
            ],
            headers=["id", "parent", "label", "order"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_rejects_non_numeric_order(self) -> None:
        """Reject non-numeric order values in CSV input."""
        generator = DendrogramGenerator()
        _, path = write_csv_dict_file(
            [
                {"id": "root", "parent": "", "label": "Root", "order": "a"},
            ],
            headers=["id", "parent", "label", "order"],
        )
        with self.assertRaises(ValidationError):
            generator.load_tree_csv(path)

    def test_loads_newick_tree_with_soft_dependency_from_path(self) -> None:
        """Load a Newick tree through a mocked BioPython dependency using a path."""
        generator = DendrogramGenerator()
        _, path = write_text_file("(ignored);", filename="tree.nwk")
        fake_phylo = self._create_fake_phylo()
        fake_bio = self._create_fake_bio(fake_phylo)

        with mock.patch.dict(sys.modules, {"Bio": fake_bio}):
            tree = generator.load_tree(path, input_format="newick")

        self._assert_newick_tree_valid(tree, fake_phylo, path)

    def test_loads_newick_tree_with_soft_dependency_from_stream(self) -> None:
        """Load a Newick tree through a mocked BioPython dependency using a stream."""
        generator = DendrogramGenerator()
        stream = StringIO("(ignored);")
        fake_phylo = self._create_fake_phylo()
        fake_bio = self._create_fake_bio(fake_phylo)

        with mock.patch.dict(sys.modules, {"Bio": fake_bio}):
            tree = generator.load_tree(stream, input_format="newick")

        self._assert_newick_tree_valid(tree, fake_phylo, stream)

    def test_loads_json_tree(self) -> None:
        """Load a JSON tree in the same row schema as CSV."""
        generator = DendrogramGenerator()
        _, path = write_json_file(
            [
                {"id": "root", "parent": None, "label": "Root", "order": 0},
                {"id": "child_b", "parent": "root", "label": "Child B", "order": 1},
                {"id": "child_a", "parent": "root", "label": "Child A", "order": 0},
            ]
        )

        tree = generator.load_tree(path, input_format="json")

        self.assertEqual(tree.root.node_id, "root")
        self.assertEqual([node.node_id for node in tree.nodes], ["root", "child_a", "child_b"])

    def test_loads_csv_tree_from_stream(self) -> None:
        """Load a CSV tree from an in-memory text stream."""
        generator = DendrogramGenerator()
        stream = StringIO(
            "id,parent,label,order\n"
            "root,,Root,0\n"
            "child_b,root,Child B,1\n"
            "child_a,root,Child A,0\n"
        )

        tree = generator.load_tree_csv(stream)

        self.assertEqual(tree.root.node_id, "root")
        self.assertEqual([node.node_id for node in tree.nodes], ["root", "child_a", "child_b"])

    def test_loads_json_tree_from_stream(self) -> None:
        """Load a JSON tree from an in-memory text stream."""
        generator = DendrogramGenerator()
        stream = StringIO(
            """
            [
                {"id": "root", "parent": null, "label": "Root", "order": 0},
                {"id": "child_b", "parent": "root", "label": "Child B", "order": 1},
                {"id": "child_a", "parent": "root", "label": "Child A", "order": 0}
            ]
            """
        )

        tree = generator.load_tree(stream, input_format="json")

        self.assertEqual(tree.root.node_id, "root")
        self.assertEqual([node.node_id for node in tree.nodes], ["root", "child_a", "child_b"])

    def test_newick_requires_biopython_when_requested(self) -> None:
        """Raise ImportError when Newick support is requested without BioPython."""
        generator = DendrogramGenerator()
        _, path = write_text_file("(a,b)root;", filename="tree.nwk")

        original_import = __import__

        def raising_import(
            name: str,
            globals: dict[str, object] | None = None,
            locals: dict[str, object] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> ModuleType:
            """Pretend that BioPython is unavailable."""
            if name == "Bio":
                raise ImportError("No module named Bio")
            return original_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=raising_import):
            with self.assertRaises(ImportError):
                generator.load_tree(path, input_format="newick")

    def _create_fake_phylo(self) -> types.SimpleNamespace:
        """Create a fake Bio.Phylo module."""
        fake_tree = FakeTree(
            FakeClade(
                "Root",
                [
                    FakeClade("Child B"),
                    FakeClade("Child A"),
                ],
            )
        )
        return types.SimpleNamespace(read=mock.Mock(return_value=fake_tree))

    def _create_fake_bio(self, phylo: types.SimpleNamespace) -> types.SimpleNamespace:
        """Create a fake Bio module containing Phylo."""
        return types.SimpleNamespace(Phylo=phylo)

    def _assert_newick_tree_valid(
        self,
        tree: types.SimpleNamespace,
        fake_phylo: types.SimpleNamespace,
        expected_source: str | pathlib.Path | StringIO,
    ) -> None:
        """Helper to run common assertions for Newick tree loading."""
        self.assertEqual(tree.root.label, "Root")
        self.assertEqual([node.label for node in tree.nodes], ["Root", "Child B", "Child A"])
        fake_phylo.read.assert_called_once_with(expected_source, "newick")