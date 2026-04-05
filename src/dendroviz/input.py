from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .errors import ValidationError
from .models import InputFormat, InputNode, TreeModel, TreeNode


class TreeCsvLoader:
    REQUIRED_COLUMNS = ("id", "parent", "label", "order")

    def load_rows(self, path: str | Path, *, input_format: InputFormat = "csv") -> list[InputNode]:
        if input_format == "csv":
            return self._load_csv_rows(path)
        if input_format == "newick":
            return self._load_newick_rows(path)
        raise ValidationError(f"Unsupported input format: {input_format}")

    def _load_csv_rows(self, path: str | Path) -> list[InputNode]:
        csv_path = Path(path)
        if not csv_path.exists():
            raise ValidationError(f"Input CSV does not exist: {csv_path}")

        with csv_path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.DictReader(handle)
            self._validate_headers(reader.fieldnames)
            nodes = [self._parse_row(row, row_number) for row_number, row in enumerate(reader, start=2)]

        if not nodes:
            raise ValidationError("Input CSV contains headers but no data rows.")

        self._validate_rows(nodes)
        return nodes

    def _load_newick_rows(self, path: str | Path) -> list[InputNode]:
        newick_path = Path(path)
        if not newick_path.exists():
            raise ValidationError(f"Input Newick file does not exist: {newick_path}")

        try:
            from Bio import Phylo
        except ImportError as exc:
            raise ImportError(
                "Newick support requires BioPython. Install it with: pip install biopython"
            ) from exc

        try:
            phylogeny = Phylo.read(str(newick_path), "newick")
        except Exception as exc:
            raise ValidationError(f"Unable to parse Newick input: {newick_path}") from exc

        root = getattr(phylogeny, "root", None)
        if root is None:
            raise ValidationError("Newick input does not contain a root clade.")

        nodes: list[InputNode] = []
        generated_ids: set[str] = set()
        next_id = 0

        def build_node_id(label: str) -> str:
            nonlocal next_id
            base_label = "".join(character if character.isalnum() else "_" for character in label.strip()).strip("_")
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
        return nodes

    def load_tree(self, path: str | Path, *, input_format: InputFormat = "csv") -> TreeModel:
        return self.build_tree(self.load_rows(path, input_format=input_format))

    def build_tree(self, nodes: list[InputNode]) -> TreeModel:
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

    def _validate_headers(self, fieldnames: list[str] | None) -> None:
        if fieldnames is None:
            raise ValidationError("Input CSV is empty.")
        if tuple(fieldnames) != self.REQUIRED_COLUMNS:
            raise ValidationError(
                "Input CSV must have exactly these columns in order: "
                + ",".join(self.REQUIRED_COLUMNS)
            )

    def _parse_row(self, row: dict[str, str | None], row_number: int) -> InputNode:
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

    def _validate_rows(self, nodes: list[InputNode]) -> None:
        self._validate_unique_ids(nodes)
        self._validate_single_root(nodes)
        self._validate_parents_exist(nodes)
        self._validate_no_cycles(nodes)

    def _validate_unique_ids(self, nodes: list[InputNode]) -> None:
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
        roots = [node.node_id for node in nodes if node.parent_id is None]
        if len(roots) != 1:
            raise ValidationError(f"Exactly one root row is required, found {len(roots)}.")

    def _validate_parents_exist(self, nodes: list[InputNode]) -> None:
        ids = {node.node_id for node in nodes}
        missing = sorted({node.parent_id for node in nodes if node.parent_id and node.parent_id not in ids})
        if missing:
            raise ValidationError(f"Missing parent ids referenced by rows: {', '.join(missing)}")

    def _validate_no_cycles(self, nodes: list[InputNode]) -> None:
        parent_by_id = {node.node_id: node.parent_id for node in nodes}
        visited: set[str] = set()
        active: set[str] = set()

        def visit(node_id: str) -> None:
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
        root.depth = depth
        root.sort_children()
        ordered_nodes = [root]
        for child in root.children:
            ordered_nodes.extend(self._assign_depths_and_collect(child, depth + 1))
        return ordered_nodes
