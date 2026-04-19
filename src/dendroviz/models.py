from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterator, Literal

TreeLayout = Literal["radial", "vertical", "horizontal"]
LineStyle = Literal["curved", "split", "straight"]
InputFormat = Literal["csv", "newick", "json"]
LabelMode = Literal["all", "leaves", "none"]
LabelOrientation = Literal["horizontal", "auto"]
ColorMode = Literal["global", "palette"]
PaletteName = Literal[
    "set1",
    "set2",
    "set3",
    "pastel1",
    "pastel2",
    "accent",
    "paired",
    "tableau",
    "dark2",
    "scientific",
]


@dataclass(slots=True)
class InputNode:
    node_id: str
    parent_id: str | None
    label: str
    order: float


@dataclass(slots=True)
class TreeNode:
    node_id: str
    parent_id: str | None
    label: str
    order: float
    depth: int = 0
    children: list["TreeNode"] = field(default_factory=list)
    x: float = 0.0
    y: float = 0.0
    angle: float | None = None
    radius: float | None = None
    leaf_index: float = 0.0

    @property
    def is_leaf(self) -> bool:
        """Return whether the node has no children."""
        return not self.children

    @property
    def position(self) -> tuple[float, float]:
        """Return the node's Cartesian position."""
        return (self.x, self.y)

    @property
    def polar_position(self) -> tuple[float, float]:
        """Return the node's polar coordinates."""
        if self.angle is None or self.radius is None:
            raise ValueError("Node does not have radial coordinates.")
        return (self.angle, self.radius)

    def add_child(self, child: "TreeNode") -> None:
        """Append a child node."""
        self.children.append(child)

    def sort_children(self) -> None:
        """Sort children by order, label, and node id."""
        self.children.sort(key=lambda child: (child.order, child.label, child.node_id))

    def iter_preorder(self) -> Iterator["TreeNode"]:
        """Yield the node and its descendants in preorder."""
        yield self
        for child in self.children:
            yield from child.iter_preorder()


@dataclass(slots=True)
class TreeModel:
    root: TreeNode
    nodes: list[TreeNode]
    node_map: dict[str, TreeNode]

    def iter_edges(self) -> Iterator[tuple[TreeNode, TreeNode]]:
        """Yield parent-child pairs for each edge in the tree."""
        for node in self.nodes:
            if node.parent_id is None:
                continue
            yield self.node_map[node.parent_id], node

    def leaves(self) -> list[TreeNode]:
        """Return all leaf nodes in tree order."""
        return [node for node in self.nodes if node.is_leaf]

    def top_level_branch(self, node: TreeNode) -> TreeNode | None:
        """Return the branch root for the given node, or None for the tree root."""
        if node.parent_id is None:
            return None
        current = node
        while (
            current.parent_id is not None and self.node_map[current.parent_id].parent_id is not None
        ):
            current = self.node_map[current.parent_id]
        return current

    def path_to_node(self, node: TreeNode) -> list[TreeNode]:
        """Return the path from the tree root to the given node."""
        path: list[TreeNode] = []
        current: TreeNode | None = node
        while current is not None:
            path.append(current)
            current = self.node_map[current.parent_id] if current.parent_id is not None else None
        path.reverse()
        return path


@dataclass(slots=True)
class EdgePath:
    edge_id: str
    source_id: str
    target_id: str
    points: list[tuple[float, float]]


@dataclass(slots=True)
class LayoutOptions:
    depth_spacing: float = 160.0
    sibling_spacing: float = 90.0
    radial_base_angle_deg: float = -90.0
    radial_sweep_deg: float = 360.0
    curve_points: int = 60
    straight_points: int = 24
    node_radius: float = 6.0
    margin: float = 32.0
    svg_scale: float = 1.0
    font_size: int = 12
    root_fork_fraction: float = 0.35
    show_internal_nodes: bool = True
    show_root_node: bool = True
    label_mode: LabelMode = "all"
    label_orientation: LabelOrientation = "auto"
    label_offset: float = 18.0
    color_mode: ColorMode = "global"
    palette: PaletteName = "set1"
    edge_color: str = "#334155"
    node_color: str = "#0f172a"
    label_color: str = "#111827"


@dataclass(slots=True)
class RenderResult:
    tree: TreeModel
    edges: list[EdgePath]
    csv_rows: list[dict[str, str | float | int]]
    tree_layout: TreeLayout
    line_style: LineStyle
    output_csv: Path | None = None
    output_svg: Path | None = None
    output_json: Path | None = None

    @property
    def root(self) -> TreeNode:
        """Return the tree root."""
        return self.tree.root

    @property
    def nodes(self) -> list[TreeNode]:
        """Return the ordered tree nodes."""
        return self.tree.nodes
