# Contributing

This project is developed on feature branches.

## Local Setup

Install the package in editable mode with development dependencies:

```bash
pip install -e .[dev]
```

Run the test suite with:

```bash
python -m unittest discover -s tests -v
```

Run linting with:

```bash
python -m ruff check .
```

Build a distribution check with:

```bash
python -m build --no-isolation
```

## Release Process

The project uses Semantic Versioning:

- `MAJOR` for breaking API or CLI changes
- `MINOR` for new backward-compatible features
- `PATCH` for bug fixes and release-only polish

Before a release tag is created:

1. Update the version in `pyproject.toml`.
2. Add a short note to `CHANGELOG.md`.
3. Run the test suite, Ruff, and a build check.
4. Merge the feature branch.
5. Create and push a tag like `v0.1.0` to trigger the PyPI publish pipeline.
