from __future__ import annotations

import argparse
import logging
import sys

from .api import DendrogramGenerator
from .errors import DendrogramError
from .models import LayoutOptions

logger = logging.getLogger("dendroviz.cli")


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line argument parser."""
    parser = argparse.ArgumentParser(
        prog="dendroviz", description="Build dendrogram CSV and SVG output."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    build_parser = subparsers.add_parser(
        "build", help="Generate dendrogram artefacts from an input tree."
    )
    build_parser.add_argument("input_path", help="Path to the input tree file.")
    build_parser.add_argument("--input-format", choices=["csv", "newick", "json"], default="csv")
    build_parser.add_argument(
        "--tree-layout", choices=["radial", "vertical", "horizontal"], required=True
    )
    build_parser.add_argument(
        "--line-style", choices=["curved", "split", "straight"], required=True
    )
    build_parser.add_argument("--output-csv", help="Path to write the render-ready CSV.")
    build_parser.add_argument("--output-json", help="Path to write the rendered JSON output.")
    build_parser.add_argument("--output-svg", help="Path to write the SVG output.")
    build_parser.add_argument(
        "--log-level",
        choices=["CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"],
        default="WARNING",
        help="Set the logging verbosity for the command.",
    )
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
    build_parser.add_argument("--colour-mode", choices=["global", "palette"], default="global")
    build_parser.add_argument(
        "--palette",
        default="set1",
        help="Palette name or comma-separated hex colours, for example set1 or #112233,#445566.",
    )
    build_parser.add_argument(
        "--palette-depth",
        type=int,
        default=1,
        help="Tree depth to colour when palette mode is enabled.",
    )
    build_parser.add_argument(
        "--show-palette-legend",
        action="store_true",
        help="Render a small legend in SVG output when palette mode is active.",
    )
    build_parser.add_argument(
        "--show-svg-data-attributes",
        action="store_true",
        help="Add data-* metadata attributes to SVG elements for browser interactivity.",
    )
    build_parser.add_argument(
        "--show-svg-titles",
        action="store_true",
        help="Add short hover titles to SVG elements.",
    )
    build_parser.add_argument(
        "--svg-title-parts",
        default="label",
        help="Comma-separated tooltip parts for SVG nodes, for example label or label,group.",
    )
    build_parser.add_argument(
        "--svg-title-template",
        help="Tooltip template for SVG nodes, for example 'Family: {group}\\nLanguage: {label}'.",
    )
    build_parser.add_argument("--node-colour", default="#0f172a")
    build_parser.add_argument("--edge-colour", default="#334155")
    build_parser.add_argument("--label-colour", default="#111827")
    build_parser.add_argument("--depth-spacing", type=float, default=160.0)
    build_parser.add_argument("--sibling-spacing", type=float, default=90.0)
    build_parser.add_argument("--curve-points", type=int, default=60)
    build_parser.add_argument("--straight-points", type=int, default=24)
    build_parser.add_argument("--radial-base-angle-deg", type=float, default=-90.0)
    build_parser.add_argument("--radial-sweep-deg", type=float, default=360.0)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the command-line entry point."""
    parser = build_parser()
    args = parser.parse_args(argv)

    logging.basicConfig(
        level=getattr(logging, args.log_level),
        format="%(levelname)s:%(name)s:%(message)s",
    )
    generator = DendrogramGenerator()

    if args.command != "build":
        parser.error("Unsupported command.")

    if args.output_csv is None and args.output_json is None and args.output_svg is None:
        parser.error(
            "At least one of --output-csv, --output-json, or --output-svg must be provided."
        )

    svg_title_parts = tuple(
        part.strip().lower()
        for part in str(args.svg_title_parts).split(",")
        if part.strip()
    )
    if not svg_title_parts:
        parser.error("--svg-title-parts must include at least one part.")

    svg_title_template = args.svg_title_template
    if svg_title_template is not None:
        svg_title_template = (
            str(svg_title_template)
            .replace("\\n", "\n")
            .replace("\\t", "\t")
            .replace("\\r", "\r")
        )

    logger.info(
        "Building dendrogram from %s (%s) using %s/%s",
        args.input_path,
        args.input_format,
        args.tree_layout,
        args.line_style,
    )
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
        colour_mode=args.colour_mode,
        palette=args.palette,
        palette_depth=args.palette_depth,
        show_palette_legend=args.show_palette_legend,
        show_svg_data_attributes=args.show_svg_data_attributes,
        show_svg_titles=args.show_svg_titles,
        svg_title_parts=svg_title_parts,
        svg_title_template=svg_title_template,
        node_colour=args.node_colour,
        edge_colour=args.edge_colour,
        label_colour=args.label_colour,
    )

    try:
        result = generator.generate_tree(
            args.input_path,
            tree_layout=args.tree_layout,
            line_style=args.line_style,
            input_format=args.input_format,
            output_csv=args.output_csv,
            output_json=args.output_json,
            output_svg=args.output_svg,
            show_labels=args.show_labels,
            options=options,
        )
    except (DendrogramError, ImportError) as exc:
        logger.error("Failed to build dendrogram: %s", exc)
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except Exception:
        logger.exception("Unexpected error while building dendrogram")
        return 1

    logger.info(
        "Generated %d nodes and %d edges",
        len(result.nodes),
        len(result.edges),
    )
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
