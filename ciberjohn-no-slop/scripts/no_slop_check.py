#!/usr/bin/env python3
"""no_slop_check.py — verify text against the ciberjohn-no-slop constraint set.

Scans files (or stdin) for banned vocabulary, banned phrases, banned openers,
em dash overuse, exclamation spam, ellipsis abuse, and checklist patterns.
Prints findings with line numbers and exits non-zero when violations are found.

Usage:
    python3 no_slop_check.py file.md [file2.md ...]
    cat draft.txt | python3 no_slop_check.py -
    python3 no_slop_check.py --help

Keep the pattern lists in sync with references/banned-words.md.
"""

import argparse
import re
import sys

BANNED_WORDS = [
    r"\bdelve[sd]?\b", r"\btapestr(?:y|ies)\b", r"\blandscape\b",
    r"\btestament\b", r"\bvibrant\b", r"\bpivotal\b", r"\bcrucial\b",
    r"\bintricat\w*\b", r"\bmeticulous\w*\b", r"\bbolster(?:ed|ing)?\b",
    r"\bgarner(?:ed|ing)?\b", r"\bunderscore[ds]?\b", r"\binterplay\b",
    r"\bmultifaceted\b", r"\bnuanced\b", r"\bfoster(?:ing|ed)?\b",
    r"\bleverage[ds]?\b", r"\butilize[ds]?\b", r"\bcommence[ds]?\b",
    r"\bfacilitate[ds]?\b", r"\bencompass\w*\b", r"\bparamount\b",
    r"\bgroundbreaking\b", r"\bcutting-edge\b", r"\bgame-?chang\w*\b",
    r"\btransformative\b", r"\brevolutioni[sz]e[ds]?\b", r"\bseamless\w*\b",
    r"\brobust\b", r"\bcomprehensive\b", r"\bendeavo\w*\b",
    r"\baforementioned\b", r"\bharnessing\b", r"\bspearheading\b",
    r"\bnavigating\b", r"\bshowcas\w*\b", r"\bhighlight\w*\b",
    r"\benhanc\w*\b", r"\bunprecedented\b",
    r"\bremarkable\b", r"\bstunning\b", r"\bprofound\b", r"\bepic\b",
    r"\bsynerg\w*\b", r"\bpain points\b", r"\bvalue add\b",
    r"\bmoving forward\b", r"\btouch base\b", r"\bcircle back\b",
    r"\brest assured\b", r"\bit goes without saying\b",
    r"\bemphasi[sz]ing\b",
]

BANNED_PHRASES = [
    r"in today's", r"in an era of", r"it's worth noting", r"it is worth noting",
    r"it's important to note", r"it is important to note",
    r"let's dive", r"let us dive", r"delve into", r"at its core",
    r"in the realm of", r"when it comes to", r"a testament to",
    r"not just\b.*\bbut\b", r"not only\b.*\bbut also\b",
    r"this is where\b.*\bcomes in", r"whether you'?re a",
    r"at the end of the day", r"the bottom line is", r"here's the thing",
    r"here's the deal", r"here's what matters", r"what this means is",
    r"i need you to understand", r"without further ado", r"in a nutshell",
    r"buckle up", r"next level", r"unlock the power", r"empower\w*",
    r"elevate your", r"streamline your", r"supercharge your",
    r"bridge the gap", r"move the needle", r"in conclusion",
    r"^overall,", r"^firstly", r"^secondly", r"^thirdly",
    r"i hope this helps", r"i hope this finds you well",
    r"as per my last email", r"don't hesitate to reach out",
    r"in order to",
]

BANNED_OPENERS = [
    r"^certainly,", r"^absolutely,", r"^sure,", r"^great question!",
    r"^that's a great point!", r"^i'?d be happy to",
    r"^as an ai\b", r"^as a language model",
    r"^however, it's important", r"^moreover,", r"^furthermore,",
    r"^additionally,", r"^interestingly,", r"^notably,", r"^importantly,",
    r"^indeed,", r"^with over\s+\d+\s+years", r"^one of the most",
    r"^by [A-Za-z]+ing\b",
]

