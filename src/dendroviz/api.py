from __future__ import annotations

from pathlib import Path

from .export import CsvExporter, SvgExporter
from .input import TreeCsvLoader
from .layout import TreeLayouter
from .models import InputFormat, LayoutOptions, LineStyle, RenderResult, TreeLayout, TreeModel
from .routing import EdgeRouter


class DendrogramGenerator:
    def __init__(
        self,
        *,
        loader: TreeCsvLoader | None = None,
        csv_exporter: CsvExporter | None = None,
        svg_exporter: SvgExporter | None = None,
    ) -> None:
        self.loader = loader or TreeCsvLoader()
        self.csv_exporter = csv_exporter or CsvExporter()
        self.svg_exporter = svg_exporter or SvgExporter()

    def load_tree_csv(self, path: str | Path) -> TreeModel:
        return self.loader.load_tree(path, input_format="csv")

    def load_tree(self, path: str | Path, *, input_format: InputFormat = "csv") -> TreeModel:
        return self.loader.load_tree(path, input_format=input_format)

    def generate_tree(
        self,
        input_path: str | Path,
        *,
        tree_layout: TreeLayout,
        line_style: LineStyle,
        input_format: InputFormat = "csv",
        output_csv: str | Path | None = None,
        output_svg: str | Path | None = None,
        show_labels: bool = False,
        options: LayoutOptions | None = None,
    ) -> RenderResult:
        resolved_options = options or LayoutOptions()
        tree = self.loader.load_tree(input_path, input_format=input_format)
        TreeLayouter(resolved_options).apply(tree, tree_layout)
        edges = EdgeRouter(resolved_options).build_paths(tree, tree_layout, line_style)
        result = RenderResult(
            tree=tree,
            edges=edges,
            csv_rows=[],
            tree_layout=tree_layout,
            line_style=line_style,
        )
        result.csv_rows = self.csv_exporter.build_rows(result, resolved_options)

        if output_csv is not None:
            result.output_csv = self.csv_exporter.export(output_csv, result.csv_rows)
        if output_svg is not None:
            result.output_svg = self.svg_exporter.export(output_svg, result, show_labels, resolved_options)
        return result

    def export_csv(self, path: str | Path, rows: list[dict[str, str | float | int]]) -> Path:
        return self.csv_exporter.export(path, rows)

    def export_svg(
        self,
        path: str | Path,
        result: RenderResult,
        *,
        show_labels: bool = False,
        options: LayoutOptions | None = None,
    ) -> Path:
        return self.svg_exporter.export(path, result, show_labels, options or LayoutOptions())
