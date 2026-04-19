# DendroViz

`DendroViz` turns a rooted tree input into a scaffolded dendrogram dataset and optional SVG output.

It is designed for publication as a reusable Python library, while also including a small CLI for direct file conversion.

The package, CLI, and Python import path are all `dendroviz`.

## Examples

<table>
  <tr>
    <td align="center">
      <strong>Vertical tree with straight lines</strong><br>
      <img src="build/dummy-small-vertical-straight.svg" alt="Vertical straight SVG" width="250">
    </td>
    <td align="center">
      <strong>Horizontal tree with curved lines</strong><br>
      <img src="build/dummy-small-horizontal-curved.svg" alt="Horizontal curved SVG" width="250">
    </td>
    <td align="center">
      <strong>Radial tree with split lines</strong><br>
      <img src="build/dummy-deep-radial-split.svg" alt="Radial split SVG" width="250">
    </td>
  </tr>
</table>

## Features

- Tree layouts: `radial`, `vertical`, `horizontal`
- Line styles: `curved`, `split`, `straight`
- Any layout can be combined with any line style
- Arbitrary tree depth
- Render-ready CSV export
- Rendered JSON export for downstream tools and inspection
- SVG export with labels on or off
- SVG controls for leaf-only labels, root/internal node visibility, and colors
- Deterministic sibling ordering from CSV
- Optional Newick support through BioPython

## Installation

```bash
pip install dendroviz
```

Install the optional Newick parser only if you need it:

```bash
pip install biopython
```

For local development:

```bash
pip install -e .[dev]
```

## Quickstart

### Input CSV format

The library expects a single rooted tree with exactly these columns:

```csv
id,parent,label,order
root,,Root,0
branch_a,root,Branch A,0
branch_b,root,Branch B,1
leaf_a1,branch_a,Leaf A1,0
leaf_a2,branch_a,Leaf A2,1
leaf_b1,branch_b,Leaf B1,0
```

Rules:

- `id` must be unique
- `parent` is empty for the single root row
- every non-root parent must exist
- `order` controls sibling order and must be numeric
- cycles are not allowed

### Input Newick format

Newick input is also supported when BioPython is installed:

```python
from dendroviz import DendrogramGenerator

generator = DendrogramGenerator()
tree = generator.load_tree("examples/tree.nwk", input_format="newick")
```

Sibling order is taken from the order children appear in the Newick file.

### Python API

```python
from dendroviz import DendrogramGenerator, LayoutOptions

generator = DendrogramGenerator()
result = generator.generate_tree(
    "examples/dummy_deep.csv",
    tree_layout="radial",
    line_style="split",
    output_csv="build/dummy-deep-radial-split.csv",
    output_svg="build/dummy-deep-radial-split.svg",
    show_labels=True,
    options=LayoutOptions(
        label_mode="all",
        show_internal_nodes=True,
        show_root_node=True,
        label_orientation="auto",
        label_offset=24,
        color_mode="palette",
        palette="scientific",
    ),
)

print(len(result.nodes), len(result.edges))
```

To export the rendered tree as JSON instead of, or in addition to, CSV and SVG:

```python
result = generator.generate_tree(
    "examples/dummy_deep.csv",
    tree_layout="radial",
    line_style="split",
    output_json="build/dummy-deep.json",
    show_labels=True,
)
```

The JSON output is a rendered tree payload, not a raw input echo. It includes:

- `tree_layout` and `line_style`
- `show_labels`
- the resolved `options`
- `nodes` with positions, depth, branch metadata, and colors
- `edges` with routed points and colors

To render a Newick file instead:

```python
result = generator.generate_tree(
    "examples/tree.nwk",
    input_format="newick",
    tree_layout="radial",
    line_style="split",
)
```

Try it with the included dummy data:

- [dummy_small.csv](examples/dummy_small.csv)
- [dummy_medium.csv](examples/dummy_medium.csv)
- [dummy_deep.csv](examples/dummy_deep.csv)

### CLI

```bash
dendroviz build examples/dummy_deep.csv \
  --input-format csv \
  --tree-layout radial \
  --line-style split \
  --output-csv build/dummy-deep-radial-split.csv \
  --output-json build/dummy-deep.json \
  --output-svg build/dummy-deep-radial-split.svg \
  --show-labels \
  --label-mode leaves \
  --hide-internal-nodes \
  --label-orientation auto \
  --label-offset 24 \
  --color-mode palette \
  --palette scientific
```

