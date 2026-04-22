from __future__ import annotations

import csv
import json
import re
import unittest
from pathlib import Path

from dendroviz import DendrogramGenerator, LayoutOptions
from dendroviz.errors import ValidationError
from tests.helpers import write_csv_file


def write_tree_csv() -> tuple[Path, Path]:
    """Write a sample tree CSV used by export tests."""
    return write_csv_file(
        [
            ["root", "", "Røot", "0"],
            ["a", "root", "Ä", "0"],
            ["b", "root", "Bee", "1"],
        ],
        headers=["id", "parent", "label", "order"],
    )


def write_deep_branch_tree_csv() -> tuple[Path, Path]:
    """Write a deeper tree used to test palette branch depth colouring."""
    return write_csv_file(
        [
            ["root", "", "Root", "0"],
            ["a", "root", "A", "0"],
            ["b", "root", "B", "1"],
            ["a1", "a", "A1", "0"],
            ["a2", "a", "A2", "1"],
            ["b1", "b", "B1", "0"],
            ["b2", "b", "B2", "1"],
            ["a1_leaf", "a1", "A1 Leaf", "0"],
            ["a2_leaf", "a2", "A2 Leaf", "0"],
            ["b1_leaf", "b1", "B1 Leaf", "0"],
            ["b2_leaf", "b2", "B2 Leaf", "0"],
        ],
        headers=["id", "parent", "label", "order"],
        filename="deep-branch-tree.csv",
    )


