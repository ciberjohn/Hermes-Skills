#!/usr/bin/env python3
"""Convert a styled HTML "prep pack" into clean Markdown for Joplin.

Class-aware state machine. Emits:
- h2/h3 headings
- bullet lists (ul/li, qlist, minicards, tsteps, glossary)
- markdown tables (thead/tbody)
- blockquotes for callouts, success/danger boxes, chat bubbles
- <details>/<summary> preserved for sample exchanges

Usage:
  html_pack_to_markdown.py /path/to/input.html [> output.md]
"""
import argparse
import re
import sys
from html.parser import HTMLParser


class PackParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out = []
        self.skip_depth = 0
        self.div_stack = []       # class names of open divs
        self.list_depth = 0
        self.in_cell = False
        self.cell_text = []
        self.row_cells = []
        self.table_rows = []
        self.in_thead = False
        self.pending_prefix = ""  # prefix to emit on next text (bubble who, etc.)
        self.who_skip = 0         # skip depth for .who divs (name already emitted)
        self.span_stack = []      # class names of open spans

    # --- helpers ---
    def emit(self, s):
        if self.skip_depth == 0 and self.who_skip == 0:
            self.out.append(s)

    def div_cls(self):
        return self.div_stack[-1] if self.div_stack else ""

    def cur_has(self, *names):
        return any(n in self.div_cls() for n in names)

    # --- events ---
    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        cls = a.get("class", "")
        if tag in ("script", "style", "head", "nav", "footer"):
            self.skip_depth += 1
            return
        if tag == "br":
            self.emit("\n")
            return

        if tag == "div":
            self.div_stack.append(cls)
            if "who" in cls:
                self.who_skip += 1
                return
            if self.cur_has("navchips"):
                return
            if self.cur_has("eyebrow"):
                self.emit("\n\n**")
            elif self.cur_has("callout", "success-box", "danger-box"):
                self.emit("\n\n> ")
            elif self.cur_has("bubble"):
                who = "**Interviewer:** " if "them" in cls else "**You:** "
                self.pending_prefix = "\n\n> " + who
            elif self.cur_has("minicard"):
                self.emit("\n\n- ")
            elif self.cur_has("tstep"):
                self.emit("\n\n- **")
            elif self.cur_has("gterm"):
                self.emit("\n- ")
            elif ("code-label" in cls or "label" in cls) and len(self.div_stack) >= 2 and "minicard" in self.div_stack[-2]:
                self.emit("**")  # bold the label inside a minicard
            return

        if tag == "h2":
            self.emit("\n\n## ")
        elif tag == "h3":
            self.emit("\n\n### ")
        elif tag == "h4":
            self.emit("\n\n#### ")
        elif tag == "p":
            self.emit("\n\n")
        elif tag == "ul":
            self.list_depth += 1
            self.emit("\n")
        elif tag == "li":
            self.emit("\n" + "  " * (self.list_depth - 1) + "- ")
        elif tag in ("strong", "b"):
            if not self.in_cell:
                self.emit("**")
        elif tag in ("em", "i"):
            if not self.in_cell:
                self.emit("*")
        elif tag == "code":
            if not self.in_cell:
                self.emit("`")
        elif tag == "a":
            self.emit("[")
        elif tag == "span":
            self.span_stack.append(cls)
            if "pill" in cls:
                self.emit("`")
            elif "label" in cls:
                self.emit("**")
            elif "who" in cls:
                self.who_skip += 1
            elif "num" in cls:
                self.emit("**")  # closing marker handled on endtag with separator
        elif tag == "table":
            self.emit("\n\n")
        elif tag == "tr":
            self.row_cells = []
        elif tag in ("th", "td"):
            self.in_cell = True
            self.cell_text = []
        elif tag == "details":
            self.emit("\n\n<details>\n")
        elif tag == "summary":
            self.emit("\n<summary>")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "nav", "footer"):
            self.skip_depth = max(0, self.skip_depth - 1)
            return

        if tag == "div":
            cls = self.div_stack.pop() if self.div_stack else ""
            if "who" in cls:
                self.who_skip = max(0, self.who_skip - 1)
                return
            if "navchips" in cls:
                return
            if "eyebrow" in cls:
                self.emit("**\n")
            elif "minicard" in cls:
                pass
            elif "tstep" in cls:
                self.emit("\n")
            elif "day" in cls and "tstep" in self.div_cls():
                # close bold right after the day label (Within N days)
                self.emit("**\n")
            elif "gterm" in cls:
                self.emit("\n")
            elif "code-label" in cls or "label" in cls:
                self.emit("**")
            return

        if tag in ("h2", "h3", "h4"):
            self.emit("\n")
        elif tag == "p":
            self.emit("\n")
        elif tag == "ul":
            self.list_depth = max(0, self.list_depth - 1)
            self.emit("\n")
        elif tag in ("strong", "b", "em", "i", "code"):
            if not self.in_cell:
                self.emit("**" if tag in ("strong", "b") else ("`" if tag == "code" else "*"))
        elif tag == "span":
            cls = self.span_stack.pop() if self.span_stack else ""
            if "pill" in cls:
                self.emit("`")
            elif "label" in cls:
                self.emit("**")
            elif "who" in cls:
                self.who_skip = max(0, self.who_skip - 1)
            elif "num" in cls:
                self.emit("** ")
        elif tag == "a":
            self.emit("]")
        elif tag == "tr":
            self.table_rows.append(list(self.row_cells))
        elif tag in ("th", "td"):
            self.in_cell = False
            self.row_cells.append(" ".join("".join(self.cell_text).split()))
        elif tag == "table":
            rows = self.table_rows
            if rows:
                header = rows[0]
                self.emit("| " + " | ".join(header) + " |\n")
                self.emit("|" + "|".join(["---"] * len(header)) + "|\n")
                for r in rows[1:]:
                    while len(r) < len(header):
                        r.append("")
                    self.emit("| " + " | ".join(r) + " |\n")
            self.table_rows = []   # reset so the next table doesn't inherit rows
            self.emit("\n")
        elif tag == "details":
            self.emit("\n</details>\n")
        elif tag == "summary":
            self.emit("</summary>")

    def handle_data(self, data):
        if self.skip_depth > 0 or self.who_skip > 0:
            return
        if self.in_cell:
            self.cell_text.append(data)
            return
        if self.pending_prefix:
            self.emit(self.pending_prefix)
            self.pending_prefix = ""
        if not data.strip():
            return
        self.emit(data)


