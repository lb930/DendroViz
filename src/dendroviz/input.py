from __future__ import annotations

import csv
import io
import json
import logging
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Sequence

from .errors import ValidationError
from .models import InputFormat, InputNode, TreeModel, TreeNode

logger = logging.getLogger(__name__)


class TreeCsvLoader:
    REQUIRED_COLUMNS = ("id", "parent", "label", "order")

    def load_rows(self, path: str | Path, *, input_format: InputFormat = "csv") -> list[InputNode]:
        """Load raw input rows in the requested format."""
        logger.debug("Loading %s input from %s", input_format, path)
        if input_format == "csv":
            return self._load_csv_rows(path)
        if input_format == "newick":
            return self._load_newick_rows(path)
        if input_format == "json":
            return self._load_json_rows(path)
        raise ValidationError(f"Unsupported input format: {input_format}")

    def _load_csv_rows(self, path: str | Path) -> list[InputNode]:
        """Load and validate rows from a CSV file."""
        csv_path = Path(path)
        if not csv_path.exists():
            raise ValidationError(f"Input CSV does not exist: {csv_path}")

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self._validate_headers(reader.fieldnames)
            nodes = [
                self._parse_row(row, row_number) for row_number, row in enumerate(reader, start=2)
            ]

        if not nodes:
            raise ValidationError("Input CSV contains headers but no data rows.")

        self._validate_rows(nodes)
        logger.info("Loaded %d CSV rows from %s", len(nodes), csv_path)
        return nodes

    def _load_newick_rows(self, source: str | Path | io.TextIOBase) -> list[InputNode]:
        """Load and normalise rows from a Newick file or stream."""
        try:
            from Bio import Phylo
        except ImportError as exc:
            raise ImportError(
                "Newick support requires BioPython. Install it with: pip install biopython"
            ) from exc

        try:
            phylogeny = Phylo.read(source, "newick")
        except FileNotFoundError as exc:
            raise ValidationError(f"Input Newick file does not exist: {source}") from exc
        except Exception as exc:
            raise ValidationError(f"Unable to parse Newick input: {source}") from exc

        root = getattr(phylogeny, "root", None)
        if root is None:
            raise ValidationError("Newick input does not contain a root clade.")

        nodes: list[InputNode] = []
        generated_ids: set[str] = set()
        next_id = 0

        def build_node_id(label: str) -> str:
            """Build a stable node id from a clade label."""
            nonlocal next_id
            base_label = "".join(
                character if character.isalnum() else "_" for character in label.strip()
            ).strip("_")
            if base_label:
                candidate = base_label
                suffix = 2
                while candidate in generated_ids:
                    candidate = f"{base_label}_{suffix}"
                    suffix += 1
                generated_ids.add(candidate)
                return candidate

            candidate = f"node_{next_id}"
            next_id += 1
            while candidate in generated_ids:
                candidate = f"node_{next_id}"
                next_id += 1
            generated_ids.add(candidate)
            return candidate

        def visit(clade: Any, parent_id: str | None, order: int) -> None:
            """Traverse a Newick clade tree and collect input nodes."""
            label = str(getattr(clade, "name", "") or "")
            node_id = build_node_id(label)
            nodes.append(
                InputNode(
                    node_id=node_id,
                    parent_id=parent_id,
                    label=label,
                    order=float(order),
                )
            )

            for child_order, child in enumerate(getattr(clade, "clades", [])):
                visit(child, node_id, child_order)

        visit(root, None, 0)
        self._validate_rows(nodes)
        logger.info("Loaded %d Newick rows from %s", len(nodes), source)
        return nodes

    def _load_json_rows(self, path: str | Path) -> list[InputNode]:
        """Load and normalise rows from a JSON file."""
        json_path = Path(path)
        if not json_path.exists():
            raise ValidationError(f"Input JSON file does not exist: {json_path}")

        try:
            payload = json.loads(json_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise ValidationError(f"Unable to parse JSON input: {json_path}") from exc

        rows = self._extract_json_rows(payload)
        if not rows:
            raise ValidationError("Input JSON contains no data rows.")

        nodes = [
            self._parse_row(self._normalise_json_row(row, row_number), row_number)
            for row_number, row in enumerate(rows, start=1)
        ]
        self._validate_rows(nodes)
        logger.info("Loaded %d JSON rows from %s", len(nodes), json_path)
        return nodes

    def load_tree(self, path: str | Path, *, input_format: InputFormat = "csv") -> TreeModel:
        """Load rows and convert them into a tree model."""
        rows = self.load_rows(path, input_format=input_format)
        tree = self.build_tree(rows)
        logger.info("Built tree with %d nodes and root %s", len(tree.nodes), tree.root.node_id)
        return tree

    def build_tree(self, nodes: list[InputNode]) -> TreeModel:
        """Build a tree model from validated input nodes."""
        tree_nodes = {
            node.node_id: TreeNode(
                node_id=node.node_id,
                parent_id=node.parent_id,
                label=node.label,
                order=node.order,
            )
            for node in nodes
        }

        root: TreeNode | None = None
        for node in tree_nodes.values():
            if node.parent_id is None:
                root = node
                continue
            tree_nodes[node.parent_id].add_child(node)

        if root is None:
            raise ValidationError("A single root node is required.")

        ordered_nodes = self._assign_depths_and_collect(root, depth=0)
        return TreeModel(root=root, nodes=ordered_nodes, node_map=tree_nodes)

    def _validate_headers(self, fieldnames: Sequence[str] | None) -> None:
        """Validate the CSV header names."""
        if fieldnames is None:
            raise ValidationError("Input CSV is empty.")
        if tuple(fieldnames) != self.REQUIRED_COLUMNS:
            raise ValidationError(
                "Input CSV must have exactly these columns in order: "
                + ",".join(self.REQUIRED_COLUMNS)
            )

    def _parse_row(self, row: dict[str, str | None], row_number: int) -> InputNode:
        """Parse one CSV row into an input node."""
        node_id = (row["id"] or "").strip()
        parent_raw = (row["parent"] or "").strip()
        label = (row["label"] or "").strip()
        order_raw = (row["order"] or "").strip()

        if not node_id:
            raise ValidationError(f"Row {row_number}: id cannot be empty.")
        if not label:
            raise ValidationError(f"Row {row_number}: label cannot be empty.")
        try:
            order = float(order_raw)
        except ValueError as exc:
            raise ValidationError(f"Row {row_number}: order must be numeric.") from exc

        return InputNode(
            node_id=node_id,
            parent_id=parent_raw or None,
            label=label,
            order=order,
        )

    def _extract_json_rows(self, payload: Any) -> list[Any]:
        """Extract a JSON row list from the loaded payload."""
        if isinstance(payload, list):
            return payload
        if isinstance(payload, Mapping):
            rows = payload.get("nodes")
            if isinstance(rows, list):
                return rows
        raise ValidationError("Input JSON must be a list or an object with a 'nodes' list.")

    def _normalise_json_row(self, row: Any, row_number: int) -> dict[str, str | None]:
        """Convert one JSON record into the CSV-style row shape."""
        if not isinstance(row, Mapping):
            raise ValidationError(f"Row {row_number}: JSON row must be an object.")

        normalised: dict[str, str | None] = {}
        for key in self.REQUIRED_COLUMNS:
            value = row.get(key)
            if value is None:
                normalised[key] = None
                continue
            normalised[key] = str(value)
        return normalised

    def _validate_rows(self, nodes: list[InputNode]) -> None:
        """Run all row-level validation checks."""
        self._validate_unique_ids(nodes)
        self._validate_single_root(nodes)
        self._validate_parents_exist(nodes)
        self._validate_no_cycles(nodes)

    def _validate_unique_ids(self, nodes: list[InputNode]) -> None:
        """Reject duplicate node ids."""
        seen: set[str] = set()
        duplicates: set[str] = set()
        for node in nodes:
            if node.node_id in seen:
                duplicates.add(node.node_id)
            seen.add(node.node_id)
        if duplicates:
            duplicate_text = ", ".join(sorted(duplicates))
            raise ValidationError(f"Duplicate id values found: {duplicate_text}")

    def _validate_single_root(self, nodes: list[InputNode]) -> None:
        """Require exactly one root row."""
        roots = [node.node_id for node in nodes if node.parent_id is None]
        if len(roots) != 1:
            raise ValidationError(f"Exactly one root row is required, found {len(roots)}.")

    def _validate_parents_exist(self, nodes: list[InputNode]) -> None:
        """Reject parent ids that do not exist in the input."""
        ids = {node.node_id for node in nodes}
        missing = sorted(
            {node.parent_id for node in nodes if node.parent_id and node.parent_id not in ids}
        )
        if missing:
            raise ValidationError(f"Missing parent ids referenced by rows: {', '.join(missing)}")

    def _validate_no_cycles(self, nodes: list[InputNode]) -> None:
        """Reject cyclic parent relationships."""
        parent_by_id = {node.node_id: node.parent_id for node in nodes}
        visited: set[str] = set()
        active: set[str] = set()

        def visit(node_id: str) -> None:
            """Walk the parent chain for cycle detection."""
            if node_id in active:
                raise ValidationError("Input tree contains a cycle.")
            if node_id in visited:
                return
            active.add(node_id)
            parent_id = parent_by_id[node_id]
            if parent_id is not None:
                visit(parent_id)
            active.remove(node_id)
            visited.add(node_id)

        for node_id in parent_by_id:
            visit(node_id)

    def _assign_depths_and_collect(self, root: TreeNode, depth: int) -> list[TreeNode]:
        """Assign depths recursively and collect nodes in preorder."""
        root.depth = depth
        root.sort_children()
        ordered_nodes = [root]
        for child in root.children:
            ordered_nodes.extend(self._assign_depths_and_collect(child, depth + 1))
        return ordered_nodes
