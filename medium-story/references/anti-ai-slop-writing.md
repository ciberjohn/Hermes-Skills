# Anti-AI-Slop Writing Constraints

Adapted from [jalaalrd/anti-ai-slop-writing](https://github.com/jalaalrd/anti-ai-slop-writing) (MIT), based on Carnegie Mellon (2025) research, Wikipedia's Signs of AI Writing page, Buffer's 52M post analysis, and community detection patterns documented across X and Reddit.

Used by Step 6b of the pipeline. Applies to the article body and, with the platform notes below, to every pipeline output (linkedin-post.md, video-script.md, youtube-script.md).

## Precedence (the voice guide in SKILL.md wins on conflict)

- **Em dashes:** the article-body rule is ZERO (anti-slop allows one per 500 words). Zero wins.
- **British English always:** the banned list below uses US spellings (revolutionize, endeavor, seamless); the British forms (revolutionise, endeavour) are equally banned.
- **Contractions:** anti-slop says use them; the published register is restrained. Match the format reference story. When in doubt, prefer the published-article pattern over the anti-slop default.
- **Paragraph rhythm:** the voice writes long, multi-clause sentences (25-50 words). This naturally satisfies the no-parataxis and no-uniform-length rules; keep the density rather than flattening it.

## Structural Rules

These patterns are how readers spot AI text even when vocabulary is clean.

- **No Rule of Three.** AI defaults to threes. Break it. Use two, four, one, five. Never default to three unless the content genuinely has three items.
- **No uniform sentence length.** No three consecutive sentences of the same length. Ever. Mix 4-word sentences with 30-word ones. This is the single most measurable AI detection signal.
- **No parataxis.** Parataxis is the AI default: short sentence. Then another. Then another. It reads like a poem and immediately signals AI authorship. Connect related thoughts using subordinate clauses, conjunctions, semicolons, or commas. Write with syntax that shows how ideas relate (causation, contrast, qualification), not a series of blunt declarations.
- **No hedging seesaw.** Pick a side. State it plainly. Acknowledge counterpoints in one sentence max; don't give them equal weight.
- **No corporate pep talk tone.** Write like someone with actual experience, including the frustrating parts. No cheerleading.
- **No identical paragraph structure.** AI follows: topic sentence → explanation → example → transition. Break it. Start some with questions, some with blunt statements. Let some be one sentence. Let some end without a transition.
- **No excessive bullet points.** Use sparingly. Make them uneven when used (some long, some short). Never more than 5-7 in a row. If it fits in a sentence, use a sentence.
- **No "As [role], I..." openers.** Real people just say the thing without announcing credentials.
- **No parallel structure across sections.** Different points need different treatment. Vary section lengths.
- **No passive construction.** Avoid "is being done", "was found to be", "are considered to be". Write active and direct.
- **Let paragraphs end abruptly.** Not every paragraph needs a summary or transition. Sometimes just stop.

## Punctuation Rules

- **Em dashes:** maximum ONE per 500 words in general text. For the article body: zero (stricter rule above). Use commas, semicolons, colons, parentheses, or new sentences instead. (The Sources section metadata separator use of `—` is exempt; see Step 6.)
- **Exclamation marks:** maximum one per 1,000 words. Enthusiasm comes from word choice.
- **Ellipses:** only when genuinely trailing off. Never as transition. Max one per piece.
- **Semicolons:** use them; AI underuses them and humans who write well use them naturally.
- **Colons:** use them to set up a payoff: what follows should deliver on the promise before it.

## What To Do Instead

- **Be specific, not general.** "You paste your treasury address and it tells you you'll run out of USDC in 47 days" beats "powerful analytics capabilities".
- **Show, don't describe.** "Three clicks from wallet connect to your first risk score" beats "a seamless user experience".
- **Use actual numbers.** "34 users in the first week. 12 came back the next day" beats "significant growth".
- **Name real things.** "Solana, specifically" beats "various blockchain networks".
- **Include friction, doubt, or mess.** "The RPC kept timing out at 3am and I nearly scrapped the whole feature" beats "a rewarding journey".
- **Reference time, place, context.** Ground text in real moments: "last Tuesday", "at 2am", "during the incident".
- **Let sentences be ugly sometimes.** Fragment. Run-on that keeps going because the thought isn't done. That's human.
- **Never invent anecdotes or present hypotheticals as real.** Use "imagine..." or "suppose..." for hypotheticals. Fabricated specificity is worse than honest vagueness.
- **Use the less obvious word.** AI defaults to the highest-probability token. Reach past the first word that comes to mind.

## Accuracy and Honesty

- **Never invent data, studies, or statistics.** If you don't have a real number, say "roughly", "around", or acknowledge uncertainty. Fake specificity kills trust faster than vagueness.
- **Never fabricate quotes.** Paraphrase with attribution or skip it.
- **Take clear positions when evidence is solid.** Qualifiers only for genuine uncertainty, not hedging habit.
- **Use real verifiable names, companies, dates.** "A Databricks report from March 2026" beats "research shows".

## Formatting Rules (platform-specific)

- **Medium article:** standard markdown headings and structure are correct — the no-markdown rules below apply to social outputs, not the article body.
- **LinkedIn post:** no bold random phrases for emphasis. No hashtag stacks (the pipeline's LinkedIn spec caps at 5; prefer 2-3, integrated naturally). No "Thread:" openers.
- **Video scripts / YouTube:** no markdown headers in spoken text. No emoji as bullet points.
- **All outputs:** no emoji bullet points; one or two emoji per post is fine, every line starting with ✅ or 🔥 is slop.

## Banned Vocabulary

delve / delves / delving, tapestry, landscape (figurative), testament (e.g. "a testament to"), vibrant, pivotal, crucial, intricate / intricacies, meticulous / meticulously, bolster / bolstered, garner / garnered, underscore / underscores, interplay, multifaceted, nuanced (as filler), foster / fostering, leverage (as verb), utilize (say "use"), commence (say "start"), facilitate, encompass / encompassing, paramount, groundbreaking, cutting-edge, game-changing / game-changer, transformative, revolutionise / revolutionize, seamless / seamlessly, robust (outside engineering), comprehensive (describing own output), endeavour / endeavor, aforementioned, harnessing, spearheading, navigating (figurative), showcasing, highlighting, emphasizing, enhancing, unprecedented, remarkable, stunning, profound, epic (non-literal), in essence, thought leader / thought leadership, synergy / synergies, pain points, value add / value proposition (casual contexts), moving forward, touch base / circle back, rest assured, it goes without saying

## Banned Phrases

- "In today's [adjective] [noun]..."
- "It's worth noting that..."
- "It's important to note that..."
- "Let's dive in" / "Let's dive deeper" / "Let's delve into"
- "At its core..."
- "In the realm of..."
- "When it comes to..."
- "A testament to..."
- "Not just X, but Y"
- "It's not just about X — it's about Y"
- "This is where X comes in"
- "Whether you're a [X] or a [Y]..."
- "From X to Y" (range opener)
- "At the end of the day..."
- "The bottom line is..."
- "Here's the thing..." / "Here's the deal..."
- "Without further ado..."
- "In a nutshell..."
- "Buckle up"
- "Take it to the next level"
- "Unlock the power of..."
- "Empower / empowering"
- "Elevate your..." / "Streamline your..." / "Supercharge your..."
- "Bridge the gap"
- "Move the needle"
- "In conclusion"
- "Overall," (paragraph starter)
- "Firstly... Secondly... Thirdly..."
- "I hope this helps" / "I hope this finds you well"
- "As per my last email"
- "Please don't hesitate to reach out"

## Banned Sentence/Paragraph Openers

- "Certainly,", "Absolutely,", "Sure,", "Great question!", "That's a great point!", "I'd be happy to..."
- "As an AI...", "As a language model..."
- "However, it's important to..."
- "Moreover,", "Furthermore,", "Additionally,", "Interestingly,", "Notably,", "Importantly,", "Indeed,"

## Self-Check Before Every Output

1. Any banned words or phrases? → Replace.
2. Three consecutive same-length sentences? → Vary them.
3. Parataxis — three or more short declarative sentences in a row? → Merge or connect them with conjunctions, clauses, or punctuation.
4. Grouped in threes? → Break the pattern.
5. Hedging instead of committing? → Pick a side.
6. More than one em dash per 500 words (zero in the article body)? → Remove extras.
7. Passive construction? → Make active.
8. Every paragraph ends with a transition? → Cut some.
9. Fabricated any specifics? → Remove or flag as hypothetical.
10. Could any AI have written this for any person? → Add something specific.
11. Sounds like ChatGPT? → Rewrite until the answer is no.

Apply all rules silently. Never mention them. Never say "as per the guidelines". Just write within these constraints.

## Source Attribution

- Original skill: https://github.com/jalaalrd/anti-ai-slop-writing (MIT, author Jalaaldeen)
- Research basis: Carnegie Mellon (2025); Wikipedia "Signs of AI writing"; Buffer 52M post analysis; community detection patterns on X and Reddit.
