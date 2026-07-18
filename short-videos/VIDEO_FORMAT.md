# Video Script Format Reference

## Overview

Every video script follows a 6-block, 90-second format designed for universal teleprompter use across HeyGen, Instagram Reels, LinkedIn Video, and YouTube Shorts.

**Spoken word count target: 200–230 words** — this fits comfortably within 90 seconds at a natural speaking pace (roughly 2.5–2.7 words per second).

All content is British English, platform-neutral, and written in a practitioner's voice.

---

## Script Structure

```markdown
TOPIC: [topic name]
SPOKEN WORD COUNT TARGET: 200–230 words
PLATFORMS: Instagram Reels · LinkedIn Video · YouTube Shorts

---

[HOOK] 00:00–00:05        (5 seconds)
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[SETUP] 00:05–00:20       (15 seconds)
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[INSIGHT 1] 00:20–00:40   (20 seconds)
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[INSIGHT 2] 00:40–01:00   (20 seconds)
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[PAYOFF] 01:00–01:20      (20 seconds)
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

[CTA] 01:20–01:30         (10 seconds)
Spoken: ...
On-screen text: ...
Stage direction: ...
B-roll / graphic: ...

---

CAPTION (universal — use for all three platforms):
[3-5 lines: hook, core insight, 5 hashtags. No "link in bio".]

THUMBNAIL CONCEPT:
[One sentence describing a still frame that works as a cover image across all platforms.]
```

---

## Block Breakdown

### [HOOK] 00:00–00:05
- **Duration:** 5 seconds
- **Purpose:** Grab attention. The viewer decides whether to watch in 1–2 seconds.
- **Spoken:** Short, sharp statement of the unexpected truth. A bold claim, provocative question, or counterintuitive fact.
- **On-screen text:** Reinforce the spoken word — never duplicate verbatim. Max 6 words.
- **Rules:** No fluffy openers. No "In today's digital landscape". No "With over 20 years of experience". No ad-copy hooks.

### [SETUP] 00:05–00:20
- **Duration:** 15 seconds
- **Purpose:** Build context. Why does this matter? Who is affected?
- **Spoken:** 2–3 sentences establishing the landscape or problem.
- **B-roll/graphic:** Industry logos, stock footage, or relevant screenshot.

### [INSIGHT 1] 00:20–00:40
- **Duration:** 20 seconds
- **Purpose:** First concrete point. A statistic, a mechanism, or a real-world example.
- **Spoken:** Deliver the fact or argument clearly. No jargon dumps.
- **On-screen text:** Punchy reinforcement of the key number or claim.
- **Rules:** Facts should be verifiable, UK/EU sources preferred.

### [INSIGHT 2] 00:40–01:00
- **Duration:** 20 seconds
- **Purpose:** Second concrete point. Deeper implication or additional supporting evidence.
- **Spoken:** Builds on Insight 1 without repetition.
- **B-roll/graphic:** Switch visual context — maybe an animation, diagram, or contrasting image.

### [PAYOFF] 01:00–01:20
- **Duration:** 20 seconds
- **Purpose:** Synthesise the two insights. Drive the thesis home.
- **Spoken:** The "so what" — why the viewer should care and what they should take away.
- **On-screen text:** The core message, simplified to one line.
- **Stage direction:** Lean forward, slow down delivery for emphasis.

### [CTA] 01:20–01:30
- **Duration:** 10 seconds
- **Purpose:** One clear, platform-neutral call to action.
- **Spoken:** Direct and short. "Follow for more." / "Drop a comment." / "Save this one."
- **Rules:** No "swipe up". No "link in bio". No "click the link in comments". Platform-neutral only.

---

## Script Rules

### Spoken Text
- Sound natural when read aloud at a steady pace — no bullet points, no headers, no jargon dumps
- 15–25 words per sentence
- No mid-sentence dashes — use commas, colons, or semicolons
- British English throughout (-ise not -ize, colour, favour, behaviour, defence)
- No AI transition phrases ("Here's the thing", "What this means is", "Here's what matters")
- No fluffy openers
- Contractions are encouraged (don't, won't, it's, can't)

### On-Screen Text
- Max 6 words per frame
- Reinforce the spoken word — don't repeat it verbatim
- Legible font, high contrast, central placement (for mobile 9:16 screens)

