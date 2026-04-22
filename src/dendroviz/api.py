from __future__ import annotations

import logging
from pathlib import Path

from .export import CsvExporter, JsonExporter, SvgExporter
from .input import TreeCsvLoader
from .layout import TreeLayouter
from .models import InputFormat, LayoutOptions, LineStyle, RenderResult, TreeLayout, TreeModel
from .routing import EdgeRouter

logger = logging.getLogger(__name__)


class DendrogramGenerator:
    def __init__(
        self,
        *,
        loader: TreeCsvLoader | None = None,
        csv_exporter: CsvExporter | None = None,
        json_exporter: JsonExporter | None = None,
        svg_exporter: SvgExporter | None = None,
    ) -> None:
        """Create a generator with optional dependency injection."""
        self.loader = loader or TreeCsvLoader()
        self.csv_exporter = csv_exporter or CsvExporter()
        self.json_exporter = json_exporter or JsonExporter()
        self.svg_exporter = svg_exporter or SvgExporter()

    def load_tree_csv(self, path: str | Path) -> TreeModel:
        """Load a CSV tree file into a tree model."""
        return self.loader.load_tree(path, input_format="csv")

    def load_tree(self, path: str | Path, *, input_format: InputFormat = "csv") -> TreeModel:
        """Load a tree file in the requested input format."""
        return self.loader.load_tree(path, input_format=input_format)

    def generate_tree(
        self,
        input_path: str | Path,
        *,
        tree_layout: TreeLayout,
        line_style: LineStyle,
        input_format: InputFormat = "csv",
        output_csv: str | Path | None = None,
        output_json: str | Path | None = None,
        output_svg: str | Path | None = None,
        show_labels: bool = False,
        options: LayoutOptions | None = None,
    ) -> RenderResult:
        """Load, lay out, route, and optionally export a tree."""
        resolved_options = options or LayoutOptions()
        self._validate_options(resolved_options)
        logger.info("Generating tree...")
        self._log_unused_option_warnings(resolved_options, show_labels)
        logger.info(
            "Generating tree from %s (%s) using %s/%s",
            input_path,
            input_format,
            tree_layout,
            line_style,
        )
        tree = self.loader.load_tree(input_path, input_format=input_format)
        logger.debug("Loaded tree with %d nodes", len(tree.nodes))
        TreeLayouter(resolved_options).apply(tree, tree_layout)
        logger.debug("Applied %s layout", tree_layout)
        edges = EdgeRouter(resolved_options).build_paths(tree, tree_layout, line_style)
        logger.debug("Built %d routed edges", len(edges))
        result = RenderResult(
            tree=tree,
            edges=edges,
            csv_rows=[],
            tree_layout=tree_layout,
            line_style=line_style,
        )
        result.csv_rows = self.csv_exporter.build_rows(result, resolved_options)
        logger.debug("Built %d CSV rows", len(result.csv_rows))

        if output_csv is not None:
            logger.info("Writing CSV output to %s", output_csv)
            result.output_csv = self.csv_exporter.export(output_csv, result.csv_rows)
        if output_json is not None:
            logger.info("Writing JSON output to %s", output_json)
            result.output_json = self.json_exporter.export(
                output_json, result, resolved_options, show_labels
            )
        if output_svg is not None:
            logger.info("Writing SVG output to %s", output_svg)
            result.output_svg = self.svg_exporter.export(
                output_svg, result, show_labels, resolved_options
            )
        return result

    def _log_unused_option_warnings(self, options: LayoutOptions, show_labels: bool) -> None:
        """Warn when the caller sets options that will be ignored."""
        defaults = LayoutOptions()
        if not show_labels:
            label_overrides: list[str] = []
            if options.label_mode != defaults.label_mode:
                label_overrides.append("--label-mode")
            if options.label_orientation != defaults.label_orientation:
                label_overrides.append("--label-orientation")
            if options.label_offset != defaults.label_offset:
                label_overrides.append("--label-offset")
            if options.font_size != defaults.font_size:
                label_overrides.append("--font-size")
            if label_overrides:
                logger.warning(
                    "Labels are disabled, so %s have no effect.",
                    ", ".join(label_overrides),
                )

        if options.colour_mode == "global":
            palette_overrides: list[str] = []
            if options.palette != defaults.palette:
                palette_overrides.append("--palette")
            if options.palette_depth != defaults.palette_depth:
                palette_overrides.append("--palette-depth")
            if palette_overrides:
                logger.warning(
                    "Palette colour settings %s are ignored unless --colour-mode palette is set.",
                    ", ".join(palette_overrides),
                )
            if options.show_palette_legend:
                logger.warning(
                    "--show-palette-legend is ignored unless --colour-mode palette is set."
                )
        else:
            colour_overrides: list[str] = []
            if options.node_colour != defaults.node_colour:
                colour_overrides.append("--node-colour")
            if options.edge_colour != defaults.edge_colour:
                colour_overrides.append("--edge-colour")
            if options.label_colour != defaults.label_colour:
                colour_overrides.append("--label-colour")
            if colour_overrides:
                logger.warning(
                    "Global colour settings %s are ignored when --colour-mode palette is set.",
                    ", ".join(colour_overrides),
                )

    def _validate_options(self, options: LayoutOptions) -> None:
        """Reject numeric options that fall outside supported ranges."""
        if options.font_size <= 0:
            raise ValueError("font_size must be positive.")
        if options.label_offset < 0:
            raise ValueError("label_offset must be non-negative.")
        if options.radial_sweep_deg <= 0:
            raise ValueError("radial_sweep_deg must be positive.")

    def export_csv(self, path: str | Path, rows: list[dict[str, str | float | int]]) -> Path:
        """Write render rows to CSV."""
        return self.csv_exporter.export(path, rows)

    def export_svg(
        self,
        path: str | Path,
        result: RenderResult,
        *,
        show_labels: bool = False,
        options: LayoutOptions | None = None,
    ) -> Path:
        """Write an SVG rendering for a previously generated tree."""
        return self.svg_exporter.export(path, result, show_labels, options or LayoutOptions())

    def export_json(
        self,
        path: str | Path,
        result: RenderResult,
        *,
        show_labels: bool = False,
        options: LayoutOptions | None = None,
    ) -> Path:
        """Write a JSON rendering for a previously generated tree."""
        return self.json_exporter.export(path, result, options or LayoutOptions(), show_labels)
