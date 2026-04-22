from __future__ import annotations

import re
import sys
from pathlib import Path

NORMALIZATIONS: tuple[tuple[re.Pattern[str], str], ...] = (
    (
        re.compile(
            r'src="(?:https://raw\.githubusercontent\.com/lb930/DendroViz/main/)?'
            r'(?:assets/dummy-small-vertical-straight\.png|build/dummy-small-vertical-straight\.svg)"',
        ),
        'src="IMAGE_VERTICAL_STRAIGHT"',
    ),
    (
        re.compile(
            r'src="(?:https://raw\.githubusercontent\.com/lb930/DendroViz/main/)?'
            r'(?:assets/dummy-small-horizontal-curved\.png|build/dummy-small-horizontal-curved\.svg)"',
        ),
        'src="IMAGE_HORIZONTAL_CURVED"',
    ),
    (
        re.compile(
            r'src="(?:https://raw\.githubusercontent\.com/lb930/DendroViz/main/)?'
            r'(?:assets/dummy-deep-radial-split\.png|build/dummy-deep-radial-split\.svg)"',
        ),
        'src="IMAGE_RADIAL_SPLIT"',
    ),
)


def normalize(text: str) -> str:
    """Normalize the README image references to a shared canonical form."""
    for pattern, replacement in NORMALIZATIONS:
        text = pattern.sub(replacement, text)
    return text


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: check_readme_parity.py README.md README.pypi.md", file=sys.stderr)
        return 2

    github_readme = Path(sys.argv[1]).read_text(encoding="utf-8")
    pypi_readme = Path(sys.argv[2]).read_text(encoding="utf-8")

    if normalize(github_readme) != normalize(pypi_readme):
        print("README.md and README.pypi.md differ outside of image sources.", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
