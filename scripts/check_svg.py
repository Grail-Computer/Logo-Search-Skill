#!/usr/bin/env python3
"""Quick SVG metadata checker.

Usage:
  python3 scripts/check_svg.py /path/to/logo.svg
"""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: check_svg.py <svg_path>")
        return 1

    path = Path(sys.argv[1])
    if not path.exists():
        print(f"error: file not found: {path}")
        return 1

    try:
        tree = ET.parse(path)
        root = tree.getroot()
    except ET.ParseError as exc:
        print(f"error: invalid svg xml: {exc}")
        return 1

    width = root.attrib.get("width", "")
    height = root.attrib.get("height", "")
    view_box = root.attrib.get("viewBox", "")

    print(f"file={path}")
    print(f"width={width or 'missing'}")
    print(f"height={height or 'missing'}")
    print(f"viewBox={view_box or 'missing'}")

    if not view_box:
        print("warning: missing viewBox (can cause scaling issues)")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