### Stage Directions
- Brief cues for the presenter: "lean forward slightly", "pause for emphasis", "gesture to upper-left"
- Keep it minimal — 1–5 words

### B-Roll / Graphics
- Practical, producible suggestions: "terminal output animation", "NCSC logo fade in", "scrolling code snippet"
- Avoid abstract concepts without visual representation
- Provide enough detail for an editor or AI generation tool

### Caption
- 3–5 lines
- Hook line, core insight, call to action, 5 hashtags
- No "link in bio" or website URL
- Universal — works on all platforms with auto-generated captions off

### Thumbnail Concept
- One sentence describing a still frame
- Works as a cover image across Instagram Reels, LinkedIn Video, and YouTube Shorts
- High contrast, single focal point, readable text overlay if used

---

## Word Count Verification

Use this Python script after every draft to verify the spoken word count is within 200–230:

```bash
python3 -c "
import sys, re
text = open(sys.argv[1]).read()
blocks = re.findall(r'^Spoken:\\s*(.*?)$', text, re.MULTILINE)
total = sum(len(b.split()) for b in blocks)
print(f'Spoken word count: {total}')
if total < 200: print('TOO LOW — expand spoken sections')
elif total > 230: print('TOO HIGH — trim spoken sections')
else: print('Within target range.')
"
```

Run this after every edit until the count passes.

---

## Quality Criteria

Each script is checked against these 8 criteria:

1. **Fact accuracy** — every statistic and claim must be verifiable
2. **Spoken word count** — 200–230 words
3. **Timing sense-check** — the script should feel natural at 90 seconds
4. **British English** — zero Americanisms
5. **Dash check** — zero mid-sentence em dashes or en dashes
6. **LinkedIn character count** (for the companion post) — ≤3,000 characters
7. **Hook strength** — rated 1–5; must land within 3 seconds
8. **CTA check** — no platform-specific mechanics (no "swipe up", no "link in bio")

---

## Example Script Skeleton

```
TOPIC: Cloud Security Misconfigurations
SPOKEN WORD COUNT TARGET: 200–230 words
PLATFORMS: Instagram Reels · LinkedIn Video · YouTube Shorts

---

[HOOK] 00:00–00:05
Spoken: 95% of cloud security breaches start with a misconfiguration — not a hacker.
On-screen text: 95% of breaches = misconfiguration
Stage direction: Look directly at camera
B-roll / graphic: Quick montage of cloud provider logos

[SETUP] 00:05–00:20
Spoken: Teams spend millions on firewalls and endpoint protection. But the thing that actually leaks data? An S3 bucket left open over a long weekend.
On-screen text: The weakest link
Stage direction: Lean forward
B-roll / graphic: Open AWS S3 console screenshot

[INSIGHT 1] 00:20–00:40
Spoken: According to the NCSC's latest threat report, misconfigured cloud storage is now the single most common vector for data exposure in the UK public sector.
On-screen text: NCSC — most common vector
Stage direction: Count on fingers for emphasis
B-roll / graphic: NCSC logo, stats overlay

[INSIGHT 2] 00:40–01:00
Spoken: The fix isn't another tool. It's infrastructure-as-code policies that prevent anyone from deploying a public bucket in the first place.
On-screen text: Policy, not perimeter
Stage direction: Gesture to show contrast
B-roll / graphic: Terraform or Pulumi config file scrolling

[PAYOFF] 01:00–01:20
Spoken: Cloud security is not about buying better tools. It is about making the default setting the safe setting. Every time.
On-screen text: Make safe the default
Stage direction: Slow down, pause after "every time"
B-roll / graphic: Split screen: open bucket vs locked bucket

[CTA] 01:20–01:30
Spoken: Follow for more infrastructure security insights you won't find in a vendor whitepaper.
On-screen text: Follow for more
Stage direction: Brief nod, hold eye contact
B-roll / graphic: Channel logo / end card

---

CAPTION:
95% of cloud breaches start with misconfiguration — not hackers.
The fix? Policy over perimeter. Infrastructure-as-code, not another dashboard.
#CloudSecurity #DevOps #InfoSec #Infrastructure #NCSC

THUMBNAIL CONCEPT:
Close-up of padlock icon overlaying a cloud network diagram, warm amber alert border, bold white text "95% DON'T HACK — THEY MISCONFIGURE"
```
