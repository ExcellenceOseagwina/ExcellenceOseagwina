#!/usr/bin/env python3
"""Validate generated SVG output before it is committed."""
from __future__ import annotations

import sys
import xml.etree.ElementTree as ET
from pathlib import Path

SVG_NS = "{http://www.w3.org/2000/svg}"
FORBIDDEN_TAGS = {"script", "foreignObject", "iframe", "object", "embed"}


def validate_svg(path: Path) -> None:
    try:
        root = ET.parse(path).getroot()
    except (ET.ParseError, OSError) as exc:
        raise ValueError(f"Cannot parse SVG {path}: {exc}") from exc

    if root.tag != f"{SVG_NS}svg":
        raise ValueError("Document root must be an SVG element.")

    for element in root.iter():
        local_name = element.tag.rsplit("}", 1)[-1].lower()
        if local_name in FORBIDDEN_TAGS:
            raise ValueError(f"Disallowed SVG element: {local_name}")

        for attribute, value in element.attrib.items():
            attr_name = attribute.rsplit("}", 1)[-1].lower()
            if attr_name.startswith("on"):
                raise ValueError(f"Event-handler attribute is not allowed: {attr_name}")
            if attr_name in {"href", "src"} and value.strip().lower().startswith(
                ("http:", "https:", "javascript:", "data:")
            ):
                raise ValueError(f"External or executable resource reference is not allowed: {attr_name}")

    print(f"SVG validation passed: {path}")


if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("stats.svg")
    try:
        validate_svg(target)
    except ValueError as error:
        print(f"SVG validation failed: {error}", file=sys.stderr)
        raise SystemExit(1)
