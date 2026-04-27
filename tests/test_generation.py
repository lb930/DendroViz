from __future__ import annotations

import sys
import types
import unittest
from pathlib import Path
from unittest import mock

from dendroviz import DendrogramGenerator, LayoutOptions
from dendroviz.models import LineStyle, TreeLayout
from tests.helpers import write_csv_file, write_text_file


def write_sample_tree() -> Path:
    """Write a sample tree CSV used by layout tests."""
    return write_csv_file(
        [
            ["root", "", "Root", "0"],
            ["left", "root", "Left", "0"],
            ["right", "root", "Right", "1"],
            ["left_a", "left", "Left A", "0"],
            ["left_b", "left", "Left B", "1"],
            ["right_a", "right", "Right A", "0"],
        ],
        headers=["id", "parent", "label", "order"],
    )[1]


class FakeClade:
    def __init__(
        self,
        name: str | None = None,
        clades: list["FakeClade"] | None = None,
        branch_length: float | None = None,
    ) -> None:
        self.name = name
        self.clades = clades or []
        self.branch_length = branch_length


class FakeTree:
    def __init__(self, root: FakeClade) -> None:
        self.root = root


class GenerationTests(unittest.TestCase):
    def test_all_layout_and_line_combinations(self) -> None:
        """Exercise every supported layout and line-style combination."""
        generator = DendrogramGenerator()
        path = write_sample_tree()
        layouts: list[TreeLayout] = ["radial", "vertical", "horizontal"]
        line_styles: list[LineStyle] = ["curved", "split", "straight"]

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
        """Verify vertical layout maps depth onto the y axis."""
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="vertical", line_style="straight")
        depths = {node.node_id: node.depth for node in result.nodes}
        ys = {node.node_id: node.y for node in result.nodes}
        self.assertLess(ys["root"], ys["left"])
        self.assertEqual(ys["left"], depths["left"] * LayoutOptions().depth_spacing)

    def test_horizontal_layout_positions_depth_on_x_axis(self) -> None:
        """Verify horizontal layout maps depth onto the x axis."""
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="horizontal", line_style="straight")
        self.assertEqual(result.root.x, 0.0)
        left = next(node for node in result.nodes if node.node_id == "left")
        self.assertGreater(left.x, result.root.x)

    def test_radial_layout_assigns_leaf_angles(self) -> None:
        """Verify radial layout assigns angles to all leaves."""
        generator = DendrogramGenerator()
        path = write_sample_tree()
        result = generator.generate_tree(path, tree_layout="radial", line_style="curved")
        leaf_angles = [node.angle for node in result.nodes if not node.children]
        self.assertTrue(all(angle is not None for angle in leaf_angles))

    def test_custom_spacing_changes_output(self) -> None:
        """Verify custom spacing values alter node coordinates."""
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

    def test_newick_branch_lengths_control_layout_distance(self) -> None:
        """Verify Newick branch lengths drive layout spacing when provided."""
        generator = DendrogramGenerator()
        _, path = write_text_file("(Short:1,(Deep:3)Long:4)Root;", filename="tree.nwk")
        fake_tree = FakeTree(
            FakeClade(
                "Root",
                [
                    FakeClade("Short", branch_length=1.0),
                    FakeClade(
                        "Long",
                        [FakeClade("Deep", branch_length=3.0)],
                        branch_length=4.0,
                    ),
                ],
            )
        )
        fake_phylo = types.SimpleNamespace(read=mock.Mock(return_value=fake_tree))
        fake_bio = types.SimpleNamespace(Phylo=fake_phylo)

        with mock.patch.dict(sys.modules, {"Bio": fake_bio}):
            result = generator.generate_tree(
                path,
                tree_layout="vertical",
                line_style="straight",
                input_format="newick",
                options=LayoutOptions(depth_spacing=10.0, branch_length_spacing=10.0),
            )

        coords = {node.label: node.y for node in result.nodes}
        self.assertEqual(coords["Root"], 0.0)
        self.assertAlmostEqual(coords["Short"], 10.0)
        self.assertAlmostEqual(coords["Long"], 40.0)
        self.assertAlmostEqual(coords["Deep"], 70.0)

    def test_newick_without_branch_lengths_falls_back_to_depth_spacing(self) -> None:
        """Verify Newick input still uses depth spacing when lengths are absent."""
        generator = DendrogramGenerator()
        _, path = write_text_file("(Short,(Deep)Long)Root;", filename="tree.nwk")
        fake_tree = FakeTree(
            FakeClade(
                "Root",
                [
                    FakeClade("Short"),
                    FakeClade("Long", [FakeClade("Deep")]),
                ],
            )
        )
        fake_phylo = types.SimpleNamespace(read=mock.Mock(return_value=fake_tree))
        fake_bio = types.SimpleNamespace(Phylo=fake_phylo)

        with mock.patch.dict(sys.modules, {"Bio": fake_bio}):
            result = generator.generate_tree(
                path,
                tree_layout="vertical",
                line_style="straight",
                input_format="newick",
                options=LayoutOptions(depth_spacing=10.0),
            )

        coords = {node.label: node.y for node in result.nodes}
        self.assertEqual(coords["Root"], 0.0)
        self.assertEqual(coords["Short"], 10.0)
        self.assertEqual(coords["Long"], 10.0)
        self.assertEqual(coords["Deep"], 20.0)

    def test_radial_split_includes_arc_segment(self) -> None:
        """Verify split radial routing includes an arc segment."""
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
        """Verify split radial routing keeps internal children on the arc ring."""
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
        """Verify vertical split routing forks at the expected depth."""
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
        """Verify horizontal split routing forks at the expected depth."""
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
