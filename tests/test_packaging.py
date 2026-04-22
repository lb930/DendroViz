from __future__ import annotations

import importlib
import unittest
from unittest import mock

from tests.helpers import write_csv_file


class PackagingTests(unittest.TestCase):
    def test_import_smoke(self) -> None:
        """Import the package and verify its top-level API is present."""
        module = importlib.import_module("dendroviz")
        self.assertEqual(module.__version__, "0.1.0")
        self.assertTrue(hasattr(module, "DendrogramGenerator"))

    def test_default_install_does_not_require_biopython(self) -> None:
        """Confirm CSV-only usage works without the optional Newick dependency."""
        from dendroviz import DendrogramGenerator

        _, path = write_csv_file(
            [
                ["root", "", "Root", "0"],
                ["child", "root", "Child", "0"],
            ],
            headers=["id", "parent", "label", "order"],
        )

        fake_import = __import__

        def raising_import(
            name: str,
            globals: object = None,
            locals: object = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> object:
            """Pretend that BioPython is unavailable."""
            if name == "Bio":
                raise ImportError("No module named Bio")
            return fake_import(name, globals, locals, fromlist, level)

        with mock.patch("builtins.__import__", side_effect=raising_import):
            generator = DendrogramGenerator()
            tree = generator.load_tree_csv(path)

        self.assertEqual(tree.root.node_id, "root")
        self.assertEqual([node.node_id for node in tree.nodes], ["root", "child"])
