from __future__ import annotations

import csv
import html
import math
from pathlib import Path

from .models import EdgePath, LayoutOptions, LineStyle, RenderResult, TreeLayout, TreeNode

PALETTES = {
    "default": ["#2563eb", "#dc2626", "#16a34a", "#ca8a04", "#9333ea", "#0891b2"],
    "pastel": ["#7dd3fc", "#f9a8d4", "#86efac", "#fde68a", "#c4b5fd", "#fdba74"],
    "high_contrast": ["#1d4ed8", "#b91c1c", "#15803d", "#a16207", "#7e22ce", "#0f766e"],
    "earth": ["#6b8e23", "#8b5e3c", "#c2410c", "#4d7c0f", "#7c2d12", "#57534e"],
    "scientific": ["#0072b2", "#d55e00", "#009e73", "#cc79a7", "#e69f00", "#56b4e9"],
}


class CsvExporter:
    FIELDNAMES = [
        "type",
        "group",
        "branch_path",
        "id",
        "parent",
        "child",
        "label",
        "index",
        "path",
        "x",
        "y",
        "size",
        "color",
        "depth",
        "tree_layout",
        "line_style",
    ]

    def build_rows(
        self,
        result: RenderResult,
        options: LayoutOptions,
    ) -> list[dict[str, str | float | int]]:
        branch_colors = self._branch_colors(result, options)
        rows: list[dict[str, str | float | int]] = []
        rows.extend(self._build_edge_rows(result, options, branch_colors))
        rows.extend(self._build_node_rows(result.nodes, result, options, branch_colors))
        return rows

    def export(self, path: str | Path, rows: list[dict[str, str | float | int]]) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        return output_path

    def _build_edge_rows(
        self,
        result: RenderResult,
        options: LayoutOptions,
        branch_colors: dict[str, str],
    ) -> list[dict[str, str | float | int]]:
        rows: list[dict[str, str | float | int]] = []
        for edge_index, edge in enumerate(result.edges):
            target = result.tree.node_map[edge.target_id]
            group = self._group_label(target, result)
            color = self._branch_aware_color(target, result, options.edge_color, branch_colors)
            for path_index, (x, y) in enumerate(edge.points):
                rows.append(
                    {
                        "type": "link",
                        "group": group,
                        "branch_path": self._branch_path(target, result),
                        "id": edge.edge_id,
                        "parent": edge.source_id,
                        "child": edge.target_id,
                        "label": "",
                        "index": edge_index,
                        "path": path_index,
                        "x": round(x, 6),
                        "y": round(y, 6),
                        "size": "",
                        "color": color,
                        "depth": "",
                        "tree_layout": result.tree_layout,
                        "line_style": result.line_style,
                    }
                )
        return rows

    def _build_node_rows(
        self,
        nodes: list[TreeNode],
        result: RenderResult,
        options: LayoutOptions,
        branch_colors: dict[str, str],
    ) -> list[dict[str, str | float | int]]:
        return [
            {
                "type": "node",
                "group": self._group_label(node, result),
                "branch_path": self._branch_path(node, result),
                "id": node.node_id,
                "parent": node.parent_id or "",
                "child": "",
                "label": node.label,
                "index": "",
                "path": "",
                "x": round(node.x, 6),
                "y": round(node.y, 6),
                "size": round(options.node_radius, 3),
                "color": self._branch_aware_color(node, result, options.node_color, branch_colors),
                "depth": node.depth,
                "tree_layout": result.tree_layout,
                "line_style": result.line_style,
            }
            for node in nodes
        ]

    def _branch_colors(self, result: RenderResult, options: LayoutOptions) -> dict[str, str]:
        if options.color_mode != "palette":
            return {}
        palette = PALETTES[options.palette]
        return {
            child.node_id: palette[index % len(palette)]
            for index, child in enumerate(result.root.children)
        }

    def _branch_aware_color(
        self,
        node: TreeNode,
        result: RenderResult,
        default_color: str,
        branch_colors: dict[str, str],
    ) -> str:
        branch = result.tree.top_level_branch(node)
        if branch is None:
            return default_color
        return branch_colors.get(branch.node_id, default_color)

    def _group_label(self, node: TreeNode, result: RenderResult) -> str:
        branch = result.tree.top_level_branch(node)
        if branch is None:
            return result.root.label
        return branch.label

    def _branch_path(self, node: TreeNode, result: RenderResult) -> str:
        return "|".join(ancestor.label for ancestor in result.tree.path_to_node(node))


