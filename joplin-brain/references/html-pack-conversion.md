# Converting Claude-generated HTML packs to Joplin Markdown

Users regularly create rich, styled HTML "prep packs" with Claude (interview prep, course materials, client briefings). They use div-class-based styling — cards, callouts, chat bubbles, minicards, tables, glossary — and need faithful conversion into clean Joplin Markdown, not a raw HTML paste.

**Worked example:** a governance prep pack → note in a domain folder. Converter: `scripts/html_pack_to_markdown.py`.

## When to use

- User sends/mentions an `.html` file that is a styled document (Claude-generated or otherwise), and the intent is "have this in my second brain" — NOT a raw capture-to-INBOX, but a curated note (see KNOWLEDGE-BASE BUILD protocol).
- Source is wherever the HTML arrived (downloads, chat attachments, agent cache). Adjust path per session.

## Recipe

1. **Copy the converter** to a temp location if the repo copy isn't editable in place: `cp scripts/html_pack_to_markdown.py /tmp/<name>_convert.py` (edit /tmp copy, re-save to repo once clean).
2. **Run** `python3 scripts/html_pack_to_markdown.py <input.html>` → inspect output in sections. The parser is class-aware (div_stack, span_stack, `who_skip`, `pending_prefix`, `in_cell`); it emits:
   - h2/h3 headings, bullet lists (ul, qlist, minicards, tsteps, glossary)
   - markdown tables (thead/tbody)
   - blockquotes for callouts / success / danger boxes
   - chat bubbles as `> **Interviewer:** …` / `> **You:** …`
   - `<details>/<summary>` preserved for collapsible sample exchanges
   - pill chips as backticked inline items
3. **Post-process with `clean()`** in the converter (it already does):
   - strip navchips line (`[Your Role]…[Glossary]`), `Section N` eyebrows
   - format `ASI03**Identity**` → `- **ASI03 — Identity**`
   - collapse stray `***` runs → `**`
   - fix callout label lines → `> **Label**`
4. **Create the Joplin note**: strip the duplicated `<h1>` title line (it becomes the note title), prepend a metadata header block (Source / Role / Context), create in a dedicated folder if the pack is a new domain, tag with domain + topic as appropriate.
5. **Verify**: `get_note(id)` with NO fields arg (custom fields drop `body`), confirm section count / word count, then AGENT LOG entry.

## Pitfalls (all hit in practice)

- **`handle_endtag` gets no attrs.** Span classes must be tracked on their own stack (`span_stack`) — pushing in starttag, popping in endtag — or the endtag can't know whether to close backticks vs bold.
- **Table rows inherit across tables.** Reset `self.table_rows = []` after emitting a table or the NEXT table duplicates the previous one's rows.
- **Formatting markers leak into table cells.** Suppress `**`/`` ` ``/`*` emission while `in_cell` — data goes to `cell_text`, markers would corrupt the markdown table.
- **Glossary double-bold.** `<div class="gterm">` wrapper + inner `<b>` produces `****` — gterm start/end should NOT emit their own bold; let the inner `<b>` handle it, then collapse `\*{3,}` → `**`.
- **Timeline steps.** Bold must close right after the day label (`Within 30 days**`) — close on the `day` div endtag, not the `tstep` endtag.
- **Bubble `.who` divs.** The name div inside a bubble must be skipped (`who_skip`) — the `> **Interviewer:**` prefix is already emitted by the bubble div handler; leaving the `.who` text in produces `**Interviewer:** Head of Infrastructure & SecurityEveryone talks…`.
- **Naive datetime.** Cloudflare/OpenAI feeds emit naive dates; the collector must attach `tzinfo=utc` to parsed dates missing it or recency filtering crashes with `can't compare offset-naive and offset-aware datetimes`.
- **Verify visually per section** before creating the note: tables, cards, callouts, glossary, questions list. Each class needs its own formatting check.
