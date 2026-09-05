# GymCoach

Personal fitness coach — Hermes Agent skill. Launches a tmux-based coaching session tailored to a beginner (sedentary, low flexibility, 50+).

## Structure

```
gymcoach/
├── SKILL.md          # Agentskills.io-compliant skill definition
└── README.md         # This file
```

## Install

1. Copy `gymcoach/` into your Hermes skills directory:
   ```bash
   cp -r gymcoach ~/.hermes/profiles/<your-profile>/skills/
   ```
2. Create the project workspace:
   ```bash
   mkdir -p ~/gymcoach/{data,plans,photos}
   ```
3. Create your personal profile in `~/gymcoach/data/user-profile.md` (see SKILL.md for template)
4. Create a Hermes project:
   ```bash
   hermes project create GymCoach ~/gymcoach
   ```
5. Load the skill:
   ```bash
   hermes chat --skills gymcoach --in ~/gymcoach
   ```

## Usage

Say **"gymcoach"** to invoke — the coach will analyse gym photos, build progressive plans, and track sessions. The tmux session persists so you can reconnect from Hermes Desktop or SSH.

## License

MIT — see [LICENSE](../LICENSE).