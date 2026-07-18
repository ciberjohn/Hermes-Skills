# Skills Reference — Hermes Agent Fleet

> A complete catalog of all 79 skills available in the fleet, organised by category.
> **Updated:** 2026-07-18
> **Source legend:** 🏭 = Ships with Hermes Agent · 🌐 = Hermes-Skills repo · 🔒 = Fleet-only (private)

---

## Autonomous AI Agents

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **autonomous-ai-agents** | 🏭 | Delegate coding tasks to external AI coding agents (Claude Code, Codex, OpenCode) via ACP transport | Load with `skill_view` and tell it what code to write. It spawns an external agent and returns the result. |
| **hermes-agent** | 🏭 | Configure, extend, or contribute to Hermes Agent itself. Setup docs, config, skill-authoring. | Use when you need to change model providers, set up gateways, or modify Hermes's own configuration: `hermes config set ...` |

## Computer Use

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **computer-use** | 🏭 | Drive your desktop remotely — click, type, scroll, drag without stealing your cursor. Cross-platform. | Only works when the `computer_use` tool is available. Say: "click the Firefox icon" or "open terminal and type ..." |

## Creative

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **ascii-art** | 🏭 | Generate ASCII art via pyfiglet, cowsay, boxes, or image-to-ASCII conversion. | `/ascii-art make a dragon` or "turn this image into ASCII art" |
| **ascii-video** | 🏭 | Convert video or audio to coloured ASCII MP4/GIF. | "Convert this video to ASCII art animation" |
| **baoyu-article-illustrator** | 🔒 | Article illustrations with consistent type, style, and palette. | "Illustrate this article with a consistent style across all images" |
| **baoyu-comic** | 🔒 | Knowledge comics — educational, biography, tutorial in comic form. | "Turn this tutorial into a comic strip" |
| **baoyu-infographic** | 🏭 | Infographics with 21 layouts × 21 styles. | "Create an infographic showing the architecture" |
| **comfyui** | 🏭 | Generate images, video, and audio with ComfyUI — install, manage nodes/models, run workflows. | "Generate an image of ... using ComfyUI with the SDXL workflow" |
| **crypto-execution-engine** | 🔒 | Design and maintain automated crypto trading with CCXT. Part of the Cyrano→Quark pipeline. | "Set up a new trading strategy on Kraken" |
| **cybermonday** | 🔒 | Cybersecurity podcast segment for Coffee & Bytes. João's operational ground truth. | "Research this week's CyberMonday topic on ..." |
| **cyrano-jones-trader** | 🔒 | TOS-themed crypto market analysis for micro-investing via Kraken. Twice-daily reports with ASCII charts. | "Run today's market analysis" |
| **design** | 🏭 | Decision framework for picking between HTML mockups, design tokens, architecture diagrams, Excalidraw sketches. | "I need a design artifact — help me choose the right format" |
| **excalidraw** | 🏭 / 🌐 | Create Excalidraw diagrams (native Hermes tools, no MCP dependency). Saves to GitHub repo. | `/excalidraw draw a network architecture diagram` |
| **humanizer** | 🏭 | Strip AI-isms from text and add real voice. | "Humanize this article draft" |
| **ideation** | 🔒 | Generate project ideas via creative constraints. | "Give me 5 project ideas combining cybersecurity and music" |
| **manim-video** | 🏭 | 3Blue1Brown-style math/algo animations via Manim CE. | "Create a manim animation explaining gradient descent" |
| **medium-story** | 🌐 | Full Medium article pipeline: research → write → 4 output agents (revisor, Heygen, LinkedIn, YouTube) → HTML → git. | `/medium-story write about ...` |
| **p5js** | 🏭 | Generative art, shaders, interactive 3D via p5.js. | "Create a p5.js sketch that visualises the Mandelbrot set" |
| **pixel-art** | 🔒 | Pixel art with era palettes (NES, Game Boy, PICO-8). | "Draw a character in NES-style pixel art" |
| **pretext** | 🏭 | DOM-free text layout for ASCII art, kinetic typography, text-as-geometry demos. | "Build a browser demo with text flowing around obstacles" |
| **short-videos** | 🌐 | 90-second universal video scripts for HeyGen / Reels / LinkedIn / Shorts. | `/short-videos create a video about zero-trust networking` |
| **songwriting-and-ai-music** | 🏭 | Songwriting craft and Suno AI music prompts. | "Write lyrics for a synthwave track about the singularity" |
| **star-trek-creative-projects** | 🔒 | Design Star Trek themed agent profiles (SOUL.md), crew definitions, and creative storytelling. | "Create a SOUL.md for a new fleet officer called T'Pring" |
| **technical-writing** | 🔒 | Umbrella for content pipeline. Routes to medium-story, short-videos, cybermonday, excalidraw. NOT for direct use. | Load the specific skill instead. |
| **touchdesigner-mcp** | 🏭 | Control TouchDesigner via MCP — create operators, wire connections, build real-time visuals (36 tools). | "Create a TouchDesigner network that reacts to audio" |

