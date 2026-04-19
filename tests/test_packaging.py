from __future__ import annotations

import importlib
import unittest


class PackagingTests(unittest.TestCase):
    def test_import_smoke(self) -> None:
        """Import the package and verify its top-level API is present."""
        module = importlib.import_module("dendroviz")
        self.assertEqual(module.__version__, "0.1.0")
        self.assertTrue(hasattr(module, "DendrogramGenerator"))