def clean(md: str) -> str:
    md = re.sub(r"\n{3,}", "\n\n", md)
    md = re.sub(r"[ \t]+\n", "\n", md)
    md = re.sub(r"([*`])\s+\1", "", md)          # "** **" -> ""
    # Remove navchips line (may be glued to "Section N" after it)
    md = re.sub(r"^\[Your Role\].*?\[Glossary\]\s*", "", md, flags=re.M | re.S)
    md = re.sub(r"^   \|", "|", md, flags=re.M)   # table leading spaces
    # ASI minicards: "- ASI03**Identity**" -> "- **ASI03 — Identity**"
    md = re.sub(r"^- ASI(\d{2})\*\*(.+?)\*\*\s*$",
                lambda m: f"- **ASI{m.group(1)} — {m.group(2)}**", md, flags=re.M)
    # Timeline steps: "- **Within 30 days\n\ntext\n**" -> "- **Within 30 days**\n\ntext"
    md = re.sub(r"^- \*\*([^\n]+)\n\n(.*?)\n\*\*$",
                lambda m: f"- **{m.group(1)}**\n\n{m.group(2)}", md, flags=re.M | re.S)
    # Eyebrow section markers (possibly with stray asterisks/whitespace and "· brief" suffixes)
    md = re.sub(r"^\s*\*{0,2}Section \d+[^\n]*\*{0,2}\s*$", "", md, flags=re.M)
    # Pill row: backticked inline chips -> bullet list
    md = re.sub(r"^`([^`]+)`(?:`([^`]+)`)?(?:`([^`]+)`)?(?:`([^`]+)`)?\s*$",
                lambda m: "\n".join(f"- {x.strip()}" for x in m.groups() if x and x.strip()),
                md, flags=re.M)
    # Callout label lines: "> Open-weight vs proprietary\n        text" -> "> **Label**\n> text"
    md = re.sub(r"^> ([^*\n][^\n]*?)\n\s{4,}(.+)$",
                lambda m: f"> **{m.group(1).strip()}**\n> {m.group(2).strip()}", md, flags=re.M)
    # Glossary double asterisks from <b> inside gterm: "- ****X** ..." -> "- **X** ..."
    md = re.sub(r"^- \*\*\*\*(.+?)\*\*\*", r"- **\1**", md, flags=re.M)
    # Collapse any stray asterisk runs (e.g. **** from nested <b> inside bold labels)
    md = re.sub(r"\*{3,}", "**", md)
    md = re.sub(r"\n{3,}", "\n\n", md)
    return md.strip() + "\n"


def main():
    ap = argparse.ArgumentParser(description="Convert styled HTML pack to Joplin Markdown")
    ap.add_argument("src", help="path to the input HTML file")
    args = ap.parse_args()
    html = open(args.src, encoding="utf-8").read()
    p = PackParser()
    p.feed(html)
    print(clean("".join(p.out)))


if __name__ == "__main__":
    main()
