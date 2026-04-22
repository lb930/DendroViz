import csv
import html
import json
import logging
import math
import re
from collections.abc import Sequence
from pathlib import Path

from .errors import ValidationError
from .models import EdgePath, LayoutOptions, RenderResult, TreeNode

logger = logging.getLogger(__name__)
PALETTE_FALLBACK_COLOUR = "#64748b"

SET1_PALETTE = [
    "#e41a1c",
    "#377eb8",
    "#4daf4a",
    "#984ea3",
    "#ff7f00",
    "#ffff33",
    "#a65628",
    "#f781bf",
    "#999999",
]

PALETTES = {
    "set1": SET1_PALETTE,
    "set2": [
        "#66c2a5",
        "#fc8d62",
        "#8da0cb",
        "#e78ac3",
        "#a6d854",
        "#ffd92f",
        "#e5c494",
        "#b3b3b3",
    ],
    "set3": [
        "#8dd3c7",
        "#ffffb3",
        "#bebada",
        "#fb8072",
        "#80b1d3",
        "#fdb462",
        "#b3de69",
        "#fccde5",
        "#d9d9d9",
        "#bc80bd",
        "#ccebc5",
        "#ffed6f",
    ],
    "pastel1": [
        "#fbb4ae",
        "#b3cde3",
        "#ccebc5",
        "#decbe4",
        "#fed9a6",
        "#ffffcc",
        "#e5d8bd",
        "#fddaec",
        "#f2f2f2",
    ],
    "pastel2": [
        "#b3e2cd",
        "#fdcdac",
        "#cbd5e8",
        "#f4cae4",
        "#e6f5c9",
        "#fff2ae",
        "#f1e2cc",
        "#cccccc",
    ],
    "accent": [
        "#7fc97f",
        "#beaed4",
        "#fdc086",
        "#ffff99",
        "#386cb0",
        "#f0027f",
        "#bf5b17",
        "#666666",
    ],
    "paired": [
        "#a6cee3",
        "#1f78b4",
        "#b2df8a",
        "#33a02c",
        "#fb9a99",
        "#e31a1c",
        "#fdbf6f",
        "#ff7f00",
        "#cab2d6",
        "#6a3d9a",
        "#ffff99",
        "#b15928",
    ],
    "tableau": [
        "#1f77b4",
        "#ff7f0e",
        "#2ca02c",
        "#d62728",
        "#9467bd",
        "#8c564b",
        "#e377c2",
        "#7f7f7f",
        "#bcbd22",
        "#17becf",
    ],
    "dark2": [
        "#1b9e77",
        "#d95f02",
        "#7570b3",
        "#e7298a",
        "#66a61e",
        "#e6ab02",
        "#a6761d",
        "#666666",
    ],
    "scientific": [
        "#e69f00",
        "#56b4e9",
        "#009e73",
        "#f0e442",
        "#0072b2",
        "#d55e00",
        "#cc79a7",
        "#000000",
    ],
}


def branch_colours_for(result: RenderResult, options: LayoutOptions) -> dict[str, str]:
    """Build per-branch colours when palette mode is enabled."""
    if options.colour_mode != "palette":
        return {}
    palette = resolve_palette_colours(options.palette)
    branch_depth = resolve_palette_depth(options.palette_depth)
    return {
        branch_root.node_id: palette[index % len(palette)]
        for index, branch_root in enumerate(
            node for node in result.tree.nodes if node.depth == branch_depth
        )
    }


def resolve_palette_colours(palette_spec: object) -> list[str]:
    """Resolve a palette specification into validated hex colours."""
    if isinstance(palette_spec, str):
        candidate = palette_spec.strip()
        palette = PALETTES.get(candidate.lower())
        if palette is None:
            palette = _split_palette_string(candidate)
    elif isinstance(palette_spec, Sequence):
        palette = list(palette_spec)
    else:
        raise ValidationError(
            "Palette must be a named palette or a sequence of hex colour strings."
        )

    resolved = [
        _normalise_hex_colour(colour, index) for index, colour in enumerate(palette, start=1)
    ]
    if not resolved:
        raise ValidationError("Palette must contain at least one colour.")
    return resolved


