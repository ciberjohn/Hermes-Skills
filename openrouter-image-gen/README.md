# OpenRouter Image Generation

Generate images through OpenRouter's chat-completions endpoint using
image-capable models. No GPU, no ComfyUI, no Docker: the image comes back
embedded in the API response JSON, decoded and written to a PNG by the bundled
scripts. Includes guidance for a recurring cartoon character so an article
series reads as one body of work.

## Prerequisites

- **Python 3** (standard library only)
- An **OpenRouter account** and API key (`OPENROUTER_API_KEY`)

## Installation

To install the skill into a Hermes profile, copy the whole directory into
`~/.hermes/skills/creative/openrouter-image-gen/`, keeping the `scripts/`
subdirectory (exclude `__pycache__` if present). If you ask your Hermes agent
to install it conversationally, the agent should copy `SKILL.md`, `README.md`,
`.gitignore`, and the contents of `scripts/`, then ask these configuration
questions one at a time:

1. Do you have an OpenRouter API key? `OPENROUTER_API_KEY` (required for image
   generation)
2. Where should the script look for the key if it is not set in the
   environment? `OPENROUTER_ENV_FILE` (optional, default `~/.hermes/.env`)

## Variables Reference

| Variable | Description | Example |
|----------|-------------|---------|
| `OPENROUTER_API_KEY` | (Required) OpenRouter API key | `sk-or-v1-xxxxxxxx` |
| `OPENROUTER_ENV_FILE` | (Optional) `.env` file containing the key when not set in the environment | `~/.hermes/.env` |

Key precedence in the scripts: explicit `OPENROUTER_ENV_FILE` first, then the
`OPENROUTER_API_KEY` environment variable, then the default `~/.hermes/.env`.
This deliberately prefers a file over the environment, because session
environments can hold stale keys.

## Directory Structure

```
openrouter-image-gen/
├── SKILL.md                  # The skill itself
├── README.md                 # This file
├── .gitignore                # Python cache + env files + generated images
└── scripts/
    ├── generate_image.py     # <out.png> "<prompt>" [model]
    └── verify_image_vision.py # <image.png> [model]
```

## How to Use

```bash
# Generate a hero illustration
python3 scripts/generate_image.py illustration.png "wide 16:9 editorial cartoon, ..." google/gemini-3.1-flash-image

# Verify it (the generator can lie about what it drew)
python3 scripts/verify_image_vision.py illustration.png
```

The image is returned as a `data:image/...;base64,....` string embedded in the
JSON response — the script walks the whole response recursively to find it
(`message.content` can be null while the image is buried in a nested array).

## Output Files

| File | Purpose |
|------|---------|
| `<out.png>` | The generated image, decoded and written to the path you gave |

## Customising

Define your own recurring character in the SKILL.md "Recurring Series
Character" section: one character, one workspace, one palette, reused in every
illustration. The spec included is an example, not a requirement.

## Contributing / License

MIT. See the [Hermes-Skills repo](https://github.com/ciberjohn/Hermes-Skills)
for the full collection.
