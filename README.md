# DendroViz

[![GitHub Actions CI](https://github.com/lb930/DendroViz/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/lb930/DendroViz/actions/workflows/ci.yml)
[![PyPI version](https://img.shields.io/pypi/v/dendroviz.svg)](https://pypi.org/project/dendroviz/)
[![License](https://img.shields.io/pypi/l/dendroviz.svg)](https://github.com/lb930/DendroViz/blob/main/LICENSE)
<br><br>`DendroViz` takes CSV, JSON, or Newick input and turns it into a dendrogram dataset. The CSV output can be used in Tableau and other charting tools. The tool can also create SVG images.

<table>
  <tr>
    <td align="center">
      <strong>Vertical tree with straight lines</strong><br>
      <img src="https://raw.githubusercontent.com/lb930/DendroViz/fix/pypi-images/assets/dummy-small-vertical-straight.png" alt="Vertical straight preview" width="250">
    </td>
    <td align="center">
      <strong>Horizontal tree with curved lines</strong><br>
      <img src="https://raw.githubusercontent.com/lb930/DendroViz/fix/pypi-images/assets/dummy-small-horizontal-curved.png" alt="Horizontal curved preview" width="250">
    </td>
    <td align="center">
      <strong>Radial tree with split lines</strong><br>
      <img src="https://raw.githubusercontent.com/lb930/DendroViz/fix/pypi-images/assets/dummy-deep-radial-split.png" alt="Radial split preview" width="250">
    </td>
  </tr>
</table>

## Table of Contents

- [Installation](#installation)
- [Quickstart](#quickstart)
- [Input Format](#input-format)
- [Colour Palettes](#colour-palettes)
- [Release Process](#release-process)
- [CLI Reference](#cli-reference)
- [Development](#development)

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

### Python API

```python
from dendroviz import DendrogramGenerator, LayoutOptions

generator = DendrogramGenerator()
result = generator.generate_tree(
    "examples/dummy_deep.csv",
    tree_layout="radial",
    line_style="split",
    output_csv="build/dummy-deep-radial-split.csv",
    output_json="build/dummy-deep.json",
    output_svg="build/dummy-deep-radial-split.svg",
    show_labels=True,
    options=LayoutOptions(
        label_mode="leaves",
        show_internal_nodes=True,
        show_root_node=True,
        label_orientation="auto",
        label_offset=24,
        colour_mode="palette",
        palette="set2",
        palette_depth=2,
    ),
)

print(len(result.nodes), len(result.edges))
```

### CLI

```bash
dendroviz build examples/dummy_deep.csv \
  --input-format csv \
  --tree-layout radial \
  --line-style split \
  --output-svg build/dummy-deep-radial-split.svg \
  --show-labels \
  --label-mode leaves \
  --label-orientation auto \
  --label-offset 24 \
  --colour-mode palette \
  --palette set2 \
  --palette-depth 2 \
  --show-palette-legend
```

Example test runs:

```bash
dendroviz build examples/dummy_small.csv \
  --tree-layout vertical \
  --line-style straight \
  --output-csv build/dummy-small-vertical-straight.csv \
  --output-svg build/dummy-small-vertical-straight.svg \
  --show-labels \
  --colour-mode palette \
  --palette set2 \
  --palette-depth 2

dendroviz build examples/dummy_small.csv \
  --tree-layout horizontal \
  --line-style curved \
  --output-csv build/dummy-small-horizontal-curved.csv \
  --output-svg build/dummy-small-horizontal-curved.svg \
  --show-labels \
  --label-mode all \
  --label-offset 28 \
  --colour-mode palette \
  --palette set2 \
  --palette-depth 2

dendroviz build examples/dummy_deep.csv \
  --tree-layout radial \
  --line-style split \
  --output-csv build/dummy-deep-radial-split.csv \
  --output-svg build/dummy-deep-radial-split.svg \
  --show-labels \
  --label-orientation auto \
  --colour-mode palette \
  --palette set2 \
  --palette-depth 2
```

Try it with the included dummy data:

- [dummy_small.csv](examples/dummy_small.csv)
- [dummy_medium.csv](examples/dummy_medium.csv)
- [dummy_deep.csv](examples/dummy_deep.csv)

## Input Format

### CSV

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

### JSON

JSON input uses the same row fields as CSV. The loader accepts either:

- a top-level array of node objects
- an object with a `nodes` array

Each node object should include:

- `id`
- `parent`
- `label`
- `order`

Example:

```json
{
  "nodes": [
    { "id": "root", "parent": null, "label": "Root", "order": 0 },
    { "id": "left", "parent": "root", "label": "Left", "order": 0 },
    { "id": "right", "parent": "root", "label": "Right", "order": 1 }
  ]
}
```

Rules:

- `id` must be unique
- `parent` is `null` for the single root row
- every non-root parent must exist
- `order` controls sibling order and must be numeric
- cycles are not allowed

### Newick

Newick input is also supported when BioPython is installed. Install it with `pip install biopython`:

```python
from dendroviz import DendrogramGenerator

generator = DendrogramGenerator()
tree = generator.load_tree("examples/tree.nwk", input_format="newick")
```

Sibling order is taken from the order children appear in the Newick file.

## CLI Reference

### Mandatory

| Option | Values | Notes |
| --- | --- | --- |
| `build` | subcommand | Generate dendrogram artefacts from an input tree |
| input path | path | Path to the input tree file |
| `--tree-layout` | `radial`, `vertical`, `horizontal` | `radial` uses angle/radius coordinates, `vertical` grows top-to-bottom, `horizontal` grows left-to-right |
| `--line-style` | `curved`, `split`, `straight` | `curved` uses smooth splines, `split` branches at forks, `straight` uses direct segments |
| output flag(s) | `--output-csv`, `--output-json`, `--output-svg` | Write one or more render artefacts |

### Optional

These CLI flags map directly to `LayoutOptions` fields in the Python API.

| Option | Values | Notes |
| --- | --- | --- |
| `--log-level` | `CRITICAL`, `ERROR`, `WARNING`, `INFO`, `DEBUG` | Controls CLI verbosity |
| `--show-labels` | flag | Enables SVG labels |
| `--label-mode` | `all`, `leaves`, `none` | `leaves` shows labels only on leaf nodes; `none` hides all labels |
| `--label-orientation` | `horizontal`, `auto` | `auto` flips radial labels to stay readable on the left side |
| `--label-offset` | number | Pushes labels farther from the tree |
| `--font-size` | number | Controls label size |
| `--hide-internal-nodes` | flag | Hides non-leaf node markers |
| `--hide-root-node` | flag | Hides the root node marker |
| `--colour-mode` | `global`, `palette` | Controls whether palette colouring is used |
| `--palette` | preset name or hex colours | Used only when `--colour-mode palette` is active |
| `--palette-depth` | `1`, `2`, ... | Used only when `--colour-mode palette` is active; chooses which tree level gets palette colouring |
| `--show-palette-legend` | flag | Adds a small SVG legend when palette colouring is active |
| `--show-svg-data-attributes` | flag | Adds `data-*` metadata to SVG nodes and edges for browser scripting |
| `--show-svg-titles` | flag | Adds short hover titles to SVG nodes and edges |
| `--node-colour` | hex colour | Fallback node colour in global mode |
| `--edge-colour` | hex colour | Fallback edge colour in global mode |
| `--label-colour` | hex colour | Fallback label colour in global mode |
| `--depth-spacing` | number | Adjusts the gap between tree levels |
| `--sibling-spacing` | number | Adjusts the gap between siblings |
| `--curve-points` | number | Controls curved path smoothness |
| `--straight-points` | number | Controls how many points are used for straight paths |
| `--radial-base-angle-deg` | number | Sets the starting angle for radial layouts |
| `--radial-sweep-deg` | number | Sets the angular sweep for radial layouts |
| `--scale` | number | Enlarges SVG geometry, strokes, nodes, and text without changing the tree structure |

## Colour Palettes

All built-in palettes below are official ColorBrewer, Tableau, or Okabe-Ito palettes.
`set1` is the default palette.

Custom palettes are also supported:

- In Python, pass a list or tuple of hex colours to `LayoutOptions.palette`
- On the CLI, pass a comma-separated hex string with `--palette`, such as `#112233,#445566,#778899`
- Hex colours are validated before export, so invalid values fail fast

### Built-In Palettes

<table>
  <tr>
    <th align="left">Name</th>
    <th align="left">Swatches</th>
    <th align="left">Hex codes</th>
  </tr>
  <tr>
    <td><code>set1</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#e41a1c;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#377eb8;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#4daf4a;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#984ea3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ff7f00;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffff33;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#a65628;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#f781bf;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#999999;border:1px solid #999;"></span>
    </td>
    <td><code>#e41a1c #377eb8 #4daf4a #984ea3 #ff7f00 #ffff33 #a65628 #f781bf #999999</code></td>
  </tr>
  <tr>
    <td><code>set2</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#66c2a5;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fc8d62;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#8da0cb;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e78ac3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#a6d854;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffd92f;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e5c494;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#b3b3b3;border:1px solid #999;"></span>
    </td>
    <td><code>#66c2a5 #fc8d62 #8da0cb #e78ac3 #a6d854 #ffd92f #e5c494 #b3b3b3</code></td>
  </tr>
  <tr>
    <td><code>set3</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#8dd3c7;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffffb3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#bebada;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fb8072;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#80b1d3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fdb462;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#b3de69;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fccde5;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#d9d9d9;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#bc80bd;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ccebc5;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffed6f;border:1px solid #999;"></span>
    </td>
    <td><code>#8dd3c7 #ffffb3 #bebada #fb8072 #80b1d3 #fdb462 #b3de69 #fccde5 #d9d9d9 #bc80bd #ccebc5 #ffed6f</code></td>
  </tr>
  <tr>
    <td><code>pastel1</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#fbb4ae;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#b3cde3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ccebc5;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#decbe4;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fed9a6;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffffcc;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e5d8bd;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fddaec;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#f2f2f2;border:1px solid #999;"></span>
    </td>
    <td><code>#fbb4ae #b3cde3 #ccebc5 #decbe4 #fed9a6 #ffffcc #e5d8bd #fddaec #f2f2f2</code></td>
  </tr>
  <tr>
    <td><code>pastel2</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#b3e2cd;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fdcdac;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#cbd5e8;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#f4cae4;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e6f5c9;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fff2ae;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#f1e2cc;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#cccccc;border:1px solid #999;"></span>
    </td>
    <td><code>#b3e2cd #fdcdac #cbd5e8 #f4cae4 #e6f5c9 #fff2ae #f1e2cc #cccccc</code></td>
  </tr>
  <tr>
    <td><code>accent</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#7fc97f;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#beaed4;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fdc086;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffff99;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#386cb0;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#f0027f;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#bf5b17;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#666666;border:1px solid #999;"></span>
    </td>
    <td><code>#7fc97f #beaed4 #fdc086 #ffff99 #386cb0 #f0027f #bf5b17 #666666</code></td>
  </tr>
  <tr>
    <td><code>paired</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#a6cee3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#1f78b4;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#b2df8a;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#33a02c;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fb9a99;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e31a1c;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#fdbf6f;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ff7f00;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#cab2d6;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#6a3d9a;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ffff99;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#b15928;border:1px solid #999;"></span>
    </td>
    <td><code>#a6cee3 #1f78b4 #b2df8a #33a02c #fb9a99 #e31a1c #fdbf6f #ff7f00 #cab2d6 #6a3d9a #ffff99 #b15928</code></td>
  </tr>
  <tr>
    <td><code>tableau</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#1f77b4;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#ff7f0e;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#2ca02c;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#d62728;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#9467bd;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#8c564b;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e377c2;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#7f7f7f;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#bcbd22;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#17becf;border:1px solid #999;"></span>
    </td>
    <td><code>#1f77b4 #ff7f0e #2ca02c #d62728 #9467bd #8c564b #e377c2 #7f7f7f #bcbd22 #17becf</code></td>
  </tr>
  <tr>
    <td><code>dark2</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#1b9e77;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#d95f02;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#7570b3;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e7298a;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#66a61e;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#e6ab02;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#a6761d;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#666666;border:1px solid #999;"></span>
    </td>
    <td><code>#1b9e77 #d95f02 #7570b3 #e7298a #66a61e #e6ab02 #a6761d #666666</code></td>
  </tr>
  <tr>
    <td><code>scientific</code></td>
    <td>
      <span style="display:inline-block;width:1em;height:1em;background:#e69f00;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#56b4e9;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#009e73;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#f0e442;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#0072b2;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#d55e00;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#cc79a7;border:1px solid #999;"></span>
      <span style="display:inline-block;width:1em;height:1em;background:#000000;border:1px solid #999;"></span>
    </td>
    <td><code>#e69f00 #56b4e9 #009e73 #f0e442 #0072b2 #d55e00 #cc79a7 #000000</code></td>
  </tr>
</table>

## Development

For now, use `pip install -e .[dev]` for local setup and run `python -m unittest discover -s tests -v` to execute the test suite.

## Release Process

This project follows Semantic Versioning:

- `MAJOR` for breaking API or CLI changes
- `MINOR` for new backward-compatible features
- `PATCH` for bug fixes and release-only polish

Before creating a release tag:

1. Update the version in `pyproject.toml`.
2. Add a short note to `CHANGELOG.md`.
3. Run the test suite, Ruff, and a build check.
4. Create and push a tag like `v0.1.0`.
5. Let GitHub Actions publish the tagged build to PyPI.
