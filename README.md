# Prompt Library

Self-hosted Prompt + Agent workbench for organizing and reusing LLM prompts.

## Current App State (Implemented)

The project is currently a hybrid local app with:

- Prompt management in the UI, stored in JSON (`data_file`)
- Agent management in the UI, stored on filesystem folders under `agents/`
- User-scoped views from `launch-config.ini` (`users=...`)

### Stage progress (current)

- Stage 1: Prompt terminology updates (done)
- Stage 2: Inline prompt text editing with dirty save/cancel/copy flows (done)
- Stage 3: Backend agent filesystem service + Flask routes (done)
- Stage 4: First visible agent UI layer (done)

### Prompt features currently available

- Prompt groups (including `All` and `Unsorted`) per user
- Search/filter by prompt group
- Expand/collapse prompt cards
- Inline prompt text editing in expanded cards
- Dirty-state save/cancel/copy confirmation behavior
- Prompt delete
- Prompt reorder (collapsed cards)
- Drag/drop move prompts between groups

### Agent features currently available

- Agent navigation/filter presence in left nav
- Agent list rendering by active user/group
- Expand/collapse agent cards
- Load existing agent sections from backend
- Section tab switching
- Edit/save/cancel existing section content
- Dirty-edit discard confirmations on key navigation paths
- Agent delete with confirmation
- Construct buttons shown but intentionally disabled (Stage 5 not implemented yet)

### Agent features intentionally deferred

- Agent construct logic (Stage 5)
- Agent zip export (Stage 6)
- Character/token counts (Stage 7)
- Agent creation UX and section create/rename/order editing

## Architecture Notes

- Flask + server-rendered HTML (no frontend framework)
- Prompt data remains JSON-backed
- Agent data remains filesystem-backed:

```text
agents/<user>/<group>/<agent>/
  agent.json
  role.md
  rules.md
  process.md
  output.md
```

Section keys are canonically handled as lowercase names (e.g. `role`, `rules`) with compatibility for legacy values like `role.md`.

## Features

- Fast local web UI for prompts and agents
- JSON-backed prompt storage (`data_file` configurable)
- Filesystem-backed agent storage (`agents_root` optional)
- Simple local launcher config via `launch-config.ini`
- Works for localhost or LAN access
- Windows launcher script included (`start-prompt-library.vbs`)

## Requirements

- Python 3.x
- Flask

Install Flask:

```powershell
pip install flask
```

Optional (recommended): use a virtual environment instead of global install.

## Quick Start (Windows)

1. Copy `launch-config.example.ini` to `launch-config.ini`
2. Edit `launch-config.ini` for your machine
3. Start the app:
   - Double-click `start-prompt-library.vbs`
   - or run `python server.py`
4. Open the URL from your config (example: `http://127.0.0.1:5000`)

## Configuration

Edit `launch-config.ini`:

```ini
listen_port=5000
open_scheme=http
open_host=127.0.0.1
data_file=prompt_library.json
agents_root=agents
users=User One,User Two
```

Both launch methods (`start-prompt-library.vbs` and `python server.py`) use `launch-config.ini`.

### Config keys

- `listen_port`: port to listen on/open (default `5000`)
- `open_scheme`: URL scheme (`http` by default)
- `open_host`: host/IP to open in browser (`127.0.0.1` for local, LAN IP for intranet)
- `data_file`: JSON file used by `server.py` (relative filename or absolute path)
- `agents_root`: optional filesystem root for agent folders (defaults to `agents`)
- `users`: comma-separated user names shown in the app user dropdown

## Local Network Access

`server.py` runs on `0.0.0.0`, so other devices on your LAN can connect if:

- they can reach your machine's LAN IP
- your firewall allows inbound traffic on `listen_port`

Example LAN setting:

```ini
open_host=192.168.x.x
```

## Files

- `server.py` - Flask server and data API
- `agent_service.py` - filesystem-backed agent storage service
- `templates/prompt_library.html` - main UI
- `start-prompt-library.vbs` - Windows launcher
- `stop-server-5000.vbs` - helper to stop port 5000 listener
- `launch-config.example.ini` - public-safe sample config

## GitHub / Local Data Notes

- `launch-config.ini` ignored by git, so machine-specific settings stay local and are not included in the repo.
- JSON data files are ignored by git by default, so prompt content stays local and is not included in the repo.
- Ignored JSON filenames include `contexts.json` and `prompt_library.json`.

