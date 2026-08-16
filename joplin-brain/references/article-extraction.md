# Article extraction → Joplin knowledge note (worked recipe 2026-08-14)

Used to seed a knowledge base from a vendor security blog post. Works when the page is plain HTML (no JS-rendered body).

## 1. Fetch with browser UA (curl works for most blog platforms)

```bash
curl -sL -m 30 -A "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36" \
  "https://<url>" -o /tmp/article.html -w "HTTP %{http_code} | %{size_download} bytes\n"
```

## 2. Extract the article body (Python)

Trap: generic content divs vary by CMS. Some blogs have NO `article-content` / `entry-content` class on the article body — instead slice from the first `<article` tag:

```python
import re, html
raw = open('/tmp/article.html', encoding='utf-8', errors='ignore').read()
body = raw[raw.find('<article'):]                 # ← key: start at <article
body = re.sub(r'<script.*?</script>', ' ', body, flags=re.S)
body = re.sub(r'<style.*?</style>', ' ', body, flags=re.S)
body = re.sub(r'<h([1-6])[^>]*>', lambda m: '\n\n' + '#'*int(m.group(1)) + ' ', body)
body = re.sub(r'<li[^>]*>', '\n- ', body)
body = re.sub(r'<p[^>]*>', '\n', body)
body = re.sub(r'<br\s*/?>', '\n', body)
body = re.sub(r'<[^>]+>', ' ', body)
body = html.unescape(body)
body = re.sub(r'[ \t]+', ' ', body)
body = re.sub(r'\n\s*\n+', '\n\n', body)
open('/tmp/article_text.txt','w').write(body)
print(body[:6000])
```

## 3. Finding links inside body text

Trap: naive regex `<a href="...">([^<]*)</a>` fails when anchor text contains nested tags (e.g. `<a><strong>Pattern & Practice</strong></a>`). Instead find the keyword in raw HTML and read the href from context:

```python
i = raw.find('Pattern')
while i != -1:
    print(raw[max(0,i-400):i+400])   # href visible in surrounding context
    i = raw.find('Pattern', i+1)
```

## 4. Distill (per KNOWLEDGE-BASE BUILD protocol)

Structure: metadata block (authors, date, read time, URL) → one-line thesis → key concepts → best practices → anti-patterns → action plan → **Implications for me** (agent ops angle + user business angle). Create with `j.create_note(title, body, folder_id=fid, tags=[...], source=<url>)`.

## Related link extraction notes

- Vendor blog "Related posts" sections carry recent threat-intel titles — useful for proposing next KB items.
- In-body links to official checklists/patterns (e.g. learn.microsoft.com PnP checklists) should always be harvested as KB follow-ups.
