---
name: openrouter-image-gen
description: "Use when an illustration, cover, thumbnail, or any generated image is needed and local diffusion is unavailable. Generates via OpenRouter API, cheap models, no GPU, with recurring-character guidance for consistent article series art."
license: MIT
metadata:
  version: "1.0.0"
  tags: [image-generation, openrouter, api, vision, creative, llm]
  platforms: [linux]
  related_skills: [comfyui, medium-story, baoyu-article-illustrator]
---

# OpenRouter Image Generation

Generate images through OpenRouter's standard chat-completions endpoint using
image-capable models. No local GPU, no ComfyUI workflow, no Docker: the image
comes back inside the API response JSON.

## Configuration Variables

Set these in your environment before running the pipeline, or document them in
a `.env` file at your repo root:

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | (Required) OpenRouter API key for image generation | `sk-or-v1-xxxxxxxx` |
| `OPENROUTER_ENV_FILE` | (Optional) Path to a `.env` file containing the key, when it is not set directly in the environment | `~/.hermes/.env` |

If `OPENROUTER_API_KEY` is not set, the scripts fall back to reading it from
`OPENROUTER_ENV_FILE` (default `~/.hermes/.env`), looking for a line of the
form `OPENROUTER_API_KEY=...`.

## When to Use

- User asks for an illustration, cover, thumbnail, or any generated image and
  OpenRouter is the stated or available path.
- Local diffusion (ComfyUI) is not available or the job is a one-off.
- Text must render inside the image (T-shirts, signs, posters): Gemini image
  models handle text well — spell the text exactly in the prompt, then verify.

## Endpoint & Response Shape (the critical bit)

- POST `https://openrouter.ai/api/v1/chat/completions` with the normal chat
  payload: `{"model": ..., "messages": [{"role":"user","content":"<prompt>"}], "n": 1}`.
- The image is returned **embedded in the JSON** as a `data:image/...;base64,....`
  URL string. There is NO separate file download and NO image field you can
  trust to exist: `message.content` can be `null` while the image is buried
  somewhere else (e.g. nested content arrays, `reasoning_details`).
- **Always walk the whole response JSON recursively** and collect every string
  starting with `data:image` (fallback: `http(s)` URLs matching
  image|png|jpe?g|webp). Decode the first hit. See `scripts/generate_image.py`.

## Model Selection

Discover image-capable models live:

```bash
curl -s https://openrouter.ai/api/v1/models -o /tmp/or_models.json
# filter: architecture.output_modalities contains "image"
```

Cheap verified picks (re-check pricing via the API):

| Model | Prompt $/token | Notes |
|---|---|---|
| `google/gemini-3.1-flash-lite-image` | ~$0.25/M | Nano Banana 2 Lite — default "nice cheap" pick |
| `google/gemini-2.5-flash-image` | ~$0.30/M | Nano Banana; proven text quality |
| `google/gemini-3.1-flash-image` | ~$0.50/M | Nano Banana 2; best quality |
| `openai/gpt-5-image` | ~$10/M | premium, rarely needed |

Prompt guidance: state style ("editorial illustration", "slightly cartoonish"),
composition ("wide 16:9"), and explicitly "no real logos, no brand names, no
watermark".

## The Recurring Series Character (recommended)

For article or blog illustrations, define ONE cartoon character and reuse it in
every illustration so the series reads as a single body of work. Save the first
good generation as the style anchor and include the full spec in every prompt.

Example spec (used by the author of this skill — customise freely):

- A cartoon person of your choosing (example used by the author: stout/bald
  man, short goatee, round glasses, warm smile, plain black T-shirt, optionally
  a tech joke in green text)
- Their workspace: cluttered desk with monitors (terminal text and/or data
  visuals), shelves with books and electronics, warm desk lamp, string lights,
  night window
- A recurring motif: sci-fi paraphernalia (model starship, poster) — describe
  generically, never ask for trademarked logos
- Palette: cool blues/teals/purples with warm amber accents; wide 16:9
- Editorial cartoon style, clean linework, cel shading; "no real logos, no
  brand names, no watermark"

## Verification (always — the model can lie about what it drew)

The configured aux vision model may not accept images (e.g. a text-only
fallback → HTTP 400 "This model does not support image"). Workaround: send the
PNG to a cheap vision-capable model over OpenRouter as a `data:` URL in a
content array
`[{type:"text",text:...},{type:"image_url",image_url:{url:"data:image/png;base64,..."}}]`.
A verified vision model: `google/gemini-3.5-flash-lite` (check the current
list — a `gemini-3.1-flash` without `-image` may not exist as a text model).
Ask targeted questions: is the required text legible and correctly spelled?
Are the requested elements present? See `scripts/verify_image_vision.py`.

## Key Pitfall — stale API keys

- An invalid/rotated OpenRouter key returns HTTP 401 `{"error":{"message":"User
  not found."}}`.
- `GET /models` may STILL return 200 with an invalid key (the models list is
  not a strong auth check). **Confirm the key with `GET /api/v1/credits`**,
  which 401s on a bad key.
- In Hermes, keys may live in multiple `.env` files and they can DIVERGE. The
  session environment may hold a stale key sourced earlier from the wrong
  file. Read the key from `OPENROUTER_API_KEY` explicitly (or the
  `OPENROUTER_ENV_FILE` path) rather than trusting `os.environ` alone.
- Never print keys to chat or commit them.

## Scripts

- `scripts/generate_image.py <out.png> "<prompt>" [model]` — reads the key from
  `OPENROUTER_API_KEY` (or `OPENROUTER_ENV_FILE`), calls the API, walks the
  JSON for the image, writes the PNG. Default model
  `google/gemini-3.1-flash-lite-image`.
- `scripts/verify_image_vision.py <image.png> [model]` — vision check of a PNG
  via OpenRouter (data URL), prints the model's description. Default model
  `google/gemini-3.5-flash-lite`.

## Related

- `comfyui` — local diffusion workflows (different path, no API cost).
- `baoyu-article-illustrator` — style/palette guidance for article images
  (pair with this skill for consistent series art).
- `medium-story` — article pipeline; drop the PNG in the story folder and
  reference it with a `[*FILES*: name.png — description]` placeholder.
