from __future__ import annotations

import csv
import re
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from dendroviz import DendrogramGenerator, LayoutOptions


def write_tree_csv() -> tuple[Path, Path]:
    directory = Path(tempfile.mkdtemp())
    input_path = directory / "tree.csv"
    with input_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.writer(handle)
        writer.writerow(["id", "parent", "label", "order"])
        writer.writerow(["root", "", "Røot", "0"])
        writer.writerow(["a", "root", "Ä", "0"])
        writer.writerow(["b", "root", "Bee", "1"])
    return directory, input_path


class ExportTests(unittest.TestCase):
    def test_writes_csv_and_svg(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_csv = directory / "render.csv"
        output_svg = directory / "render.svg"

        result = generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_csv=output_csv,
            output_svg=output_svg,
            show_labels=True,
        )

        self.assertEqual(result.output_csv, output_csv)
        self.assertEqual(result.output_svg, output_svg)
        self.assertTrue(output_csv.exists())
        self.assertTrue(output_svg.exists())
        csv_text = output_csv.read_text(encoding="utf-8")
        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn(
            "type,group,id,parent,child,label,index,path,x,y,size,color,depth,tree_layout,line_style",
            csv_text,
        )
        self.assertIn("Røot", svg_text)
        self.assertIn("<circle", svg_text)

    def test_csv_uses_layered_viz_schema(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_csv = directory / "render.csv"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_csv=output_csv,
        )

        with output_csv.open("r", encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))

        link_row = next(row for row in rows if row["type"] == "link")
        node_row = next(row for row in rows if row["type"] == "node" and row["id"] == "a")

        self.assertEqual(link_row["group"], "Ä")
        self.assertEqual(link_row["child"], "a")
        self.assertEqual(link_row["path"], "0")

        self.assertEqual(node_row["label"], "Ä")
        self.assertEqual(node_row["size"], "6.0")
        self.assertEqual(node_row["depth"], "1")

    def test_svg_hides_labels_when_disabled(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "render.svg"

        generator.generate_tree(
            input_path,
            tree_layout="horizontal",
            line_style="curved",
            output_svg=output_svg,
            show_labels=False,
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertNotIn("Røot</text>", svg_text)
        self.assertIn("<path", svg_text)

    def test_svg_can_hide_internal_nodes_and_show_leaf_labels_only(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "leaf-only.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(show_internal_nodes=False, label_mode="leaves"),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertNotIn(">Røot</text>", svg_text)
        self.assertIn(">Ä</text>", svg_text)
        self.assertEqual(svg_text.count("<circle"), 3)

    def test_svg_can_hide_root_node_separately(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "no-root.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(show_internal_nodes=False, show_root_node=False, label_mode="leaves"),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertEqual(svg_text.count("<circle"), 2)

    def test_svg_radial_leaf_labels_use_rotation_and_custom_colors(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "styled.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="curved",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(
                label_mode="leaves",
                label_orientation="auto",
                edge_color="#ff0000",
                node_color="#00ff00",
                label_color="#0000ff",
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('stroke="#ff0000"', svg_text)
        self.assertIn('fill="#00ff00"', svg_text)
        self.assertIn('fill="#0000ff"', svg_text)
        self.assertIn('transform="rotate(', svg_text)

    def test_svg_palette_mode_colors_top_level_branches_automatically(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "palette.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(color_mode="palette", palette="scientific", label_mode="leaves"),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('stroke="#0072b2"', svg_text)
        self.assertIn('stroke="#d55e00"', svg_text)
        self.assertIn('fill="#0072b2"', svg_text)
        self.assertIn('fill="#d55e00"', svg_text)

    def test_svg_expands_canvas_for_large_labels(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        plain_svg = directory / "plain.svg"
        labeled_svg = directory / "labeled.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="curved",
            output_svg=plain_svg,
            show_labels=False,
        )
        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="curved",
            output_svg=labeled_svg,
            show_labels=True,
            options=LayoutOptions(label_mode="leaves", label_orientation="auto", label_offset=36, font_size=20),
        )

        plain_text = plain_svg.read_text(encoding="utf-8")
        labeled_text = labeled_svg.read_text(encoding="utf-8")
        plain_width = float(re.search(r'width="([0-9.]+)"', plain_text).group(1))
        labeled_width = float(re.search(r'width="([0-9.]+)"', labeled_text).group(1))
        plain_height = float(re.search(r'height="([0-9.]+)"', plain_text).group(1))
        labeled_height = float(re.search(r'height="([0-9.]+)"', labeled_text).group(1))

        self.assertGreater(labeled_width, plain_width)
        self.assertGreater(labeled_height, plain_height)

    def test_svg_scale_increases_canvas_and_font_size(self) -> None:
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        plain_svg = directory / "plain.svg"
        scaled_svg = directory / "scaled.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=plain_svg,
            show_labels=True,
            options=LayoutOptions(label_mode="leaves", label_orientation="auto"),
        )
        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=scaled_svg,
            show_labels=True,
            options=LayoutOptions(label_mode="leaves", label_orientation="auto", svg_scale=2.0),
        )

        plain_text = plain_svg.read_text(encoding="utf-8")
        scaled_text = scaled_svg.read_text(encoding="utf-8")
        plain_width = float(re.search(r'width="([0-9.]+)"', plain_text).group(1))
        scaled_width = float(re.search(r'width="([0-9.]+)"', scaled_text).group(1))

        self.assertGreater(scaled_width, plain_width * 1.9)
        self.assertIn('stroke-width: 4.000', scaled_text)
        self.assertIn('font-size="24.000"', scaled_text)