CHECKLIST_PATTERNS = [
    ("it is worth", r"\bit is worth\b"),
    ("important to note", r"\bimportant to note\b"),
    ("in conclusion", r"\bin conclusion\b"),
    ("in today's [X]", r"\bin today's\b"),
    ("in an era of", r"\bin an era of\b"),
]

EM_DASH = "\u2014"
ELLIPSIS = "\u2026"


def scan(text, source):
    findings = []          # (category, line_no, pattern)
    counters = {"em_dash": 0, "exclamation": 0, "ellipsis": 0, "words": 0}

    lines = text.splitlines()
    in_fence = False
    for idx, line in enumerate(lines, 1):
        stripped = line.strip()
        # Skip fenced code blocks entirely (code, not prose).
        if stripped.startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        # Skip markdown table rows: quoted/format content, not prose.
        if stripped.startswith("|"):
            continue

        low = line.lower()

        for pattern in BANNED_WORDS:
            if re.search(pattern, low):
                findings.append(("banned word", idx, pattern.strip("\\b^$")))
        for pattern in BANNED_PHRASES:
            if re.search(pattern, low):
                findings.append(("banned phrase", idx, pattern))
        for pattern in BANNED_OPENERS:
            if re.search(pattern, low):
                findings.append(("banned opener", idx, pattern))
        for name, pattern in CHECKLIST_PATTERNS:
            if re.search(pattern, low):
                findings.append(("checklist", idx, name))

        counters["em_dash"] += line.count(EM_DASH)
        counters["ellipsis"] += line.count(ELLIPSIS)
        counters["exclamation"] += line.count("!")
        counters["words"] += len(line.split())

    # Deduplicate identical (category, line, pattern) triples.
    seen = set()
    unique = []
    for item in findings:
        if item not in seen:
            seen.add(item)
            unique.append(item)

    return unique, counters


def main():
    parser = argparse.ArgumentParser(
        description="Check text for AI-slop patterns (ciberjohn-no-slop).")
    parser.add_argument("files", nargs="*", help="Files to scan, or - for stdin")
    args = parser.parse_args()

    total_violations = 0
    for source in args.files or ["-"]:
        if source == "-":
            text = sys.stdin.read()
            label = "<stdin>"
        else:
            with open(source, encoding="utf-8") as fh:
                text = fh.read()
            label = source

        findings, counters = scan(text, source)
        violations = len(findings)

        em_limit = max(1, counters["words"] // 500)
        ex_limit = max(1, counters["words"] // 1000)
        if counters["em_dash"] > em_limit:
            violations += 1
            print(f"{label}: em dash overuse: {counters['em_dash']} found, "
                  f"limit {em_limit} per {counters['words']} words")
        if counters["exclamation"] > ex_limit:
            violations += 1
            print(f"{label}: exclamation overuse: {counters['exclamation']} found, "
                  f"limit {ex_limit} per {counters['words']} words")
        if counters["ellipsis"] > 1:
            violations += 1
            print(f"{label}: ellipsis overuse: {counters['ellipsis']} found, limit 1")

        if findings:
            print(f"{label}: {len(findings)} pattern hits:")
            for category, line_no, pattern in findings:
                snippet = lines_of(text, line_no)
                print(f"  L{line_no:>4} [{category}] {pattern}  :: {snippet}")
        if violations == 0:
            print(f"{label}: clean")

        total_violations += violations

    if total_violations:
        print(f"\n{total_violations} violation(s) found. Review and fix before shipping.")
        return 1
    print("\nNo violations found.")
    return 0


def lines_of(text, line_no):
    try:
        return text.splitlines()[line_no - 1].strip()[:90]
    except IndexError:
        return ""


if __name__ == "__main__":
    sys.exit(main())
