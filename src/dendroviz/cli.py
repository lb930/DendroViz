from __future__ import annotations

import argparse
import sys

from .api import DendrogramGenerator
from .errors import DendrogramError
from .models import LayoutOptions


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="dendroviz", description="Build dendrogram CSV and SVG output."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build", help="Generate dendrogram artifacts from an input tree."
    )
    build_parser.add_argument("input_path", help="Path to the input tree file.")
    build_parser.add_argument("--input-format", choices=["csv", "newick"], default="csv")
    build_parser.add_argument(
        "--tree-layout", choices=["radial", "vertical", "horizontal"], required=True
    )
    build_parser.add_argument(
        "--line-style", choices=["curved", "split", "straight"], required=True
    )
    build_parser.add_argument("--output-csv", help="Path to write the render-ready CSV.")
    build_parser.add_argument("--output-svg", help="Path to write the SVG output.")
    build_parser.add_argument(
        "--show-labels", action="store_true", help="Show labels in SVG output."
    )
    build_parser.add_argument("--label-mode", choices=["all", "leaves", "none"], default="all")
    build_parser.add_argument(
        "--hide-internal-nodes",
        action="store_true",
        help="Hide non-leaf node markers in SVG output.",
    )
    build_parser.add_argument(
        "--hide-root-node", action="store_true", help="Hide the root node marker in SVG output."
    )
    build_parser.add_argument("--label-orientation", choices=["horizontal", "auto"], default="auto")
    build_parser.add_argument("--label-offset", type=float, default=18.0)
    build_parser.add_argument("--scale", type=float, default=1.0, help="Scale the SVG output size.")
    build_parser.add_argument("--font-size", type=int, default=12)
    build_parser.add_argument("--color-mode", choices=["global", "palette"], default="global")
    build_parser.add_argument(
        "--palette",
        choices=["default", "pastel", "high_contrast", "earth", "scientific"],
        default="default",
    )
    build_parser.add_argument("--node-color", default="#0f172a")
    build_parser.add_argument("--edge-color", default="#334155")
    build_parser.add_argument("--label-color", default="#111827")
    build_parser.add_argument("--depth-spacing", type=float, default=160.0)
    build_parser.add_argument("--sibling-spacing", type=float, default=90.0)
    build_parser.add_argument("--curve-points", type=int, default=60)
    build_parser.add_argument("--straight-points", type=int, default=24)
    build_parser.add_argument("--radial-base-angle-deg", type=float, default=-90.0)
    build_parser.add_argument("--radial-sweep-deg", type=float, default=360.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    generator = DendrogramGenerator()

    if args.command != "build":
        parser.error("Unsupported command.")

    if args.output_csv is None and args.output_svg is None:
        parser.error("At least one of --output-csv or --output-svg must be provided.")

    options = LayoutOptions(
        depth_spacing=args.depth_spacing,
        sibling_spacing=args.sibling_spacing,
        curve_points=args.curve_points,
        straight_points=args.straight_points,
        radial_base_angle_deg=args.radial_base_angle_deg,
        radial_sweep_deg=args.radial_sweep_deg,
        show_internal_nodes=not args.hide_internal_nodes,
        show_root_node=not args.hide_root_node,
        label_mode=args.label_mode,
        label_orientation=args.label_orientation,
        label_offset=args.label_offset,
        svg_scale=args.scale,
        font_size=args.font_size,
        color_mode=args.color_mode,
        palette=args.palette,
        node_color=args.node_color,
        edge_color=args.edge_color,
        label_color=args.label_color,
    )

    try:
        result = generator.generate_tree(
            args.input_path,
            tree_layout=args.tree_layout,
            line_style=args.line_style,
            input_format=args.input_format,
            output_csv=args.output_csv,
            output_svg=args.output_svg,
            show_labels=args.show_labels,
            options=options,
        )
    except (DendrogramError, ImportError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2

    print(
        f"Generated {len(result.nodes)} nodes and {len(result.edges)} edges "
        f"using {result.tree_layout}/{result.line_style}."
    )
    if result.output_csv is not None:
        print(f"CSV: {result.output_csv}")
    if result.output_svg is not None:
        print(f"SVG: {result.output_svg}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
