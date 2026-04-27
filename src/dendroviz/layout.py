from __future__ import annotations

import logging
import math

from .models import LayoutOptions, TreeLayout, TreeModel, TreeNode

logger = logging.getLogger(__name__)


class TreeLayouter:
    def __init__(self, options: LayoutOptions) -> None:
        """Create a layouter with the given layout options."""
        self.options = options

    def apply(self, tree: TreeModel, tree_layout: TreeLayout) -> list[TreeNode]:
        """Apply the requested layout to a tree."""
        logger.info("Applying %s layout to %d nodes", tree_layout, len(tree.nodes))
        if tree_layout == "radial":
            return self._apply_radial(tree)
        if tree_layout == "vertical":
            return self._apply_vertical(tree)
        return self._apply_horizontal(tree)

    def _apply_vertical(self, tree: TreeModel) -> list[TreeNode]:
        """Assign vertical layout coordinates."""
        self._assign_leaf_positions(tree)
        for node in tree.nodes:
            node.x = node.leaf_index * self.options.sibling_spacing
            node.y = self._distance_to_axis(node)
            node.angle = None
            node.radius = None
        return tree.nodes

    def _apply_horizontal(self, tree: TreeModel) -> list[TreeNode]:
        """Assign horizontal layout coordinates."""
        self._assign_leaf_positions(tree)
        for node in tree.nodes:
            node.x = self._distance_to_axis(node)
            node.y = node.leaf_index * self.options.sibling_spacing
            node.angle = None
            node.radius = None
        return tree.nodes

    def _apply_radial(self, tree: TreeModel) -> list[TreeNode]:
        """Assign radial layout coordinates."""
        leaves = tree.leaves()
        leaf_count = max(len(leaves), 1)
        base_angle = math.radians(self.options.radial_base_angle_deg)
        sweep = math.radians(self.options.radial_sweep_deg)

        for index, leaf in enumerate(leaves):
            leaf.leaf_index = float(index)
            leaf.angle = base_angle + sweep * self._leaf_fraction(index, leaf_count, sweep)

        self._assign_internal_angles(tree.root)

        for node in tree.nodes:
            radius = self._distance_to_axis(node)
            angle = node.angle if node.angle is not None else 0.0
            node.radius = radius
            node.x = radius * math.cos(angle)
            node.y = radius * math.sin(angle)
        logger.debug("Assigned radial coordinates to %d nodes", len(tree.nodes))
        return tree.nodes

    def _distance_to_axis(self, node: TreeNode) -> float:
        """Convert a node's tree distance into layout coordinates."""
        if node.distance is not None:
            return node.distance * self.options.branch_length_spacing
        return node.depth * self.options.depth_spacing

    def _assign_leaf_positions(self, tree: TreeModel) -> None:
        """Assign leaf indices before propagating them upward."""
        for index, leaf in enumerate(tree.leaves()):
            leaf.leaf_index = float(index)
        self._assign_internal_leaf_index(tree.root)

    def _assign_internal_leaf_index(self, node: TreeNode) -> float:
        """Compute a node's leaf index from its descendants."""
        if node.is_leaf:
            return node.leaf_index
        child_positions = [self._assign_internal_leaf_index(child) for child in node.children]
        node.leaf_index = sum(child_positions) / len(child_positions)
        return node.leaf_index

    def _assign_internal_angles(self, node: TreeNode) -> float:
        """Compute a node's radial angle from its descendants."""
        if node.is_leaf:
            if node.angle is None:
                raise ValueError("Leaf nodes must have an angle before radial layout is finalized.")
            return node.angle
        child_angles = [self._assign_internal_angles(child) for child in node.children]
        node.angle = self._circular_mean(child_angles)
        node.leaf_index = sum(child.leaf_index for child in node.children) / len(node.children)
        return node.angle

    def _leaf_fraction(self, index: int, leaf_count: int, sweep: float) -> float:
        """Return the normalised position for a leaf within the sweep."""
        if leaf_count == 1:
            return 0.0
        if math.isclose(abs(sweep), math.tau):
            return index / leaf_count
        return index / (leaf_count - 1)

    def _circular_mean(self, angles: list[float]) -> float:
        """Compute the circular mean for a list of angles."""
        sin_sum = sum(math.sin(angle) for angle in angles)
        cos_sum = sum(math.cos(angle) for angle in angles)
        return math.atan2(sin_sum, cos_sum)