## Data Science

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **jupyter-live-kernel** | 🏭 | Iterative Python via live Jupyter kernel (hamelnb). | "Open a Jupyter notebook and explore this dataset" |

## DevOps

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **ai-projects** | 🌐 | Clone or sync the AI-Projects GitHub repo. Replaces old Claude Code `/ai-projects` command. | `/ai-projects sync` |
| **devsecops-review** | 🔒 | Full security audit of source code — secrets, credentials, hardcoded paths, git history leaks, pipeline safety. | "Run a devsecops review on this repo" |
| **documentation-and-backups** | 🔒 | Complete "update docs and backups" procedure — wiki, GitHub docs, backup script, cron test. | "Update your docs and backups" |
| **github** | 🏭 | Umbrella for all GitHub operations — auth, PR workflow, code review, issues, repos. | "Create a PR with these changes" or "Review PR #42" |
| **hermes-operations** | 🔒 | Operate, debug, and maintain a running Hermes multi-profile installation. | "Check the cron logs" or "Debug why my gateway disconnected" |
| **infrastructure-documentation** | 🔒 | Discover, diagram, and document infrastructure — hosts, containers, networks, traffic flows. | "Document my infrastructure topology" |
| **meridian-isa-bot** | 🔒 | Automated ISA stock trading via Interactive Brokers. DCA strategy, UK-listed ETFs. | "Check Meridian's current positions" |
| **recurring-analysis-cron** | 🔒 | Build periodic analysis pipelines — data collector + LLM analyst + evolution tracking. | "Set up a daily cron that monitors my homelab temperatures" |
| **scotty-t3mp3st** | 🔒 | Dispatch Scotty for T3MP3ST security operations — autonomous recon, scanning, kill chain. | "Scotty, run a full T3MP3ST sweep of the fleet" |
| **skill-writer** | 🌐 | Creates new Hermes skills from a description. Generates SKILL.md, README.md, peer review. | `/skill-writer I need a skill that monitors disk usage` |

## Email

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **gmail-sent-verification** | 🔒 | Verify sent emails in Gmail Sent folder via IMAP — check delivery, recipients, subject. | "Verify that my email to John was sent correctly" |
| **himalaya** | 🏭 | IMAP/SMTP email from terminal via Himalaya CLI. | "Read my inbox" or "Send an email to ..." |

## Gaming

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **minecraft-modpack-server** | 🔒 | Host modded Minecraft servers (CurseForge, Modrinth). | "Set up a new modded Minecraft server with the ATM9 pack" |
| **pokemon-player** | 🔒 | Play Pokemon via headless emulator + RAM reads. | "Start playing Pokemon Red and show me my current party" |

## Media

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **heartmula** | 🏭 | Suno-like song generation from lyrics + tags. | "Create a song from these lyrics in the style of synthwave" |
| **spotify** | 🔒 | Play, search, queue, manage playlists and devices via Spotify. | "Play my Discover Weekly playlist" |
| **youtube-tools** | 🔒 | YouTube transcript extraction, channel analysis, content repurposing. | "Summarise this YouTube video" or "Get transcripts from my last 10 videos" |

