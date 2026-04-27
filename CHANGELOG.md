# Changelog

## 0.1.5

- CSV and JSON loaders now accept in-memory text streams as well as file paths.
- Vertical leaf labels now support auto placement below the node.
- Newick branch lengths now influence layout spacing when present.
- Newick branch lengths are now used directly, with depth-based spacing as the fallback.

## 0.1.3

- Added group metadata to SVG tooltips.

## 0.1.2

- Relaxed README parity normalisation.

## 0.1.1

- Fixed PyPI image rendering and packaging.

## 0.1.0

- Initial public release of `dendroviz`.
- CSV, JSON, and SVG export for rooted trees.
- CLI and Python API for radial, vertical, and horizontal layouts.
- Palette-driven SVG colouring, optional legends, data attributes, and short titles.

## Versioning Policy

This project uses Semantic Versioning (`MAJOR.MINOR.PATCH`).

- `MAJOR` increments may introduce breaking changes.
- `MINOR` increments add backward-compatible features.
- `PATCH` increments cover fixes, packaging updates, and documentation polish.
