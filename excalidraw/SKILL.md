---
name: excalidraw
description: "Create Excalidraw diagrams using native Hermes tools. Generates valid .excalidraw JSON, saves to a GitHub repo, and provides the sharing instance URL for viewing/editing. Replaces MCP-based diagram tools — no external dependency."
version: 1.1.0
tags: [diagrams, excalidraw, visual, architecture, design]
platforms: [linux]
---

# Excalidraw — Hermes-Native Diagram Pipeline

Create Excalidraw diagrams and save them to a diagrams GitHub repo using Hermes tools directly. **No MCP dependency** — generates standard `.excalidraw` JSON files.

## Prerequisites

| Requirement | Details |
|-------------|---------|
| **GitHub repo** | A Git repository (public or private) to store `.excalidraw` files |
| **Local clone** | Clone your diagrams repo to `{{EXCALIDRAW_REPO_PATH}}` |
| **Git auth** | SSH key or credential helper configured for the remote |
| **Python 3** | Used for generating diagram JSON via helper functions |
| **Excalidraw instance** (optional) | Self-hosted or `https://excalidraw.com` to view/edit |

## Configuration Variables

Set these environment variables or substitute them directly in commands:

| Variable | Example | Purpose |
|----------|---------|---------|
| `{{EXCALIDRAW_REPO_PATH}}` | `/path/to/excalidraw-diagrams` | Local clone of your diagrams repo |
| `{{EXCALIDRAW_REPO_URL}}` | `https://github.com/username/excalidraw-diagrams.git` | Remote for cloning/pushing |
| `{{EXCALIDRAW_INSTANCE_URL}}` | `http://localhost:3002` or `https://excalidraw.com` | URL of your Excalidraw instance |

## Repo Folder Map (suggested)

| Folder | Use case |
|--------|----------|
| `architecture/` | System architecture, server layout, agent interconnections |
| `blog-posts/` | Article concept maps, technical process diagrams, comparison charts |
| `podcasts/` | Episode visuals, threat maps, segment flow diagrams |
| `videos/` | Storyboards, flow diagrams, visual hooks for short-form video |
| `misc/` | Anything that doesn't fit above |

## When to Use

- User says "draw a diagram of..." or "create a visual for..."
- User needs an architecture diagram, flow chart, topology map, or concept sketch
- User wants visuals for a blog post, presentation, video, or documentation

## Pipeline Steps

### Step 1: Sync the diagrams repo

```bash
terminal(command="if [ ! -d {{EXCALIDRAW_REPO_PATH}}/.git ]; then git clone {{EXCALIDRAW_REPO_URL}} {{EXCALIDRAW_REPO_PATH}}; else git -C {{EXCALIDRAW_REPO_PATH}} pull --ff-only origin main; fi", timeout=30)
```

### Step 2: Determine the target folder

Match the diagram purpose to a repo folder from the map above. Default to `misc/` if unsure.

### Step 3: Design and generate the diagram

Ask the user what the diagram should show. Clarify:
- What elements need to be on the diagram (boxes, labels, connections)
- Which direction the flow goes (top-to-bottom, left-to-right)
- Any colour coding needed

Then write valid Excalidraw JSON. Use the Python generator approach to produce clean, structured diagrams.

### Step 4: Create the diagram file

Name the file using kebab-case (e.g. `rag-chatbot-architecture.excalidraw`).

Save to the correct folder under the repo:

```bash
terminal(command="mkdir -p {{EXCALIDRAW_REPO_PATH}}/TARGET_FOLDER && cat > {{EXCALIDRAW_REPO_PATH}}/TARGET_FOLDER/FILENAME.excalidraw << 'JSONEOF'
[GENERATED JSON CONTENT]
JSONEOF", timeout=10)
```

Or for larger diagrams, write the JSON to a temp file then copy:

```bash
terminal(command="python3 /tmp/gen_diagram.py && cp /tmp/diagram_output.json {{EXCALIDRAW_REPO_PATH}}/TARGET_FOLDER/FILENAME.excalidraw", timeout=15)
```

### Step 5: Commit and push

```bash
terminal(command="cd {{EXCALIDRAW_REPO_PATH}} && git add . && git commit -m 'diagram: DESCRIPTION' && git push", timeout=30)
```

### Step 6: Report back

Tell the user:
- The diagram file path in the repo: `TARGET_FOLDER/FILENAME.excalidraw`
- They can view/edit at `{{EXCALIDRAW_INSTANCE_URL}}` (self-hosted instance or excalidraw.com)
- Or drag-and-drop onto `https://excalidraw.com` for instant viewing (no account needed)

## Excalidraw JSON Structure

A valid `.excalidraw` file has this structure:

```json
{
  "type": "excalidraw",
  "version": 2,
  "source": "https://excalidraw.com",
  "elements": [
    { /* shapes, text, arrows */ }
  ],
  "appState": {
    "gridSize": null,
    "viewBackgroundColor": "#ffffff"
  }
}
```

## Colour Palette (Standard Excalidraw)

| Use | Colour | Fill Variant |
|-----|--------|-------------|
| Primary / Blue | `#1971c2` (stroke) | `#a5d8ff` (fill) |
| Amber / Orange | `#e67700` (stroke) | `#ffec99` (fill) |
| Success / Green | `#2f9e44` (stroke) | `#b2f2bb` (fill) |
| Error / Red | `#c92a2a` (stroke) | `#ffc9c9` (fill) |
| Accent / Purple | `#6741d9` (stroke) | `#d0bfff` (fill) |
| Neutral / Grey | `#495057` (stroke) | `#dee2e6` (fill) |

## Python Generation Approach

Use the bundled `python_helpers.py` (in this skill directory) or inline the helper functions to generate diagram JSON programmatically.

The `python_helpers.py` file provides:

- **`rect(id, x, y, w, h, label, fill="#a5d8ff")`** → Returns `(rectangle_element, text_element)` tuple with `boundElements` and `containerId` wired up correctly.
- **`arrow(id, x, y, dx, dy, start_id, end_id)`** → Returns an arrow element with `startBinding` and `endBinding` set.
- **`text(id, x, y, w, h, text, container_id=None, **kwargs)`** → Returns a text element (bound or standalone).
- **`diagram(title, elements, app_state=None)`** → Wraps elements into a complete `.excalidraw` document.

## Pitfalls

- **Container binding is required.** Do NOT use `"label": {"text": "..."}` on shapes — it is silently ignored by Excalidraw. Use `boundElements` on the shape + a separate text element with `containerId`.
- **Standalone text** (not bound to a shape) needs `"containerId": null`.
- **Camera/pseudo-elements** (`cameraUpdate`) are NOT valid Excalidraw elements — do not include them in the JSON. They are MCP-specific.
- **The repo path is ephemeral** if stored in a temp directory. Ensure the clone persists or re-clone on each run.
- **Git auth**: Private repos require SSH key or credential helper. If push fails, the JSON file still exists locally — report the error.
- **Large diagrams** with many elements can produce JSON files exceeding 100KB. Consider splitting complex diagrams into multiple files. 10–15 elements is a comfortable size for one diagram.
- **Fill colours for labels**: set `"backgroundColor": "transparent"` on text elements so they don't obscure the shape's fill colour.
