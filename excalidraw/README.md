# Excalidraw Hermes Skill

Generate Excalidraw diagrams directly from Hermes Agent — no Claude Code MCP, no external dependencies. This skill produces valid `.excalidraw` JSON files using Python helper functions and stores them in a Git repository for versioning and sharing.

## What It Does

- Generates clean Excalidraw diagrams (flow charts, architecture maps, topology diagrams, concept sketches) as standard `.excalidraw` JSON
- Provides Python helper functions (`rect()`, `arrow()`, `text()`) so you build diagrams programmatically rather than hand-writing JSON
- Saves diagram files to a GitHub repo with automatic commit and push
- Supports a self-hosted Excalidraw instance or `https://excalidraw.com` for viewing and editing

## Prerequisites

| Requirement | Notes |
|-------------|-------|
| **Hermes Agent** | You need a running Hermes Agent session |
| **GitHub repo** | A Git repository to store `.excalidraw` files (public or private) |
| **Git auth** | SSH key or credential helper configured for the remote |
| **Python 3** | Used for running the Python helper script |
| **Excalidraw** | Either self-hosted (Docker) or `https://excalidraw.com` for viewing |

## Installation

### 1. Clone this skill (optional — for standalone use)

```bash
git clone https://github.com/your-org/Hermes-Skills.git
cd Hermes-Skills/excalidraw
```

### 2. Set up your diagrams repo

```bash
# Create a new repo on GitHub, then:
export EXCALIDRAW_REPO_PATH="/path/to/excalidraw-diagrams"
export EXCALIDRAW_REPO_URL="https://github.com/your-username/excalidraw-diagrams.git"

git clone "$EXCALIDRAW_REPO_URL" "$EXCALIDRAW_REPO_PATH"
```

### 3. Configure Hermes

If you are using this as a Hermes skill, load it in your session:

```
skill_view(name="excalidraw")
```

Set the configuration variables in your Hermes profile or session.

### 4. (Optional) Self-host Excalidraw with Docker

```bash
docker run -d --name excalidraw -p 3002:80 excalidraw/excalidraw:latest
```

Then set `{{EXCALIDRAW_INSTANCE_URL}}` to `http://localhost:3002`.

> **Note:** Self-hosting is optional. You can use `https://excalidraw.com` directly — drag-and-drop the `.excalidraw` file to open it with no account required.

## Usage

### Quick Start

```python
from python_helpers import rect, arrow, diagram

# Build elements
r1, t1 = rect("r1", 100, 100, 200, 80, "Frontend", fill="#a5d8ff")
r2, t2 = rect("r2", 100, 280, 200, 80, "Backend", fill="#b2f2bb")
a1 = arrow("a1", 200, 180, 0, 100, "r1", "r2")

# Generate the diagram file
doc = diagram("My Architecture", [r1, t1, a1, r2, t2])

import json
with open("my-architecture.excalidraw", "w") as f:
    json.dump(doc, f, indent=2)
```

### Using the Python Helper Pattern

The `python_helpers.py` script provides three core functions:

#### `rect(id, x, y, w, h, label, fill="#a5d8ff")`
Creates a rectangle with a bound text label. Returns `(shape_element, text_element)`.

| Parameter | Description |
|-----------|-------------|
| `id` | Unique element identifier (e.g. `"server"`, `"db"`) |
| `x, y` | Top-left position in the Excalidraw canvas |
| `w, h` | Width and height of the rectangle |
| `label` | Text to display inside the rectangle |
| `fill` | Background fill colour (default: light blue `#a5d8ff`) |

#### `arrow(id, x, y, dx, dy, start_id, end_id)`
Creates an arrow connecting two elements.

| Parameter | Description |
|-----------|-------------|
| `id` | Unique element identifier (e.g. `"a1"`, `"flow"`) |
| `x, y` | Starting position of the arrow |
| `dx, dy` | Offset from start to end (width and height of arrow) |
| `start_id` | ID of the source element (arrow attaches here) |
| `end_id` | ID of the target element (arrow points here) |

#### `text(id, x, y, w, h, text, container_id=None)`
Creates a text element. If `container_id` is provided, it is bound to that element.

