# Skill Structure

Every skill lives under `$HOME/.openclaw/skills/<skill-name>/` and follows the layout below.

## Directory layout

```
$HOME/.openclaw/skills/<skill-name>/
├── SKILL.md              # Required — frontmatter + instructions
├── .venv/                # Python virtual environment (created on first run, gitignored)
├── scripts/              # Executable scripts the agent runs
│   └── <script>.py
├── requirements.txt      # Python deps (optional — only when using pip install -r)
└── <data-files>          # Anything the skill reads/writes at runtime
                          # e.g. todo.db, devices.json, memory.yml, token.json
```

## SKILL.md

```markdown
---
name: <lowercase-hyphens>          # max 64 chars, no reserved words
description: <what it does and when to use it>   # max 1024 chars
---

# <Skill Title>

## Setup
...

## Workflow / Commands
...

## Constraints
...
```

## $HOME paths

All absolute paths use `$HOME/.openclaw/skills/<skill-name>/` as the root — never hardcode a username. Scripts are invoked using their full path so the agent never needs to `cd` first:

```bash
$HOME/.openclaw/skills/<skill-name>/.venv/bin/python3 \
  $HOME/.openclaw/skills/<skill-name>/scripts/<script>.py
```

## Virtual environment

Use a `.venv` inside the skill directory. Always check before creating:

**If `.venv` already exists** — activate only:

```bash
cd $HOME/.openclaw/skills/<skill-name>
source .venv/bin/activate
```

**If not** — create, activate, and install:

```bash
cd $HOME/.openclaw/skills/<skill-name>
python3 -m venv .venv
source .venv/bin/activate
pip install <packages>
# or: pip install -r requirements.txt
```

Once a `.venv` exists, invoke scripts directly via the venv interpreter so activation is not required:

```bash
$HOME/.openclaw/skills/<skill-name>/.venv/bin/python3 \
  $HOME/.openclaw/skills/<skill-name>/scripts/<script>.py <args>
```

> Skills that use stdlib only (no third-party packages) skip the venv entirely and call `python3` directly.

## Scripts

- Live in `scripts/` relative to the skill root.
- Accept CLI arguments — no interactive prompts.
- Print structured output (JSON, plain text) to stdout.
- Handle errors internally; never ask the agent to guess a fix.

## Data files

Runtime state (databases, cached API responses, OAuth tokens, YAML memory, etc.) lives at the skill root alongside `SKILL.md`. Reference them via `$HOME/.openclaw/skills/<skill-name>/<file>` in instructions.

## .gitignore entries

Add per-skill gitignore entries for generated/runtime files:

```
skills/<skill-name>/.venv/
skills/<skill-name>/token.json
skills/<skill-name>/*.db
```
