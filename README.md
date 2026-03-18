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
- Stage 5: Agent construct behavior (done)
- Stage 5.1: Agent creation + section add flow + agent groups (done)
- Stage 5.2: Prompt/Agent group parity (create, reorder, context-menu delete) (done)
- Stage 5.3: No Group model + scroll/resize polish (done)

### Prompt features currently available

- Prompt groups (including `All` and `Unsorted`) per user
- Prompt groups use `No Group` as the built-in default (pinned first)
- Prompt groups are filtered by selected real group (no synthetic `All Prompts` row)
- Prompt group creation from `+ Group`
- Prompt group drag-reorder (Prompt groups only)
- Prompt group delete via right-click context menu (moves prompts to `No Group`)
- Search/filter by prompt group
- Expand/collapse prompt cards
- Inline prompt text editing in expanded cards
- Prompt card quick action text updated to `Copy to Clipboard`
- Dirty-state save/cancel/copy confirmation behavior
- Prompt delete
- Prompt reorder (collapsed cards)
- Prompt reorder (collapsed and expanded cards)
- Drag/drop move prompts between groups

### Agent features currently available

- Agent navigation/filter presence in left nav
- Agent list rendering by active user/group
- Agent group creation in Agent mode (`+ Group`)
- Agent groups use `No Group` as the built-in default (pinned first)
- Agent groups are filtered by selected real group (no synthetic `All Agents` row)
- Agent group drag-reorder (Agent groups only)
- Agent group delete via right-click context menu (moves agents to `No Group`)
- Agent groups persisted as metadata + real folders (including empty groups)
- Agent drag/drop assignment to Agent groups in sidebar
- Expand/collapse agent cards
- Multiple agent cards can remain expanded at once
- Agent card reorder (collapsed and expanded)
- Add Agent dialog with disk-backed creation in selected group (or `Unsorted` from `All Agents`)
- Load existing agent sections from backend
- Section tab switching
- Edit/save/cancel existing section content
- Add new section via `+` tab with Enter/Escape name flow and uniqueness checks
- Dirty-edit discard confirmations on key navigation paths
- Agent delete with confirmation
- Construct Agent Prompt + Construct Section Prompt
- Construct preview dialog with copy flow and post-copy confirmation
- Dirty-state construct decision flow:
  - Save and Construct
  - Construct Without Saving
  - Cancel

### Agent features intentionally deferred

- Agent zip export (Stage 6)
- Character/token counts (Stage 7)
- Agent section rename/reorder/deletion UX
- Agent group rename UX

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

agents/<user>/agent-groups.json
  # persisted Agent-group metadata: key, label, order, optional createdAt
```

UI notes:
- The page now handles normal vertical scrolling for long Prompt/Agent lists.
- Expanded Prompt/Agent cards are not capped by a fixed viewport max-height.

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