def _split_palette_string(palette_spec: str) -> list[str]:
    """Split a textual palette specification into colour strings."""
    tokens = [token for token in re.split(r"[\s,]+", palette_spec) if token]
    if not tokens:
        raise ValidationError("Palette string cannot be empty.")
    return tokens


def _normalise_hex_colour(colour: object, index: int) -> str:
    """Validate and normalise a hex colour string."""
    if not isinstance(colour, str):
        raise ValidationError(f"Palette colour {index} must be a string.")
    candidate = colour.strip()
    if candidate.startswith("#"):
        candidate = candidate[1:]
    if not re.fullmatch(r"[0-9a-fA-F]{6}", candidate):
        raise ValidationError(
            f"Palette colour {index} must be a hex colour in #RRGGBB format: {colour!r}"
        )
    return f"#{candidate.lower()}"


def resolve_palette_depth(branch_depth: int) -> int:
    """Validate and normalise the palette depth."""
    if branch_depth < 1:
        raise ValidationError("Palette branch depth must be at least 1.")
    return branch_depth


def resolve_branch_root(
    node: TreeNode,
    result: RenderResult,
    branch_depth: int,
) -> TreeNode | None:
    """Return the ancestor that anchors palette colouring for a node."""
    if node.depth < branch_depth:
        return None
    current = node
    while current.depth > branch_depth and current.parent_id is not None:
        current = result.tree.node_map[current.parent_id]
    if current.depth != branch_depth:
        return None
    return current


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
        "colour",
        "depth",
        "tree_layout",
        "line_style",
    ]

    def build_rows(
        self,
        result: RenderResult,
        options: LayoutOptions,
    ) -> list[dict[str, str | float | int]]:
        """Build CSV rows for all routed edges and nodes."""
        branch_colours = branch_colours_for(result, options)
        rows: list[dict[str, str | float | int]] = []
        rows.extend(self._build_edge_rows(result, options, branch_colours))
        rows.extend(self._build_node_rows(result.nodes, result, options, branch_colours))
        return rows

    def export(self, path: str | Path, rows: list[dict[str, str | float | int]]) -> Path:
        """Write CSV rows to disk."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        logger.info("Writing CSV export to %s (%d rows)", output_path, len(rows))
        with output_path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=self.FIELDNAMES)
            writer.writeheader()
            writer.writerows(rows)
        return output_path

    def _build_edge_rows(
        self,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> list[dict[str, str | float | int]]:
        """Build CSV rows for routed edges."""
        rows: list[dict[str, str | float | int]] = []
        for edge_index, edge in enumerate(result.edges):
            target = result.tree.node_map[edge.target_id]
            group = self._group_label(target, result, options.palette_depth)
            colour = self._branch_aware_colour(
                target,
                result,
                PALETTE_FALLBACK_COLOUR
                if options.colour_mode == "palette"
                else options.edge_colour,
                branch_colours,
                options.palette_depth,
            )
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
                        "colour": colour,
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
        branch_colours: dict[str, str],
    ) -> list[dict[str, str | float | int]]:
        """Build CSV rows for nodes."""
        return [
            {
                "type": "node",
                "group": self._group_label(node, result, options.palette_depth),
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
                "colour": self._branch_aware_colour(
                    node,
                    result,
                    (
                        PALETTE_FALLBACK_COLOUR
                        if options.colour_mode == "palette"
                        else options.node_colour
                    ),
                    branch_colours,
                    options.palette_depth,
                ),
                "depth": node.depth,
                "tree_layout": result.tree_layout,
                "line_style": result.line_style,
            }
            for node in nodes
        ]

    def _branch_aware_colour(
        self,
        node: TreeNode,
        result: RenderResult,
        default_colour: str,
        branch_colours: dict[str, str],
        branch_depth: int,
    ) -> str:
        """Resolve the display colour for a node or edge."""
        branch = resolve_branch_root(node, result, branch_depth)
        if branch is None:
            return default_colour
        return branch_colours.get(branch.node_id, default_colour)

    def _group_label(
        self,
        node: TreeNode,
        result: RenderResult,
        branch_depth: int,
    ) -> str:
        """Return the label for the branch depth used by palette colouring."""
        branch = resolve_branch_root(node, result, branch_depth)
        if branch is None:
            return result.root.label
        return branch.label

    def _branch_path(self, node: TreeNode, result: RenderResult) -> str:
        """Return a human-readable path of labels to a node."""
        return "|".join(ancestor.label for ancestor in result.tree.path_to_node(node))


class JsonExporter:
    def export(
        self,
        path: str | Path,
        result: RenderResult,
        options: LayoutOptions,
        show_labels: bool,
    ) -> Path:
        """Write a JSON rendering to disk."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        payload = self._build_payload(result, options, show_labels)
        logger.info(
            "Writing JSON export to %s (%d nodes, %d edges)",
            output_path,
            len(result.nodes),
            len(result.edges),
        )
        output_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return output_path

    def _build_payload(
        self,
        result: RenderResult,
        options: LayoutOptions,
        show_labels: bool,
    ) -> dict[str, object]:
        """Build a JSON-serializable render payload."""
        branch_colours = branch_colours_for(result, options)
        return {
            "tree_layout": result.tree_layout,
            "line_style": result.line_style,
            "show_labels": show_labels,
            "options": self._options_payload(options),
            "nodes": [
                self._node_payload(node, result, options, branch_colours) for node in result.nodes
            ],
            "edges": [
                self._edge_payload(edge, result, options, branch_colours) for edge in result.edges
            ],
        }

    def _options_payload(self, options: LayoutOptions) -> dict[str, object]:
        """Serialize layout options to a JSON object."""
        return {
            "depth_spacing": options.depth_spacing,
            "sibling_spacing": options.sibling_spacing,
            "radial_base_angle_deg": options.radial_base_angle_deg,
            "radial_sweep_deg": options.radial_sweep_deg,
            "curve_points": options.curve_points,
            "straight_points": options.straight_points,
            "node_radius": options.node_radius,
            "margin": options.margin,
            "svg_scale": options.svg_scale,
            "font_size": options.font_size,
            "root_fork_fraction": options.root_fork_fraction,
            "show_internal_nodes": options.show_internal_nodes,
            "show_root_node": options.show_root_node,
            "label_mode": options.label_mode,
            "label_orientation": options.label_orientation,
            "label_offset": options.label_offset,
            "colour_mode": options.colour_mode,
            "palette": options.palette,
            "palette_depth": options.palette_depth,
            "edge_colour": options.edge_colour,
            "node_colour": options.node_colour,
            "label_colour": options.label_colour,
        }

    def _node_payload(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> dict[str, object]:
        """Serialize a node for JSON output."""
        return {
            "node_id": node.node_id,
            "parent_id": node.parent_id,
            "label": node.label,
            "order": node.order,
            "depth": node.depth,
            "x": node.x,
            "y": node.y,
            "angle": node.angle,
            "radius": node.radius,
            "leaf_index": node.leaf_index,
            "is_leaf": node.is_leaf,
            "group": self._group_label(node, result, options.palette_depth),
            "branch_path": self._branch_path(node, result),
            "colour": self._branch_aware_colour(
                node,
                result,
                PALETTE_FALLBACK_COLOUR
                if options.colour_mode == "palette"
                else options.node_colour,
                branch_colours,
                options.palette_depth,
            ),
        }

    def _edge_payload(
        self,
        edge: EdgePath,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> dict[str, object]:
        """Serialize an edge for JSON output."""
        node = result.tree.node_map[edge.target_id]
        return {
            "edge_id": edge.edge_id,
            "source_id": edge.source_id,
            "target_id": edge.target_id,
            "group": self._group_label(node, result, options.palette_depth),
            "branch_path": self._branch_path(node, result),
            "colour": self._branch_aware_colour(
                node,
                result,
                PALETTE_FALLBACK_COLOUR
                if options.colour_mode == "palette"
                else options.edge_colour,
                branch_colours,
                options.palette_depth,
            ),
            "points": [{"x": x, "y": y} for x, y in edge.points],
        }

    def _branch_aware_colour(
        self,
        node: TreeNode,
        result: RenderResult,
        default_colour: str,
        branch_colours: dict[str, str],
        branch_depth: int,
    ) -> str:
        """Resolve the display colour for a node or edge."""
        branch = resolve_branch_root(node, result, branch_depth)
        if branch is None:
            return default_colour
        return branch_colours.get(branch.node_id, default_colour)

    def _group_label(
        self,
        node: TreeNode,
        result: RenderResult,
        branch_depth: int,
    ) -> str:
        """Return the label for the branch depth used by palette colouring."""
        branch = resolve_branch_root(node, result, branch_depth)
        if branch is None:
            return result.root.label
        return branch.label

    def _branch_path(self, node: TreeNode, result: RenderResult) -> str:
        """Return a human-readable path of labels to a node."""
        return "|".join(ancestor.label for ancestor in result.tree.path_to_node(node))


class SvgExporter:
    def export(
        self,
        path: str | Path,
        result: RenderResult,
        show_labels: bool,
        options: LayoutOptions,
    ) -> Path:
        """Write an SVG rendering to disk."""
        output_path = Path(path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        branch_colours = branch_colours_for(result, options)
        scale = max(options.svg_scale, 0.01)
        legend_entries = self._palette_legend_entries(result, options, branch_colours)
        logger.info(
            "Writing SVG export to %s (%d nodes, %d edges)",
            output_path,
            len(result.nodes),
            len(result.edges),
        )

        min_x, min_y, width, height = self._compute_bounds(result.nodes, options, show_labels)
        legend_svg = ""
        if legend_entries:
            legend_svg, legend_width, legend_height = self._svg_palette_legend(
                legend_entries,
                width,
                height,
                scale,
            )
            width = max(width, legend_width)
            height = max(height, legend_height)
        view_box = f"0 0 {width:.3f} {height:.3f}"
        path_elements = "\n".join(
            self._svg_path(
                edge,
                min_x,
                min_y,
                options.margin,
                scale,
                self._edge_colour(edge, result, options, branch_colours),
                result,
                options,
                branch_colours,
            )
            for edge in result.edges
        )
        node_elements = "\n".join(
            self._svg_node(
                node,
                min_x,
                min_y,
                options,
                scale,
                show_labels,
                result,
                branch_colours,
            )
            for node in result.nodes
        )

        svg_content = (
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{view_box}" '
            f'width="{width:.3f}" height="{height:.3f}" role="img">\n'
            "<title>Dendrogram</title>\n"
            "<style>\n"
            f".edge {{ fill: none; stroke-width: {2 * scale:.3f}; stroke-linecap: round; }}\n"
            ".node { }\n"
            ".label { font-family: Helvetica, Arial, sans-serif; }\n"
            ".legend { font-family: Helvetica, Arial, sans-serif; }\n"
            ".legend-title { font-weight: 700; }\n"
            "</style>\n"
            f"{path_elements}\n"
            f"{node_elements}\n"
            f"{legend_svg}\n"
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
        """Compute the SVG bounding box for a tree."""
        min_x = min(node.x for node in nodes)
        max_x = max(node.x for node in nodes)
        min_y = min(node.y for node in nodes)
        max_y = max(node.y for node in nodes)
        label_padding = 0.0
        if show_labels and options.label_mode != "none":
            label_padding = max(
                options.node_radius + options.label_offset + (options.font_size * 8), 0.0
            )
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
        stroke_colour: str,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> str:
        """Render one SVG path element."""
        metadata = self._svg_element_metadata_for_edge(edge, result, options, branch_colours)
        title = self._svg_element_title_for_edge(edge, result, options)
        transformed = [
            f"{((x - min_x + margin) * scale):.3f},{((y - min_y + margin) * scale):.3f}"
            for x, y in edge.points
        ]
        return (
            f'<path class="edge" stroke="{stroke_colour}" {metadata} '
            f'd="M {" L ".join(transformed)}">'
            f"{title}</path>"
        )

    def _svg_node(
        self,
        node: TreeNode,
        min_x: float,
        min_y: float,
        options: LayoutOptions,
        scale: float,
        show_labels: bool,
        result: RenderResult,
        branch_colours: dict[str, str],
    ) -> str:
        """Render one SVG node and optional label."""
        x = (node.x - min_x + options.margin) * scale
        y = (node.y - min_y + options.margin) * scale
        parts: list[str] = []
        if self._should_render_node(node, options):
            node_colour = self._node_colour(node, result, options, branch_colours)
            metadata = self._svg_element_metadata_for_node(
                node,
                result,
                options,
                branch_colours,
                node_colour,
            )
            title = self._svg_element_title_for_node(node, result, options)
            parts.append(
                f'<circle class="node" fill="{node_colour}" {metadata} '
                f'cx="{x:.3f}" cy="{y:.3f}" r="{(options.node_radius * scale):.3f}">'
                f"{title}</circle>"
            )
        if show_labels and self._should_render_label(node, options):
            parts.append(
                self._svg_label(
                    node,
                    x,
                    y,
                    options,
                    scale,
                    result,
                    branch_colours,
                    self._layout_for_node(node, result),
                )
            )
        return "\n".join(parts)

    def _layout_for_node(self, node: TreeNode, result: RenderResult) -> str:
        """Infer the rendered tree layout from a node's coordinates."""
        if node.angle is not None and node.radius is not None:
            return "radial"
        root = result.root
        if abs(root.y - node.y) > abs(root.x - node.x):
            return "vertical"
        return "horizontal"

    def _should_render_node(self, node: TreeNode, options: LayoutOptions) -> bool:
        """Return whether the node marker should be rendered."""
        if node.parent_id is None:
            return options.show_root_node
        if node.is_leaf:
            return True
        return options.show_internal_nodes

    def _should_render_label(self, node: TreeNode, options: LayoutOptions) -> bool:
        """Return whether the node label should be rendered."""
        if node.parent_id is None:
            return options.show_root_node and options.label_mode != "none"
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
        branch_colours: dict[str, str],
        tree_layout: str,
    ) -> str:
        """Render a non-radial SVG label."""
        label_colour = self._label_colour(node, result, options, branch_colours)
        metadata = self._svg_element_metadata_for_node(
            node,
            result,
            options,
            branch_colours,
            label_colour,
        )
        title = self._svg_element_title_for_node(node, result, options)
        if (
            node.angle is not None
            and node.radius is not None
            and options.label_orientation == "auto"
        ):
            return self._svg_radial_label(
                node,
                x,
                y,
                options,
                scale,
                label_colour,
                metadata,
                title,
            )
        if tree_layout == "horizontal":
            if node.is_leaf or options.label_mode == "leaves":
                label_x = x + ((options.node_radius + options.label_offset) * scale)
                label_y = y
                anchor = "start"
            else:
                label_x = x
                label_y = y - ((options.node_radius + options.label_offset) * scale)
                anchor = "middle"
        else:
            label_x = x + ((options.node_radius + options.label_offset) * scale)
            label_y = y
            anchor = "start"
        return (
            f'<text class="label" {metadata} x="{label_x:.3f}" y="{label_y:.3f}" '
            f'font-size="{options.font_size * scale:.3f}" fill="{label_colour}" '
            f'text-anchor="{anchor}" dominant-baseline="middle">'
            f"{title}{html.escape(node.label)}</text>"
        )

    def _svg_radial_label(
        self,
        node: TreeNode,
        x: float,
        y: float,
        options: LayoutOptions,
        scale: float,
        label_colour: str,
        metadata: str,
        title: str,
    ) -> str:
        """Render a radial SVG label."""
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
            f'<text class="label" {metadata} x="{label_x:.3f}" y="{label_y:.3f}" '
            f'font-size="{options.font_size * scale:.3f}" fill="{label_colour}" '
            f'text-anchor="{anchor}" dominant-baseline="middle" '
            f'transform="rotate({rotation:.3f} {label_x:.3f} {label_y:.3f})">'
            f"{title}{html.escape(node.label)}</text>"
        )

    def _edge_colour(
        self,
        edge: EdgePath,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> str:
        """Resolve the stroke colour for an edge."""
        node = result.tree.node_map[edge.target_id]
        return self._branch_aware_colour(
            node,
            result,
            PALETTE_FALLBACK_COLOUR if options.colour_mode == "palette" else options.edge_colour,
            branch_colours,
            options.palette_depth,
        )

    def _node_colour(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> str:
        """Resolve the fill colour for a node."""
        return self._branch_aware_colour(
            node,
            result,
            PALETTE_FALLBACK_COLOUR if options.colour_mode == "palette" else options.node_colour,
            branch_colours,
            options.palette_depth,
        )

    def _label_colour(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> str:
        """Resolve the fill colour for a label."""
        return self._branch_aware_colour(
            node,
            result,
            PALETTE_FALLBACK_COLOUR if options.colour_mode == "palette" else options.label_colour,
            branch_colours,
            options.palette_depth,
        )

    def _branch_aware_colour(
        self,
        node: TreeNode,
        result: RenderResult,
        fallback_colour: str,
        branch_colours: dict[str, str],
        branch_depth: int,
    ) -> str:
        """Resolve a palette colour for the node's branch or use a fallback."""
        branch = resolve_branch_root(node, result, branch_depth)
        if branch is None:
            return fallback_colour
        return branch_colours.get(branch.node_id, fallback_colour)

    def _svg_element_metadata_for_node(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
        colour: str,
    ) -> str:
        """Return optional SVG data attributes for a node-related element."""
        if not options.show_svg_data_attributes:
            return ""
        branch = resolve_branch_root(node, result, options.palette_depth)
        branch_id = branch.node_id if branch is not None else ""
        branch_path = "|".join(ancestor.node_id for ancestor in result.tree.path_to_node(node))
        return (
            f'data-node-id="{html.escape(node.node_id, quote=True)}" '
            f'data-parent-id="{html.escape(node.parent_id or "", quote=True)}" '
            f'data-label="{html.escape(node.label, quote=True)}" '
            f'data-depth="{node.depth}" '
            f'data-branch-id="{html.escape(branch_id, quote=True)}" '
            f'data-branch-path="{html.escape(branch_path, quote=True)}" '
            f'data-colour="{html.escape(colour, quote=True)}"'
        )

    def _svg_element_metadata_for_edge(
        self,
        edge: EdgePath,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> str:
        """Return optional SVG data attributes for an edge-related element."""
        if not options.show_svg_data_attributes:
            return ""
        target = result.tree.node_map[edge.target_id]
        branch = resolve_branch_root(target, result, options.palette_depth)
        branch_id = branch.node_id if branch is not None else ""
        branch_path = "|".join(ancestor.node_id for ancestor in result.tree.path_to_node(target))
        colour = self._branch_aware_colour(
            target,
            result,
            PALETTE_FALLBACK_COLOUR if options.colour_mode == "palette" else options.edge_colour,
            branch_colours,
            options.palette_depth,
        )
        return (
            f'data-edge-id="{html.escape(edge.edge_id, quote=True)}" '
            f'data-source-id="{html.escape(edge.source_id, quote=True)}" '
            f'data-target-id="{html.escape(edge.target_id, quote=True)}" '
            f'data-branch-id="{html.escape(branch_id, quote=True)}" '
            f'data-branch-path="{html.escape(branch_path, quote=True)}" '
            f'data-colour="{html.escape(colour, quote=True)}"'
        )

    def _svg_element_title_for_node(
        self,
        node: TreeNode,
        result: RenderResult,
        options: LayoutOptions,
    ) -> str:
        """Return an optional short SVG title for a node-related element."""
        if not options.show_svg_titles:
            return ""
        return f"<title>{html.escape(node.label)}</title>"

    def _svg_element_title_for_edge(
        self,
        edge: EdgePath,
        result: RenderResult,
        options: LayoutOptions,
    ) -> str:
        """Return an optional short SVG title for an edge-related element."""
        if not options.show_svg_titles:
            return ""
        source = result.tree.node_map[edge.source_id]
        target = result.tree.node_map[edge.target_id]
        return f"<title>{html.escape(source.label)} → {html.escape(target.label)}</title>"

    def _palette_legend_entries(
        self,
        result: RenderResult,
        options: LayoutOptions,
        branch_colours: dict[str, str],
    ) -> list[tuple[str, str]]:
        """Build legend entries for palette-driven output."""
        if options.colour_mode != "palette" or not options.show_palette_legend:
            return []
        branch_depth = resolve_palette_depth(options.palette_depth)
        entries: list[tuple[str, str]] = []
        for node in result.tree.nodes:
            if node.depth != branch_depth:
                continue
            entries.append((node.label, branch_colours.get(node.node_id, PALETTE_FALLBACK_COLOUR)))
        return entries

    def _svg_palette_legend(
        self,
        entries: list[tuple[str, str]],
        tree_width: float,
        tree_height: float,
        scale: float,
    ) -> tuple[str, float, float]:
        """Render a compact palette legend beside the tree."""
        if not entries:
            return "", tree_width, 0.0

        legend_x = tree_width + (24.0 * scale)
        legend_y = 24.0 * scale
        padding_x = 14.0 * scale
        padding_y = 12.0 * scale
        swatch_size = 10.0 * scale
        row_height = 18.0 * scale
        row_gap = 8.0 * scale
        title_font_size = 12.0 * scale
        entry_font_size = 11.0 * scale
        label_gap = 8.0 * scale
        title_height = 16.0 * scale
        max_label_chars = max(len(label) for label, _ in entries)
        content_width = max(132.0 * scale, (max_label_chars * 6.4 + 48.0) * scale)
        legend_height = (padding_y * 2) + title_height + row_gap + (len(entries) * row_height)

        legend = [
            f'<g id="palette-legend" class="legend" aria-label="Palette legend" '
            f'transform="translate({legend_x:.3f} {legend_y:.3f})">',
            (
                f'<rect x="0" y="0" width="{content_width:.3f}" '
                f'height="{legend_height:.3f}" rx="{8.0 * scale:.3f}" '
                f'fill="#ffffff" fill-opacity="0.86" stroke="#cbd5e1" />'
            ),
            (
                f'<text class="legend-title" x="{padding_x:.3f}" y="{padding_y:.3f}" '
                f'font-size="{title_font_size:.3f}" fill="#0f172a" '
                f'dominant-baseline="hanging">Palette legend</text>'
            ),
        ]

        start_y = padding_y + title_height + row_gap + (row_height / 2.0)
        for index, (label, colour) in enumerate(entries):
            row_y = start_y + (index * row_height)
            legend.append(
                (
                    f'<rect class="legend-swatch" x="{padding_x:.3f}" '
                    f'y="{(row_y - (swatch_size / 2.0)):.3f}" '
                    f'width="{swatch_size:.3f}" height="{swatch_size:.3f}" '
                    f'rx="{2.0 * scale:.3f}" fill="{colour}" />'
                )
            )
            legend.append(
                (
                    f'<text class="legend-label" x="{(padding_x + swatch_size + label_gap):.3f}" '
                    f'y="{row_y:.3f}" font-size="{entry_font_size:.3f}" fill="#0f172a" '
                    f'dominant-baseline="middle">{html.escape(label)}</text>'
                )
            )
        legend.append("</g>")

        total_width = legend_x + content_width + (24.0 * scale)
        total_height = max(tree_height, legend_y + legend_height + (24.0 * scale))
        return "\n".join(legend), total_width, total_height
