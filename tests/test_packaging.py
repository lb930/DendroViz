from __future__ import annotations

import importlib
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))


class PackagingTests(unittest.TestCase):
    def test_import_smoke(self) -> None:
        module = importlib.import_module("dendroviz")
        self.assertEqual(module.__version__, "0.1.0")
        self.assertTrue(hasattr(module, "DendrogramGenerator"))
