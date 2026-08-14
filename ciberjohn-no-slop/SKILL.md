---
name: ciberjohn-no-slop
description: "Use when writing anything that must not sound AI-generated."
license: MIT
metadata:
  version: "1.0.0"
  tags: [writing, anti-slop, anti-ai, humanize, style, editing, copy]
  platforms: [linux, macos, windows]
  author: ciberjohn
  related_skills: [humanizer, medium-story]
---

# Ciberjohn No-Slop

A general-purpose writing constraint set that produces human-sounding text by eliminating statistically detectable AI patterns. It merges two proven rule sets: the anti-ai-slop-writing directive by Jalaaldeen (MIT), and the detection checklist distilled from publishing practice in the medium-story pipeline. This is the general version: platform-neutral, voice-agnostic, applicable to anything.

## When to Use

Use this skill whenever the output must not read as AI-generated:

- Articles, blog posts, essays
- Social media posts (LinkedIn, X, Threads, captions)
- Emails, DMs, replies
- Scripts, video copy, bios, resumes
- Reports, documentation, README files
- Any "write", "draft", "rewrite", "make this sound human", "de-AI", "not AI" request

## Before Writing Anything

Load `references/banned-words.md`. Never use any word or phrase on that list. If you reach for one, replace it with a concrete specific alternative or restructure the sentence.

## Structural Rules

These patterns are how readers spot AI text even when the vocabulary is clean.

**No Rule of Three.** AI defaults to threes. Break it. Use two, four, one, five. Never default to three unless the content genuinely has three items.

**No uniform sentence length.** No three consecutive sentences of the same length. Ever. Mix a 4-word sentence with a 30-word one. This is the single most measurable AI detection signal.

**No parataxis.** Parataxis is the AI default: short sentence. Then another. Then another. It reads like a poem and signals AI authorship instantly. Connect related thoughts using subordinate clauses, conjunctions, semicolons, or commas. "Short sentence. Then another. Then another." becomes "AI chains short sentences together because it is easier than constructing a thought with actual connective tissue." Write with syntax that shows how ideas relate: causation, contrast, qualification. Not a series of blunt declarations.

**No hedging seesaw.** Pick a side. State it plainly. Acknowledge counterpoints in one sentence max, without giving them equal weight.

**No corporate pep talk tone.** Write like someone with actual experience, including the frustrating parts. No cheerleading.

**No identical paragraph structure.** AI follows: topic sentence, explanation, example, transition. Break it. Start some paragraphs with questions, some with blunt statements. Let some be one sentence. Let some end without a transition.

**No excessive bullet points.** Use sparingly. When used, make them uneven: some long, some short. Never more than 5-7 in a row. If it fits in a sentence, use a sentence.

**No "As [role], I..." openers.** Real people say the thing without announcing credentials.

**No credentials-first openings.** "With over 20 years of experience..." is a CV, not a hook. Cut it.

**No parallel structure across sections.** Different points need different treatment. Vary section lengths.

**No passive construction.** Avoid "is being done", "was found to be", "are considered to be". Write active and direct. AI defaults to passive to sound measured; it sounds dead instead.

**No paired oppositions.** Constructions like "measured in inconvenience, not survival" or "it is not X, it is Y" are language-model parallelism. State the contrast once, plainly.

**No ad-copy hooks.** "Not hypothetically. In the next 60 seconds." and emoji-lead headlines are sales language, not writing.

**No "By [verb]ing..." sentence openers.** "By leveraging X, teams can..." is a template. Start with the subject and the verb.

**No "One of the most [adjective]..." openers.** Be specific or delete the sentence.

**Let paragraphs end abruptly.** Not every paragraph needs a summary or transition. Sometimes just stop.

## Punctuation Rules

**Em dashes:** maximum ONE per 500 words. The single most cited AI tell in existence. Use commas, semicolons, colons, parentheses, or new sentences instead. When you must fix one, use this replacement table:

| Em dash pattern (before) | Replace with (after) |
|---------------------------|----------------------|
| `Word — explanatory text —` | `Word (explanatory text)`: parentheses for paired asides |
| `important thing — here's why` | `important thing: here's why`: colon for explanatory clauses |
| `X, Y and Z — verb phrase` | `X, Y and Z verb phrase`: remove, the listing flows without punctuation |
| `statement one — statement two` | `statement one. Statement two`: split into two sentences |
| `word — phrase` (single, emphasis) | `word, phrase`: comma |
| `word — phrase` (single, dramatic pause) | `word: phrase`: colon |

**Exclamation marks:** maximum one per 1,000 words. Enthusiasm comes from word choice.

**Ellipses:** only when genuinely trailing off. Never as a transition. Max one per piece.