Example test runs:

```bash
PYTHONPATH=src python3 -m dendroviz.cli build examples/dummy_small.csv \
  --tree-layout vertical \
  --line-style straight \
  --output-csv build/dummy-small-vertical-straight.csv \
  --output-svg build/dummy-small-vertical-straight.svg \
  --show-labels

PYTHONPATH=src python3 -m dendroviz.cli build examples/dummy_small.csv \
  --tree-layout horizontal \
  --line-style curved \
  --output-csv build/dummy-small-horizontal-curved.csv \
  --output-svg build/dummy-small-horizontal-curved.svg \
  --show-labels \
  --label-mode all \
  --label-offset 28 \
  --edge-color '#1d4ed8' \
  --node-color '#111827' \
  --label-color '#047857'

PYTHONPATH=src python3 -m dendroviz.cli build examples/dummy_deep.csv \
  --tree-layout radial \
  --line-style split \
  --output-csv build/dummy-deep-radial-split.csv \
  --output-svg build/dummy-deep-radial-split.svg \
  --show-labels \
  --label-orientation auto \
  --color-mode palette \
  --palette scientific
```

### Leaf-only labels and radial outer label placement

For a cleaner radial tree where only leaf nodes are drawn and only leaves get labels:

```bash
PYTHONPATH=src python3 -m dendroviz.cli build examples/dummy_deep.csv \
  --tree-layout radial \
  --line-style split \
  --output-svg build/dummy-deep-radial-split.svg \
  --show-labels \
  --label-orientation auto
```

To keep the root visible while hiding other internal nodes, do nothing extra because the root stays visible by default.
To hide the root marker too, add:

```bash
  --hide-root-node
```

To align radial leaf labels outside the tree with automatic flipping on the left side, add:

```bash
  --label-orientation auto
```

You can push labels farther outward with:

```bash
  --label-offset 24
```

You can also increase label size with:

```bash
  --font-size 18
```

To enlarge the entire SVG output without changing the tree structure, add:

```bash
  --scale 2
```

You can also set SVG colors globally:

```bash
  --edge-color '#334155' \
  --node-color '#0f172a' \
  --label-color '#7c2d12'
```

Or let the library color each top-level branch automatically:

```bash
  --color-mode palette \
  --palette scientific
```

Available built-in palettes:

- `default`
- `pastel`
- `high_contrast`
- `earth`
- `scientific`

## Output CSV schema

The render-ready CSV is a layered visualization table that works better with tools like Tableau and custom BI visuals:

- `type`: `link` or `node`
- `group`: top-level branch label used for grouping and color logic
- `id`: node id or link id
- `parent`: parent node id or source node id
- `child`: target node id for links, empty for nodes
- `label`: node label or empty for links
- `index`: link index for grouping path rows, empty for nodes
- `path`: point order within a link path, empty for nodes
- `x`, `y`: Cartesian coordinates
- `size`: node radius for node rows, empty for links
- `color`: resolved edge/node color
- `depth`: node depth or empty for links
- `tree_layout`: selected tree layout
- `line_style`: selected edge routing style

## Output JSON schema

The JSON export is intended for downstream tools that want the rendered tree as structured data rather than SVG markup.

Top-level fields:

- `tree_layout`: selected tree layout
- `line_style`: selected edge routing style
- `show_labels`: whether label rendering was requested
- `options`: the resolved layout and styling options
- `nodes`: rendered node records
- `edges`: routed edge records

Each node record includes:

- `node_id`
- `parent_id`
- `label`
- `order`
- `depth`
- `x`, `y`
- `angle`, `radius`
- `leaf_index`
- `is_leaf`
- `group`
- `branch_path`
- `color`

Each edge record includes:

- `edge_id`
- `source_id`
- `target_id`
- `group`
- `branch_path`
- `color`
- `points`

`points` is an array of `{x, y}` coordinates describing the routed path.

## How layout and line style interact

- `radial` layout arranges nodes by angle and radius
- `vertical` layout grows top-to-bottom
- `horizontal` layout grows left-to-right
- `curved` line style uses smooth cubic curves
- `split` line style uses branched orthogonal or radial split paths
- `straight` line style uses direct line segments

## Development

For now, use `pip install -e .[dev]` for local setup and run `python -m unittest discover -s tests -v` to execute the test suite.
