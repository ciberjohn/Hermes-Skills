# Revisor Methodology

> Referenced by `medium-story/SKILL.md` in the Revisor agent description.
> **CUSTOMISE** — Adapt the verification patterns to your tools.

## Structured Fact-Checking Process

### 1. GitHub API Verification

```bash
# Check repository star count
curl -s "https://api.github.com/repos/OWNER/REPO" | jq '.stargazers_count'

# Check fork count
curl -s "https://api.github.com/repos/OWNER/REPO" | jq '.forks_count'
```

### 2. British English / Americanism Detection

```bash
# Flag -ize endings (should be -ise in British English)
grep -nP '\b\w+ize\b' article.md

# Flag American spellings
grep -nP '\bcolor\b|\bdefense\b|\borganization\b|\brealize\b' article.md

# Flag -or endings
grep -nP '\bbehavior\b|\bfavor\b|\bhonor\b|\blabor\b|\bneighbor\b' article.md
```

### 3. Dash Audit

```bash
# Find em dashes in body text (exclude Sources section)
sed -n '1,/^## Sources$/p' article.md | grep -n $'\xe2\x80\x94'
```

### 4. Source URL Validation

```bash
# Check URL returns HTTP 200
curl -s -o /dev/null -w "%{http_code}" "URL"
```

### 5. Report Format

The Revisor produces a structured report with sections:
- **Stats Verified** — each stat with pass/fail/close-enough
- **Spelling** — British English compliance
- **Americanisms** — any flagged
- **Dash Check** — mid-sentence em dash violations
- **Issues Found** — actionable items only