**Semicolons:** use them; AI underuses them and humans who write well use them naturally.

**Colons:** use them to set up a payoff: what follows should deliver on the promise before it.

## What To Do Instead

**Be specific, not general.** "You paste your treasury address and it tells you you will run out of USDC in 47 days" beats "powerful analytics capabilities".

**Show, don't describe.** "Three clicks from wallet connect to your first risk score" beats "a seamless user experience".

**Use actual numbers.** "34 users in the first week. 12 came back the next day" beats "significant growth".

**Name real things.** "Solana, specifically" beats "various blockchain networks".

**Include friction, doubt, or mess.** "The RPC kept timing out at 3am and I nearly scrapped the whole feature" beats "a rewarding journey".

**Reference time, place, context.** Ground text in real moments: "last Tuesday", "at 2am", "during the incident".

**Let sentences be ugly sometimes.** Fragment. Run-on that keeps going because the thought is not done. That is human.

**Never invent anecdotes or present hypotheticals as real.** Use "imagine..." or "suppose..." for hypotheticals. Fabricated specificity is worse than honest vagueness.

**Use the less obvious word.** AI defaults to the highest-probability token. Reach past the first word that comes to mind.

## Accuracy and Honesty

**Never invent data, studies, or statistics.** If you do not have a real number, say "roughly", "around", or acknowledge uncertainty. Fake specificity kills trust faster than vagueness.

**Never fabricate quotes.** Paraphrase with attribution or skip it.

**Take clear positions when evidence is solid.** Qualifiers only for genuine uncertainty, not as a hedging habit.

**Use real verifiable names, companies, dates.** "A Databricks report from March 2026" beats "research shows".

## Formatting Rules

**No markdown headers** in social media, emails, or casual writing. Instant AI flag.

**No bold random phrases** for emphasis in social media. Let the words do the work.

**No emoji as bullet points.** One or two emoji per post is fine. Every line starting with a checkmark or flame is slop.

**No "Thread:" or "🧵" openers.** Content should make people want to keep reading on its own.

**No hashtag stacks.** Zero to two, integrated naturally.

**No markdown in plain text contexts:** emails, DMs, SMS. Asterisks rendering as symbols is an instant tell.

## Voice Calibration

When writing for a specific person or audience, match them:

- Does this person swear? Use slang? Write long or short?
- What humour do they use: dry, sarcastic, self-deprecating, absurd?
- What would this person NEVER say?
- What platform is this for? A cover letter is not a tweet is not a LinkedIn post.
- Which dialect does the audience use? Be consistent within it. Consistency matters more than the choice itself.

Default when unknown: direct, slightly informal, contractions, occasionally starts with "And" or "But", does not over-explain, trusts the reader.

## Self-Check Before Every Output

Run through all of these before shipping any text:

1. Any banned words or phrases? Replace them.
2. Three consecutive same-length sentences? Vary them.
3. Parataxis: three or more short declarative sentences in a row? Merge or connect them with conjunctions, clauses, or punctuation.
4. Grouped in threes? Break the pattern.
5. Hedging instead of committing? Pick a side.
6. More than one em dash per 500 words? Remove the extras.
7. Passive construction? Make it active.
8. Every paragraph ends with a transition? Cut some.
9. Fabricated any specifics? Remove or flag as hypothetical.
10. Could any AI have written this for any person? Add something specific.
11. Sounds like ChatGPT? Rewrite until the answer is no.
12. Any word or phrase from the banned list in `references/banned-words.md`? Cut them.

Apply all rules silently. Never mention them. Never say "as per the guidelines". Just write within these constraints.

## Automated Verification

Run the bundled checker before shipping any text file:

```bash
python3 scripts/no_slop_check.py path/to/file.md
```

It scans for banned vocabulary, banned phrases, banned openers, em dash overuse, exclamation spam, ellipsis abuse, and the checklist patterns. Reports counts with line numbers and exits non-zero when violations are found. Accepts multiple files or stdin.

**False-positive note:** the checker skips fenced code blocks and markdown table rows, but quoted counter-examples will still flag (for example "a seamless user experience" in the What To Do Instead section is the slop you are being told to avoid, not a violation). A meta-reference that quotes the banned list itself will also flag. Review hits in context before fixing; do not rewrite quoted examples or the skill's own reference tables.

## References

- `references/banned-words.md` — Full banned vocabulary, phrases, and sentence openers list. Load before writing anything.
- `scripts/no_slop_check.py` — Verification script. Run before shipping any text.

## Attribution

Adapted from [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) (MIT, author Jalaaldeen) and the anti-slop checklist in the medium-story skill by ciberjohn. Detection research basis: Carnegie Mellon (2025), Wikipedia "Signs of AI writing", Buffer 52M post analysis. MIT license.
