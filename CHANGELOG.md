# Changelog

## 0.1.4

- CSV and JSON loaders now accept in-memory text streams as well as file paths.
- Vertical leaf labels now support auto placement below the node.
- Removed the redundant `--show-labels` flag in favour of `--label-mode`.
- Moved low-level layout tuning flags into an advanced section and clarified their numeric types.

## 0.1.3

- Fixed PNG resolution.
- Added a separate PyPI README.

## 0.1.2

- Added the example PNG assets.

## 0.1.1

- PyPI image/packaging fix.

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