class SvgExporter:
    def export(
        self,
        path: str | Path,
        result: RenderResult,
        show_labels: bool,
        options: LayoutOptions,
    ) -> Path:
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        branch_colors = self._branch_colors(result, options)
        scale = max(options.svg_scale, 0.01)

        min_x, min_y, width, height = self._compute_bounds(result.nodes, options, show_labels)
        view_box = f"0 0 {width:.3f} {height:.3f}"
        path_elements = "\n".join(
            self._svg_path(
                edge,
                min_x,
                min_y,
                options.margin,
                scale,
                self._edge_color(edge, result, options, branch_colors),
            )
            for edge in result.edges
        )
        node_elements = "\n".join(
            self._svg_node(node, min_x, min_y, options, scale, show_labels, result, branch_colors) for node in result.nodes
        )

        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
            f'width="{width:.3f}" height="{height:.3f}" role="img">\n'
            "<title>Dendrogram</title>\n"
            "<style>\n"
            f".edge {{ fill: none; stroke-width: {2 * scale:.3f}; stroke-linecap: round; }}\n"
            ".node { }\n"
            ".label { font-family: Helvetica, Arial, sans-serif; }\n"
            "</style>\n"
            f"{path_elements}\n"
            f"{node_elements}\n"
            "</svg>\n"
        )

        output_path.write_text(svg_content, encoding="utf-8")
        return output_path

    def _compute_bounds(
        self,
        nodes: list[TreeNode],
        options: LayoutOptions,
        show_labels: bool,
    ) -> tuple[float, float, float, float]:
        min_x = min(node.x for node in nodes)
        max_x = max(node.x for node in nodes)
        min_y = min(node.y for node in nodes)
        max_y = max(node.y for node in nodes)
        label_padding = 0.0
        if show_labels and options.label_mode != "none":
            label_padding = max(options.node_radius + options.label_offset + (options.font_size * 8), 0.0)
        min_x -= label_padding
        max_x += label_padding
        min_y -= label_padding
        max_y += label_padding
        scale = max(options.svg_scale, 0.01)
        width = ((max_x - min_x) + (options.margin * 2)) * scale
        height = ((max_y - min_y) + (options.margin * 2)) * scale
        return min_x, min_y, width, height

    def _svg_path(
        self,
        edge: EdgePath,
        min_x: float,
        min_y: float,
        margin: float,
        scale: float,
        stroke_color: str,
    ) -> str:
        transformed = [f"{((x - min_x + margin) * scale):.3f},{((y - min_y + margin) * scale):.3f}" for x, y in edge.points]
        return f'<path class="edge" stroke="{stroke_color}" d="M {" L ".join(transformed)}" />'

    def _svg_node(
        self,
        node: TreeNode,
        min_x: float,
        min_y: float,
        options: LayoutOptions,
        scale: float,
        show_labels: bool,
        result: RenderResult,
        branch_colors: dict[str, str],
    ) -> str:
        x = (node.x - min_x + options.margin) * scale
        y = (node.y - min_y + options.margin) * scale
        parts: list[str] = []
        if self._should_render_node(node, options):
            parts.append(
                f'<circle class="node" fill="{self._node_color(node, result, options, branch_colors)}" '
                f'cx="{x:.3f}" cy="{y:.3f}" r="{(options.node_radius * scale):.3f}" />'
            )
        if show_labels and self._should_render_label(node, options):
            parts.append(self._svg_label(node, x, y, options, scale, result, branch_colors))
        return "\n".join(parts)

    def _should_render_node(self, node: TreeNode, options: LayoutOptions) -> bool:
        if node.parent_id is None:
            return options.show_root_node
        if node.is_leaf:
            return True
        return options.show_internal_nodes

    def _should_render_label(self, node: TreeNode, options: LayoutOptions) -> bool:
        if options.label_mode == "none":
            return False
        if options.label_mode == "leaves":
            return node.is_leaf
        return True

    def _svg_label(
        self,
        node: TreeNode,
        x: float,
        y: float,
        options: LayoutOptions,
        scale: float,
        result: RenderResult,
        branch_colors: dict[str, str],
    ) -> str:
        if node.angle is not None and node.radius is not None and options.label_orientation == "auto":
            return self._svg_radial_label(node, x, y, options, scale, result, branch_colors)
        label_x = x + ((options.node_radius + options.label_offset) * scale)
        label_y = y
        return (
            f'<text class="label" x="{label_x:.3f}" y="{label_y:.3f}" '
            f'font-size="{options.font_size * scale:.3f}" fill="{self._label_color(node, result, options, branch_colors)}" '
            f'dominant-baseline="middle">'
            f"{html.escape(node.label)}</text>"
        )

    def _svg_radial_label(
        self,
        node: TreeNode,
        x: float,
        y: float,
        options: LayoutOptions,
        scale: float,
        result: RenderResult,
        branch_colors: dict[str, str],
    ) -> str:
        assert node.angle is not None
        radius_delta = options.label_offset * scale
        label_x = x + (radius_delta * math.cos(node.angle))
        label_y = y + (radius_delta * math.sin(node.angle))
        rotation = math.degrees(node.angle)
        anchor = "start"
        if math.cos(node.angle) < 0:
            rotation += 180.0
            anchor = "end"
        return (
            f'<text class="label" x="{label_x:.3f}" y="{label_y:.3f}" '
            f'font-size="{options.font_size * scale:.3f}" fill="{self._label_color(node, result, options, branch_colors)}" '
            f'text-anchor="{anchor}" dominant-baseline="middle" '
            f'transform="rotate({rotation:.3f} {label_x:.3f} {label_y:.3f})">'
            f"{html.escape(node.label)}</text>"
        )

    def _branch_colors(self, result: RenderResult, options: LayoutOptions) -> dict[str, str]:
        if options.color_mode != "palette":
            return {}
        palette = PALETTES[options.palette]
        return {
            child.node_id: palette[index % len(palette)]
            for index, child in enumerate(result.root.children)
        }

    def _edge_color(
        self,
        edge: EdgePath,
        result: RenderResult,
        options: LayoutOptions,
        branch_colors: dict[str, str],
    ) -> str:
        node = result.tree.node_map[edge.target_id]
        return self._branch_aware_color(node, result, options.edge_color, branch_colors)

    def _node_color(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
        branch_colors: dict[str, str],
    ) -> str:
        return self._branch_aware_color(node, result, options.node_color, branch_colors)

    def _label_color(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
        branch_colors: dict[str, str],
    ) -> str:
        return self._branch_aware_color(node, result, options.label_color, branch_colors)

    def _branch_aware_color(
        self,
        node: TreeNode,
        result: RenderResult,
        fallback_color: str,
        branch_colors: dict[str, str],
    ) -> str:
        branch = result.tree.top_level_branch(node)
        if branch is None:
            return fallback_color
        return branch_colors.get(branch.node_id, fallback_color)