| Parameter | Description |
|-----------|-------------|
| `id` | Unique element identifier |
| `x, y` | Position |
| `w, h` | Dimensions |
| `text` | The text content |
| `container_id` | ID of the parent shape (omit for standalone text) |

#### `diagram(title, elements, app_state=None)`
Wraps a list of elements into a complete Excalidraw document.

| Parameter | Description |
|-----------|-------------|
| `title` | Used for the source field in document metadata |
| `elements` | List of element dicts to include |
| `app_state` | Optional dict with `gridSize`, `viewBackgroundColor`, etc. |

## Excalidraw Format Reference

A valid `.excalidraw` file is a JSON document with this structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    {
      "type": "rectangle",
      "id": "unique-id",
      "x": 100,
      "y": 100,
      "width": 200,
      "height": 80,
      "strokeColor": "#1971c2",
      "backgroundColor": "#a5d8ff",
      "fillStyle": "solid",
      "strokeWidth": 1,
      "roundness": { "type": 3 },
      "boundElements": [{ "id": "text-id", "type": "text" }]
    },
    {
      "type": "text",
      "id": "text-id",
      "x": 100,
      "y": 125,
      "width": 200,
      "height": 25,
      "text": "My Label",
      "fontSize": 20,
      "fontFamily": 1,
      "textAlign": "center",
      "verticalAlign": "middle",
      "containerId": "unique-id",
      "autoResize": true,
      "strokeColor": "#1e1e1e",
      "backgroundColor": "transparent"
    },
    {
      "type": "arrow",
      "id": "arrow-id",
      "x": 300,
      "y": 140,
      "width": 100,
      "height": 0,
      "strokeColor": "#1e1e1e",
      "strokeWidth": 1,
      "startBinding": { "elementId": "r1", "gap": 0, "focus": 0 },
      "endBinding": { "elementId": "r2", "gap": 0, "focus": 0 },
      "points": [[0, 0], [100, 0]]
    }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  }
}
```

### Critical Rules

1. **Text must be a separate element** — never use `"label": {"text": "..."}` on a shape. Excalidraw silently ignores it.
2. **Bound text** needs `boundElements` on the shape AND `containerId` on the text element.
3. **Standalone text** (not inside a shape) needs `"containerId": null`.
4. **Do not include `cameraUpdate` or any pseudo-elements** — those are MCP-only artifacts, not valid Excalidraw elements.
5. **Set `backgroundColor: "transparent"` on text labels** so they don't cover the shape's fill.

## Self-Hosting Excalidraw (Optional)

If you want a private, always-on instance:

```bash
# Using Docker
docker run -d \
  --name excalidraw \
  -p 3002:80 \
  excalidraw/excalidraw:latest
```

Then access at `http://localhost:3002`.

> **Note:** The official Excalidraw Docker image (`excalidraw/excalidraw`) is maintained by the Excalidraw team. Check [their GitHub](https://github.com/excalidraw/excalidraw) for the latest deployment options, including Docker Compose and Kubernetes configs.

Alternatively, use `https://excalidraw.com` — no setup required. Just drag-and-drop an `.excalidraw` file onto the page to open it.

## Example: Full Pipeline

```python
#!/usr/bin/env python3
from python_helpers import rect, arrow, diagram
import json

# 1. Design elements
r1, t1 = rect("api", 100, 100, 240, 70, "API Gateway", fill="#a5d8ff")
r2, t2 = rect("auth", 100, 250, 240, 70, "Auth Service", fill="#b2f2bb")
r3, t3 = rect("db", 100, 400, 240, 70, "Database", fill="#ffec99")

# 2. Connect them
a1 = arrow("a1", 220, 170, 0, 80, "api", "auth")
a2 = arrow("a2", 220, 320, 0, 80, "auth", "db")

# 3. Build document
doc = diagram("API Architecture", [r1, t1, a1, r2, t2, a2, r3, t3])

# 4. Write to file
with open("api-architecture.excalidraw", "w") as f:
    json.dump(doc, f, indent=2)

print("Generated api-architecture.excalidraw")
```

## Licence

This skill is shared under the MIT Licence. See `LICENSE` in the Hermes-Skills repository root for details.
