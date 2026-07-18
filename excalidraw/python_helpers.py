#!/usr/bin/env python3
"""
Excalidraw Diagram Helper — python_helpers.py

Standalone module for generating valid Excalidraw .excalidraw JSON files
programmatically. Provides rect(), arrow(), text(), and diagram() functions
that handle the required Excalidraw element structure correctly.

Usage:
    from python_helpers import rect, arrow, text, diagram
    import json

    r1, t1 = rect("server", 100, 100, 200, 80, "Server", fill="#a5d8ff")
    r2, t2 = rect("client", 100, 280, 200, 80, "Client", fill="#b2f2bb")
    a1 = arrow("flow", 200, 180, 0, 100, "server", "client")

    doc = diagram("Server-Client Architecture", [r1, t1, a1, r2, t2])

    with open("diagram.excalidraw", "w") as f:
        json.dump(doc, f, indent=2)
"""

import json
from typing import Any, Dict, List, Optional, Tuple


# ──────────────────────────────────────────────
# Colour palette helpers
# ──────────────────────────────────────────────

PALETTE = {
    "blue": {"stroke": "#1971c2", "fill": "#a5d8ff"},
    "amber": {"stroke": "#e67700", "fill": "#ffec99"},
    "green": {"stroke": "#2f9e44", "fill": "#b2f2bb"},
    "red": {"stroke": "#c92a2a", "fill": "#ffc9c9"},
    "purple": {"stroke": "#6741d9", "fill": "#d0bfff"},
    "grey": {"stroke": "#495057", "fill": "#dee2e6"},
}

DEFAULT_STROKE = "#1e1e1e"


# ──────────────────────────────────────────────
# Element helpers
# ──────────────────────────────────────────────


def rect(
    id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    label: str,
    fill: str = "#a5d8ff",
    stroke: str = DEFAULT_STROKE,
    stroke_width: int = 1,
    roundness: int = 3,
    font_size: int = 20,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Create a rectangle shape and a bound text label.

    Returns (rectangle_element, text_element) — both must be included
    in the elements list.

    The shape uses boundElements[] to reference the text, and the text
    element uses containerId to reference the shape. This is the correct
    Excalidraw pattern — do NOT use "label" on the shape.
    """
    shape = {
        "type": "rectangle",
        "id": id,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "strokeColor": stroke,
        "backgroundColor": fill,
        "fillStyle": "solid",
        "strokeWidth": stroke_width,
        "roundness": {"type": roundness},
        "boundElements": [{"id": f"t_{id}", "type": "text"}],
    }

    text_el = {
        "type": "text",
        "id": f"t_{id}",
        "x": x,
        "y": y + (h - font_size) / 2,
        "width": w,
        "height": font_size + 4,
        "text": label,
        "fontSize": font_size,
        "fontFamily": 1,
        "textAlign": "center",
        "verticalAlign": "middle",
        "containerId": id,
        "autoResize": True,
        "strokeColor": DEFAULT_STROKE,
        "backgroundColor": "transparent",
    }

    return shape, text_el


def arrow(
    id: str,
    x: float,
    y: float,
    dx: float,
    dy: float,
    start_id: str,
    end_id: str,
    stroke: str = DEFAULT_STROKE,
) -> Dict[str, Any]:
    """
    Create an arrow connector between two elements.

    The arrow starts at (x, y) and extends by (dx, dy) pixels.
    start_id and end_id are the IDs of the shapes being connected.
    The 'focus' parameter (0.5 = centre) controls which edge anchor
    point the arrow attaches to.
    """
    return {
        "type": "arrow",
        "id": id,
        "x": x,
        "y": y,
        "width": dx,
        "height": dy,
        "strokeColor": stroke,
        "strokeWidth": 1,
        "startBinding": {"elementId": start_id, "gap": 0, "focus": 0.5},
        "endBinding": {"elementId": end_id, "gap": 0, "focus": 0.5},
        "points": [[0, 0], [dx, dy]],
    }


def text(
    id: str,
    x: float,
    y: float,
    w: float,
    h: float,
    content: str,
    container_id: Optional[str] = None,
    font_size: int = 20,
    font_family: int = 1,
    text_align: str = "center",
    vertical_align: str = "middle",
    stroke: str = DEFAULT_STROKE,
) -> Dict[str, Any]:
    """
    Create a text element (bound to a container or standalone).

    If container_id is provided, the text is attached to that shape.
    For standalone text (not inside a shape), container_id must be None.
    """
    el: Dict[str, Any] = {
        "type": "text",
        "id": id,
        "x": x,
        "y": y,
        "width": w,
        "height": h,
        "text": content,
        "fontSize": font_size,
        "fontFamily": font_family,
        "textAlign": text_align,
        "verticalAlign": vertical_align,
        "containerId": container_id,
        "autoResize": True,
        "strokeColor": stroke,
        "backgroundColor": "transparent",
    }

    return el


# ──────────────────────────────────────────────
# Document builder
# ──────────────────────────────────────────────


def diagram(
    title: str,
    elements: List[Dict[str, Any]],
    app_state: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Wrap a list of elements into a complete Excalidraw document.

    The returned dict can be serialised directly to a .excalidraw file.

    Args:
        title: Source description for the document metadata.
        elements: List of element dicts (from rect(), arrow(), text()).
        app_state: Optional overrides for gridSize, viewBackgroundColor, etc.

    Returns:
        A dict representing the full .excalidraw document.
    """
    state = {
        "gridSize": None,
        "viewBackgroundColor": "#ffffff",
    }
    if app_state:
        state.update(app_state)

    return {
        "type": "excalidraw",
        "version": 2,
        "source": title,
        "elements": elements,
        "appState": state,
    }


# ──────────────────────────────────────────────
# CLI entrypoint
# ──────────────────────────────────────────────


def main():
    """Generate an example diagram when run as a script."""
    r1, t1 = rect("api", 100, 100, 240, 70, "API Gateway", fill=PALETTE["blue"]["fill"])
    r2, t2 = rect("auth", 100, 250, 240, 70, "Auth Service", fill=PALETTE["green"]["fill"])
    r3, t3 = rect("db", 100, 400, 240, 70, "Database", fill=PALETTE["amber"]["fill"])

    a1 = arrow("a1", 220, 170, 0, 80, "api", "auth")
    a2 = arrow("a2", 220, 320, 0, 80, "auth", "db")

    doc = diagram("Example Architecture", [r1, t1, a1, r2, t2, a2, r3, t3])

    with open("example-diagram.excalidraw", "w") as f:
        json.dump(doc, f, indent=2)

    print("Generated example-diagram.excalidraw")


if __name__ == "__main__":
    main()