## MLOps

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **audiocraft-audio-generation** | 🏭 | MusicGen text-to-music, AudioGen text-to-sound via Meta's AudioCraft. | "Generate a 30-second ambient music track" |
| **dspy** | 🔒 | Declarative LM programs with auto-optimised prompts and RAG. | "Set up a DSPy program for my Q&A dataset" |
| **huggingface-hub** | 🏭 | Search, download, upload models and datasets via HuggingFace CLI. | "Find sentiment-analysis models on HuggingFace" |
| **ml-inference** | 🏭 | Serve LLMs locally with llama.cpp (GGUF) and vLLM. | "Serve Llama 3 70B on this machine with vLLM" |
| **model-evaluation** | 🔒 | Evaluate and benchmark LLMs with lm-eval-harness, track with W&B. | "Benchmark this GGUF model on the MMLU dataset" |
| **segment-anything-model** | 🏭 | Zero-shot image segmentation via points, boxes, masks (Meta's SAM). | "Segment all the cars in this image" |

## Productivity

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **airtable** | 🏭 | REST API via curl — CRUD records, filters, upserts. | "Get all records from my CRM base" |
| **google-workspace** | 🏭 | Gmail, Calendar, Drive, Docs, Sheets via OAuth. Full Workspace API. | "Create a spreadsheet with this data" or "Find the doc from last week" |
| **linear** | 🔒 | Manage issues, projects, teams via Linear GraphQL API. | "Create a Linear issue for this bug" |
| **maps** | 🏭 | Geocode, POIs, routes, timezones via OpenStreetMap/OSRM. | "Find coffee shops near this address" or "Route from A to B" |
| **note-taking** | 🏭 | Read, search, create, edit notes in Joplin and Obsidian vaults. | "Find my note about Docker networking" or "Create a new note" |
| **notion** | 🏭 | Notion API pages, databases, markdown via Workers. | "Add this to my Notion project tracker" |
| **ocr-and-documents** | 🏭 | Extract text from PDFs and scans (pymupdf, marker-pdf). | "Extract text from this scanned PDF" |
| **petdex** | 🏭 | Install and select animated petdex mascots for Hermes. | "Show me available pets" or "Set the cat as my mascot" |
| **powerpoint** | 🏭 | Create, read, edit .pptx decks, slides, notes, templates. | "Create a 5-slide deck about Q4 results" |
| **teams-meeting-pipeline** | 🏭 | Operate Teams meeting summary pipeline — summarise meetings, replay jobs, manage subscriptions. | "Summarise yesterday's standup from Teams" |

## Red Teaming

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **godmode** | 🔒 | LLM jailbreak techniques — Parseltongue, GODMODE, ULTRAPLINIAN. | Research/testing only. |
| **web-security-audit** | 🔒 | Full web app security assessment — DNS recon, TLS audit, HTTP headers, WAF detection, port scanning. | "Audit example.com for security issues" |

## Research

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **arxiv** | 🏭 | Search arXiv papers by keyword, author, category, or ID. | "Find recent papers on transformer architecture" |
| **blogwatcher** | 🏭 | Monitor blogs and RSS/Atom feeds for new content. | "Watch this blog and alert me when new posts appear" |
| **literature-review** | 🔒 | Systematic academic literature reviews — multi-source search, abstract extraction, thematic synthesis. | "Conduct a literature review on edge AI inference" |
| **llm-wiki** | 🏭 | Karpathy's LLM Wiki — build and query an interlinked markdown knowledge base. | "Add this paper to my LLM wiki" |
| **polymarket** | 🏭 | Query prediction markets — prices, orderbooks, history. | "What's the probability of the Fed cutting rates in September?" |
| **research-paper-writing** | 🏭 | Write ML research papers for NeurIPS/ICML/ICLR. | "Draft a paper about my findings on LoRA efficiency" |

## Smart Home

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **openhue** | 🏭 | Control Philips Hue lights, scenes, rooms via OpenHue CLI. | "Turn the living room lights to warm white" |

## Social Media

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **xurl** | 🏭 | X/Twitter via CLI — post, search, DM, media, v2 API. | "Post this thread about Kubernetes security to X" |

## Software Development

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **development-methodology** | 🔒 | Decision framework — spikes, systematic debugging, TDD, pre-commit verification. | "What approach should I use for this bug?" |
| **plan** | 🏭 | Write actionable markdown plans to `.hermes/plans/` — bite-sized tasks, exact paths, no execution. | "Plan the implementation of a user authentication system" |
| **skill-creation** | 🔒 | Full lifecycle for creating and iterating Hermes skills — from concept to packaged SKILL.md. | "I want to create a skill that monitors my homelab temperature" |
| **skill-publishing** | 🔒 | Sanitise and package personal skills for public distribution — strips paths, names, secrets. | "Make this skill shareable for the Hermes-Skills repo" |
| **subagent-driven-development** | 🔒 | Execute plans via delegate_task subagents with 2-stage review. | "Execute the plan in .hermes/plans/auth-system.md" |
| **writing-plans** | 🔒 | Write implementation plans with bite-sized tasks, exact paths, and code sketches. | "Write an implementation plan for a REST API" |

## Uncategorised

| Skill | Source | What It Does | How to Use |
|-------|--------|-------------|------------|
| **dogfood** | 🏭 | Exploratory QA of web apps — find bugs, collect evidence, write reports. | "Dogfood this web app and find any bugs" |
| **hermes-desktop-plugins** | 🏭 | Write desktop app plugins that add UI panes and commands to the Hermes desktop app. | "Create a plugin that shows a system monitor pane" |
| **yuanbao** | 🏭 | Tencent Yuanbao group queries — @mention users, query info/members. | Only relevant if you use Yuanbao social groups. |

---

## Summary

| Source | Count | Location |
|--------|-------|----------|
| 🏭 Ships with Hermes Agent 0.18.2 | ~47 | `github.com/NousResearch/hermes-agent/tree/main/skills/` |
| 🌐 Hermes-Skills (public) | 5 | `github.com/ciberjohn/Hermes-Skills` |
| 🔒 Fleet-only (private) | ~27 | `github.com/ciberjohn/hermes-configs` (private) |

---

> *"After all, skills are just runbooks that your agent can read."* 🖖
