from __future__ import annotations

import math

from .models import EdgePath, LayoutOptions, LineStyle, TreeLayout, TreeModel, TreeNode


class EdgeRouter:
    def __init__(self, options: LayoutOptions) -> None:
        self.options = options

    def build_paths(
        self,
        tree: TreeModel,
        tree_layout: TreeLayout,
        line_style: LineStyle,
    ) -> list[EdgePath]:
        edges: list[EdgePath] = []
        for parent, child in tree.iter_edges():
            edges.append(
                EdgePath(
                    edge_id=f"{parent.node_id}->{child.node_id}",
                    source_id=parent.node_id,
                    target_id=child.node_id,
                    points=self._route_points(parent, child, tree_layout, line_style),
                )
            )
        return edges

    def _route_points(
        self,
        parent: TreeNode,
        child: TreeNode,
        tree_layout: TreeLayout,
        line_style: LineStyle,
    ) -> list[tuple[float, float]]:
        if line_style == "straight":
            return self._interpolate_line(parent.position, child.position, self.options.straight_points)
        if line_style == "split":
            return self._route_split(parent, child, tree_layout)
        return self._route_curved(parent, child, tree_layout)

    def _route_split(
        self,
        parent: TreeNode,
        child: TreeNode,
        tree_layout: TreeLayout,
    ) -> list[tuple[float, float]]:
        if tree_layout == "radial":
            parent_angle, parent_radius = parent.polar_position
            child_angle, child_radius = child.polar_position
            split_radius = child_radius if child.children else (parent_radius + child_radius) / 2.0
            radial_leg = self._interpolate_line(
                self._polar_to_xy(parent_angle, parent_radius),
                self._polar_to_xy(parent_angle, split_radius),
                self.options.straight_points,
            )
            arc_leg = self._sample_arc(
                radius=split_radius,
                start_angle=parent_angle,
                end_angle=child_angle,
                samples=self.options.curve_points,
            )
            if child.children:
                return self._merge_segments([radial_leg, arc_leg])
            leaf_leg = self._interpolate_line(
                self._polar_to_xy(child_angle, split_radius),
                self._polar_to_xy(child_angle, child_radius),
                self.options.straight_points,
            )
            return self._merge_segments([radial_leg, arc_leg, leaf_leg])

        if tree_layout == "vertical":
            if parent.parent_id is None:
                branch_y = parent.y + (self.options.depth_spacing * self.options.root_fork_fraction)
                split_points = [
                    parent.position,
                    (parent.x, branch_y),
                    (child.x, branch_y),
                    child.position,
                ]
                return self._densify_polyline(split_points, self.options.straight_points)
            split_points = [
                parent.position,
                (child.x, parent.y),
                child.position,
            ]
        else:
            if parent.parent_id is None:
                branch_x = parent.x + (self.options.depth_spacing * self.options.root_fork_fraction)
                split_points = [
                    parent.position,
                    (branch_x, parent.y),
                    (branch_x, child.y),
                    child.position,
                ]
                return self._densify_polyline(split_points, self.options.straight_points)
            split_points = [
                parent.position,
                (parent.x, child.y),
                child.position,
            ]
        return self._densify_polyline(split_points, self.options.straight_points)

    def _route_curved(
        self,
        parent: TreeNode,
        child: TreeNode,
        tree_layout: TreeLayout,
    ) -> list[tuple[float, float]]:
        if tree_layout == "radial":
            parent_angle, parent_radius = parent.polar_position
            child_angle, child_radius = child.polar_position
            mid_radius = (parent_radius + child_radius) / 2.0
            p0 = parent.position
            p3 = child.position
            if parent.parent_id is None:
                delta = self._shortest_angle_delta(parent_angle, child_angle)
                p1 = self._polar_to_xy(parent_angle + 0.18 * delta, mid_radius * 0.45)
                p2 = self._polar_to_xy(child_angle - 0.10 * delta, mid_radius)
            else:
                p1 = self._polar_to_xy(parent_angle, mid_radius)
                p2 = self._polar_to_xy(child_angle, mid_radius)
            return self._sample_cubic_bezier(p0, p1, p2, p3, self.options.curve_points)

        midpoint = (parent.y + child.y) / 2.0 if tree_layout == "vertical" else (parent.x + child.x) / 2.0
        p0 = parent.position
        p3 = child.position
        if tree_layout == "vertical":
            p1 = (parent.x, midpoint)
            p2 = (child.x, midpoint)
        else:
            p1 = (midpoint, parent.y)
            p2 = (midpoint, child.y)
        return self._sample_cubic_bezier(p0, p1, p2, p3, self.options.curve_points)

    def _sample_cubic_bezier(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        samples: int,
    ) -> list[tuple[float, float]]:
        return [self._bezier_point(p0, p1, p2, p3, index / (samples - 1)) for index in range(samples)]

    def _bezier_point(
        self,
        p0: tuple[float, float],
        p1: tuple[float, float],
        p2: tuple[float, float],
        p3: tuple[float, float],
        t: float,
    ) -> tuple[float, float]:
        inv = 1.0 - t
        x = (
            (inv**3) * p0[0]
            + 3 * (inv**2) * t * p1[0]
            + 3 * inv * (t**2) * p2[0]
            + (t**3) * p3[0]
        )
        y = (
            (inv**3) * p0[1]
            + 3 * (inv**2) * t * p1[1]
            + 3 * inv * (t**2) * p2[1]
            + (t**3) * p3[1]
        )
        return (x, y)

    def _interpolate_line(
        self,
        start: tuple[float, float],
        end: tuple[float, float],
        samples: int,
    ) -> list[tuple[float, float]]:
        return [
            (
                start[0] + (end[0] - start[0]) * (index / (samples - 1)),
                start[1] + (end[1] - start[1]) * (index / (samples - 1)),
            )
            for index in range(samples)
        ]

    def _densify_polyline(
        self,
        points: list[tuple[float, float]],
        samples_per_segment: int,
    ) -> list[tuple[float, float]]:
        densified: list[tuple[float, float]] = []
        for segment_index in range(len(points) - 1):
            segment = self._interpolate_line(points[segment_index], points[segment_index + 1], samples_per_segment)
            if segment_index:
                segment = segment[1:]
            densified.extend(segment)
        return densified

    def _sample_arc(
        self,
        *,
        radius: float,
        start_angle: float,
        end_angle: float,
        samples: int,
    ) -> list[tuple[float, float]]:
        if samples < 2:
            return [self._polar_to_xy(end_angle, radius)]
        delta = self._shortest_angle_delta(start_angle, end_angle)
        return [
            self._polar_to_xy(start_angle + delta * (index / (samples - 1)), radius)
            for index in range(samples)
        ]

    def _merge_segments(self, segments: list[list[tuple[float, float]]]) -> list[tuple[float, float]]:
        merged: list[tuple[float, float]] = []
        for index, segment in enumerate(segments):
            if index and segment:
                merged.extend(segment[1:])
            else:
                merged.extend(segment)
        return merged

    def _polar_to_xy(self, angle: float, radius: float) -> tuple[float, float]:
        return (radius * math.cos(angle), radius * math.sin(angle))

    def _shortest_angle_delta(self, start: float, end: float) -> float:
        return math.atan2(math.sin(end - start), math.cos(end - start))