class ExportTests(unittest.TestCase):
    def test_writes_csv_and_svg(self) -> None:
        """Write both CSV and SVG outputs for a sample tree."""
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
            "type,group,branch_path,id,parent,child,label,index,path,x,y,size,colour,depth,tree_layout,line_style",
            csv_text,
        )
        self.assertIn("Røot", svg_text)
        self.assertIn("<circle", svg_text)

    def test_writes_json(self) -> None:
        """Write a JSON render result with nodes and edges."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_json = directory / "render.json"

        result = generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_json=output_json,
            show_labels=True,
        )

        self.assertEqual(result.output_json, output_json)
        payload = json.loads(output_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["tree_layout"], "radial")
        self.assertEqual(payload["line_style"], "split")
        self.assertTrue(payload["show_labels"])
        self.assertEqual(len(payload["nodes"]), 3)
        self.assertEqual(len(payload["edges"]), 2)
        self.assertEqual(payload["nodes"][0]["node_id"], "root")
        self.assertIn("points", payload["edges"][0])

    def test_csv_uses_layered_viz_schema(self) -> None:
        """Emit CSV rows that match the layered-viz schema."""
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
        self.assertEqual(link_row["branch_path"], "Røot|Ä")
        self.assertEqual(link_row["child"], "a")
        self.assertEqual(link_row["path"], "0")

        self.assertEqual(node_row["label"], "Ä")
        self.assertEqual(node_row["branch_path"], "Røot|Ä")
        self.assertEqual(node_row["size"], "6.0")
        self.assertEqual(node_row["depth"], "1")

    def test_svg_hides_labels_when_disabled(self) -> None:
        """Suppress SVG labels when label rendering is disabled."""
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

    def test_horizontal_svg_places_labels_outside_the_tree(self) -> None:
        """Place horizontal internal labels above their nodes."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "horizontal.svg"

        generator.generate_tree(
            input_path,
            tree_layout="horizontal",
            line_style="curved",
            output_svg=output_svg,
            show_labels=True,
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('text-anchor="middle"', svg_text)
        self.assertIn(">Røot</text>", svg_text)

    def test_horizontal_svg_leaf_labels_use_right_alignment(self) -> None:
        """Place horizontal leaf labels to the right of the nodes."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "horizontal-leaves.svg"

        generator.generate_tree(
            input_path,
            tree_layout="horizontal",
            line_style="curved",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(label_mode="leaves", show_internal_nodes=False),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertNotIn(">Røot</text>", svg_text)
        self.assertIn('text-anchor="start"', svg_text)
        self.assertNotIn('text-anchor="middle"', svg_text)

    def test_svg_can_hide_internal_nodes_and_show_leaf_labels_only(self) -> None:
        """Hide internal markers while still rendering leaf labels."""
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
        """Hide the root marker without affecting leaf markers."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "no-root.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(
                show_internal_nodes=False,
                show_root_node=False,
                label_mode="leaves",
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertEqual(svg_text.count("<circle"), 2)

    def test_svg_can_show_root_node_without_label_in_leaf_mode(self) -> None:
        """Render the root marker while suppressing its label in leaf mode."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "root-node-only.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(
                show_root_node=True,
                show_internal_nodes=True,
                label_mode="leaves",
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertEqual(svg_text.count("<circle"), 3)
        self.assertNotIn(">Røot</text>", svg_text)

    def test_svg_radial_leaf_labels_use_rotation_and_custom_colours(self) -> None:
        """Rotate radial labels and apply custom colours."""
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
                edge_colour="#ff0000",
                node_colour="#00ff00",
                label_colour="#0000ff",
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('stroke="#ff0000"', svg_text)
        self.assertIn('fill="#00ff00"', svg_text)
        self.assertIn('fill="#0000ff"', svg_text)
        self.assertIn('transform="rotate(', svg_text)

    def test_svg_palette_mode_colours_top_level_branches_automatically(self) -> None:
        """Colour top-level branches automatically in palette mode."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "palette.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(colour_mode="palette", palette="scientific", label_mode="leaves"),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('stroke="#e69f00"', svg_text)
        self.assertIn('stroke="#56b4e9"', svg_text)
        self.assertIn('fill="#e69f00"', svg_text)
        self.assertIn('fill="#56b4e9"', svg_text)

    def test_svg_palette_mode_can_render_a_legend(self) -> None:
        """Render a compact palette legend alongside the SVG."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "palette-legend.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(
                colour_mode="palette",
                palette="scientific",
                label_mode="leaves",
                show_palette_legend=True,
                show_svg_data_attributes=True,
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('id="palette-legend"', svg_text)
        self.assertIn("Palette legend", svg_text)
        self.assertIn('class="legend-swatch"', svg_text)
        self.assertIn('class="legend-label"', svg_text)
        self.assertIn('data-node-id="root"', svg_text)
        self.assertIn('data-edge-id="root-&gt;a"', svg_text)
        self.assertIn('data-branch-path="root|a"', svg_text)

    def test_svg_can_render_short_titles(self) -> None:
        """Render short hover titles for SVG nodes and edges."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "titles.svg"

        generator.generate_tree(
            input_path,
            tree_layout="vertical",
            line_style="straight",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(show_svg_titles=True),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertGreaterEqual(svg_text.count("<title>Røot</title>"), 2)
        self.assertIn("<title>Røot → Ä</title>", svg_text)

    def test_svg_palette_mode_can_colour_deeper_branches(self) -> None:
        """Colour a deeper branch level instead of only root children."""
        generator = DendrogramGenerator()
        directory, input_path = write_deep_branch_tree_csv()
        output_svg = directory / "palette-depth.svg"

        generator.generate_tree(
            input_path,
            tree_layout="vertical",
            line_style="straight",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(
                colour_mode="palette",
                palette="set1",
                palette_depth=2,
                label_mode="leaves",
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('stroke="#e41a1c"', svg_text)
        self.assertIn('stroke="#377eb8"', svg_text)
        self.assertIn('stroke="#4daf4a"', svg_text)
        self.assertIn('stroke="#984ea3"', svg_text)
        self.assertIn('fill="#e41a1c"', svg_text)
        self.assertIn('fill="#377eb8"', svg_text)
        self.assertIn('fill="#4daf4a"', svg_text)
        self.assertIn('fill="#984ea3"', svg_text)

    def test_svg_accepts_custom_palette_sequences(self) -> None:
        """Accept a custom palette sequence and cycle it across branches."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "custom-palette.svg"

        generator.generate_tree(
            input_path,
            tree_layout="radial",
            line_style="split",
            output_svg=output_svg,
            show_labels=True,
            options=LayoutOptions(
                colour_mode="palette",
                palette=["#112233", "#445566"],
                label_mode="leaves",
            ),
        )

        svg_text = output_svg.read_text(encoding="utf-8")
        self.assertIn('stroke="#112233"', svg_text)
        self.assertIn('stroke="#445566"', svg_text)
        self.assertIn('fill="#112233"', svg_text)
        self.assertIn('fill="#445566"', svg_text)

    def test_svg_rejects_invalid_palette_colours(self) -> None:
        """Reject invalid custom palette colours before exporting."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "invalid-palette.svg"

        with self.assertRaises(ValidationError):
            generator.generate_tree(
                input_path,
                tree_layout="radial",
                line_style="split",
                output_svg=output_svg,
                show_labels=True,
                options=LayoutOptions(
                    colour_mode="palette",
                    palette=["#112233", "not-a-colour"],
                    label_mode="leaves",
                ),
            )

    def test_svg_rejects_non_positive_font_size(self) -> None:
        """Reject non-positive font sizes before exporting."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "invalid-font-size.svg"

        with self.assertRaises(ValueError):
            generator.generate_tree(
                input_path,
                tree_layout="radial",
                line_style="split",
                output_svg=output_svg,
                show_labels=True,
                options=LayoutOptions(font_size=0),
            )

    def test_svg_rejects_negative_label_offset(self) -> None:
        """Reject negative label offsets before exporting."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "invalid-label-offset.svg"

        with self.assertRaises(ValueError):
            generator.generate_tree(
                input_path,
                tree_layout="radial",
                line_style="split",
                output_svg=output_svg,
                show_labels=True,
                options=LayoutOptions(label_offset=-1.0),
            )

    def test_svg_rejects_non_positive_radial_sweep(self) -> None:
        """Reject non-positive radial sweep values before exporting."""
        generator = DendrogramGenerator()
        directory, input_path = write_tree_csv()
        output_svg = directory / "invalid-radial-sweep.svg"

        with self.assertRaises(ValueError):
            generator.generate_tree(
                input_path,
                tree_layout="radial",
                line_style="split",
                output_svg=output_svg,
                show_labels=True,
                options=LayoutOptions(radial_sweep_deg=0.0),
            )

    def test_svg_expands_canvas_for_large_labels(self) -> None:
        """Expand the SVG canvas when labels need more room."""
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
            options=LayoutOptions(
                label_mode="leaves",
                label_orientation="auto",
                label_offset=36,
                font_size=20,
            ),
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
        """Scale the SVG canvas and font sizes together."""
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
            options=LayoutOptions(
                label_mode="leaves",
                label_orientation="auto",
                svg_scale=2.0,
            ),
        )

        plain_text = plain_svg.read_text(encoding="utf-8")
        scaled_text = scaled_svg.read_text(encoding="utf-8")
        plain_width = float(re.search(r'width="([0-9.]+)"', plain_text).group(1))
        scaled_width = float(re.search(r'width="([0-9.]+)"', scaled_text).group(1))

        self.assertGreater(scaled_width, plain_width * 1.9)
        self.assertIn("stroke-width: 4.000", scaled_text)
        self.assertIn('font-size="24.000"', scaled_text)
