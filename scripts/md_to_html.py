#!/usr/bin/env python3
"""
md_to_html.py — Convert Medium story markdown to HTML

CUSTOMISE: Update STORIES_DIR to match your repository structure.

Usage:
    python3 md_to_html.py <story_number> [--select story1,story2]
    python3 md_to_html.py 42
    python3 md_to_html.py 42 --select medium-story,linkedin-post
"""

import os, sys, re, argparse
from markdown import markdown

# ─── Configuration — CUSTOMISE THIS ───────────────────────────────────
STORIES_DIR = os.environ.get("STORIES_DIR", "{{YOUR_REPO_PATH}}/unpublished_stories")
# ──────────────────────────────────────────────────────────────────────

def convert_file(filepath, output_dir, prefix=""):
    """Convert a markdown file to HTML fragment and full page."""
    with open(filepath) as f:
        md_content = f.read()
    
    # Extract title from first # heading
    title_match = re.search(r'^#\s+(.+)$', md_content, re.MULTILINE)
    title = title_match.group(1) if title_match else os.path.basename(filepath)
    
    # Convert to HTML
    html_body = markdown(md_content, extensions=['fenced_code', 'codehilite', 'tables'])
    
    # Fragment (paste-ready)
    fragment_path = os.path.join(output_dir, f"{prefix}.fragment.html")
    with open(fragment_path, 'w') as f:
        f.write(html_body)
    print(f"  ✓  {prefix}.md")
    print(f"       → {prefix}.fragment.html  (fragment, paste-ready)")
    
    # Full page (browser preview)
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; max-width: 740px; margin: 40px auto; padding: 0 20px; line-height: 1.6; color: #242424; }}
        pre {{ background: #f4f4f4; padding: 16px; border-radius: 8px; overflow-x: auto; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 4px; font-size: 0.9em; }}
        img {{ max-width: 100%; }}
        h2 {{ margin-top: 40px; }}
        hr {{ border: none; border-top: 1px solid #e0e0e0; margin: 40px 0; }}
    </style>
</head>
<body>
{html_body}
</body>
</html>"""
    
    full_path = os.path.join(output_dir, f"{prefix}.full.html")
    with open(full_path, 'w') as f:
        f.write(full_html)
    print(f"       → {prefix}.full.html  (full page, open in browser)")


def main():
    parser = argparse.ArgumentParser(description="Convert Medium story markdown to HTML")
    parser.add_argument("story_number", help="Story number (e.g. 42)")
    parser.add_argument("--select", help="Comma-separated list of files to convert (default: all)")
    args = parser.parse_args()
    
    story_dir = os.path.join(STORIES_DIR, f"{args.story_number}_{{SLUG}}")
    
    # We need the exact directory name — find it
    if not os.path.exists(story_dir):
        # Try to find by number
        import glob
        matches = glob.glob(os.path.join(STORIES_DIR, f"{args.story_number}_*"))
        if not matches:
            print(f"❌  Story directory not found: {args.story_number}")
            sys.exit(1)
        story_dir = matches[0]
    
    print(f"📁  {os.path.basename(story_dir)}")
    
    # Files to convert
    all_files = {
        "medium-story": "medium-story.md",
        "linkedin-post": "linkedin-post.md",
    }
    
    if args.select:
        selected = args.select.split(",")
        files_to_convert = {k: v for k, v in all_files.items() if k in selected}
    else:
        files_to_convert = all_files
    
    for prefix, filename in files_to_convert.items():
        filepath = os.path.join(story_dir, filename)
        if os.path.exists(filepath):
            convert_file(filepath, story_dir, prefix)
        else:
            print(f"  ⚠️  {filename} not found, skipping")
    
    print("\n✅  Done.")


if __name__ == "__main__":
    main()
