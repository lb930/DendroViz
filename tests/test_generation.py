from __future__ import annotations

import csv
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dendroviz import DendrogramGenerator, LayoutOptions


def write_sample_tree() -> Path:
    directory = Path(tempfile.mkdtemp())
    path = directory / "tree.csv"
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "parent", "label", "order"])
        writer.writerow(["root", "", "Root", "0"])
        writer.writerow(["left", "root", "Left", "0"])
        writer.writerow(["right", "root", "Right", "1"])
        writer.writerow(["left_a", "left", "Left A", "0"])
        writer.writerow(["left_b", "left", "Left B", "1"])
        writer.writerow(["right_a", "right", "Right A", "0"])
    return path


class GenerationTests(unittest.TestCase):
    def test_all_layout_and_line_combinations(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        layouts = ["radial", "vertical", "horizontal"]
        line_styles = ["curved", "split", "straight"]

        for layout in layouts:
            for line_style in line_styles:
                with self.subTest(layout=layout, line_style=line_style):
                    result = generator.generate_tree(
                        path, tree_layout=layout, line_style=line_style
                    )
                    self.assertEqual(len(result.nodes), 6)
                    self.assertEqual(len(result.edges), 5)
                    self.assertTrue(result.csv_rows)
                    self.assertEqual(result.nodes[0].node_id, "root")

    def test_vertical_layout_positions_depth_on_y_axis(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="vertical", line_style="straight")
        depths = {node.node_id: node.depth for node in result.nodes}
        ys = {node.node_id: node.y for node in result.nodes}
        self.assertLess(ys["root"], ys["left"])
        self.assertEqual(ys["left"], depths["left"] * LayoutOptions().depth_spacing)

    def test_horizontal_layout_positions_depth_on_x_axis(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="horizontal", line_style="straight")
        self.assertEqual(result.root.x, 0.0)
        left = next(node for node in result.nodes if node.node_id == "left")
        self.assertGreater(left.x, result.root.x)

    def test_radial_layout_assigns_leaf_angles(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="radial", line_style="curved")
        leaf_angles = [node.angle for node in result.nodes if not node.children]
        self.assertTrue(all(angle is not None for angle in leaf_angles))

    def test_custom_spacing_changes_output(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        default_result = generator.generate_tree(
            path, tree_layout="vertical", line_style="straight"
        )
        custom_result = generator.generate_tree(
            path,
            tree_layout="vertical",
            line_style="straight",
            options=LayoutOptions(depth_spacing=200.0, sibling_spacing=120.0),
        )
        self.assertNotEqual(
            [(node.x, node.y) for node in default_result.nodes],
            [(node.x, node.y) for node in custom_result.nodes],
        )

    def test_radial_split_includes_arc_segment(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="radial", line_style="split")
        edge = next(edge for edge in result.edges if edge.edge_id == "left->left_b")
        child = next(node for node in result.nodes if node.node_id == "left_b")
        parent = next(node for node in result.nodes if node.node_id == "left")

        self.assertAlmostEqual(edge.points[0][0], parent.x)
        self.assertAlmostEqual(edge.points[0][1], parent.y)
        self.assertAlmostEqual(edge.points[-1][0], child.x)
        self.assertAlmostEqual(edge.points[-1][1], child.y)

        radii = [round((x**2 + y**2) ** 0.5, 3) for x, y in edge.points]
        child_radius = round((child.x**2 + child.y**2) ** 0.5, 3)
        split_radius = round((((parent.x**2 + parent.y**2) ** 0.5) + child_radius) / 2.0, 3)
        self.assertGreater(radii.count(split_radius), 3)
        self.assertEqual(radii[-1], child_radius)

    def test_radial_split_places_internal_child_on_arc_ring(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="radial", line_style="split")
        edge = next(edge for edge in result.edges if edge.edge_id == "root->left")
        child = next(node for node in result.nodes if node.node_id == "left")
        child_radius = round((child.x**2 + child.y**2) ** 0.5, 3)
        radii = [round((x**2 + y**2) ** 0.5, 3) for x, y in edge.points]

        self.assertGreater(radii.count(child_radius), 3)
        self.assertAlmostEqual(edge.points[-1][0], child.x)
        self.assertAlmostEqual(edge.points[-1][1], child.y)

    def test_vertical_split_places_internal_node_at_branch_fork(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="vertical", line_style="split")
        edge = next(edge for edge in result.edges if edge.edge_id == "root->left")
        child = next(node for node in result.nodes if node.node_id == "left")

        self.assertAlmostEqual(edge.points[-1][0], child.x)
        self.assertAlmostEqual(edge.points[-1][1], child.y)
        branch_y = round(
            result.root.y + (LayoutOptions().depth_spacing * LayoutOptions().root_fork_fraction), 3
        )
        self.assertGreater(sum(1 for _, y in edge.points if round(y, 3) == branch_y), 3)

    def test_horizontal_split_places_internal_node_at_branch_fork(self) -> None:
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="horizontal", line_style="split")
        edge = next(edge for edge in result.edges if edge.edge_id == "root->left")
        child = next(node for node in result.nodes if node.node_id == "left")

        self.assertAlmostEqual(edge.points[-1][0], child.x)
        self.assertAlmostEqual(edge.points[-1][1], child.y)
        branch_x = round(
            result.root.x + (LayoutOptions().depth_spacing * LayoutOptions().root_fork_fraction), 3
        )
        self.assertGreater(sum(1 for x, _ in edge.points if round(x, 3) == branch_x), 3)
