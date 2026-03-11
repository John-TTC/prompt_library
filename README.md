# Prompt Library

Self-hosted Prompt Library for organizing and quickly reusing your favorite LLM prompts.

## What this is

`Prompt Library` is a lightweight local web app (HTML + Flask) for managing reusable prompt blocks.  
The UI is served from your machine, and prompt data is saved to a local JSON file specified by `data_file` in `launch-config.ini`.

## Features

- Fast local web UI for prompt blocks
- JSON-backed storage (`data_file` configurable)
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
```

Both launch methods (`start-prompt-library.vbs` and `python server.py`) use `launch-config.ini`.

### Config keys

- `listen_port`: port to listen on/open (default `5000`)
- `open_scheme`: URL scheme (`http` by default)
- `open_host`: host/IP to open in browser (`127.0.0.1` for local, LAN IP for intranet)
- `data_file`: JSON file used by `server.py` (relative filename or absolute path)

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
- `templates/prompt_library.html` - main UI
- `start-prompt-library.vbs` - Windows launcher
- `stop-server-5000.vbs` - helper to stop port 5000 listener
- `launch-config.example.ini` - public-safe sample config

## GitHub / Local Data Notes

- `launch-config.ini` ignored by git, so machine-specific settings stay local and are not included in the repo.
- JSON data files are ignored by git by default, so prompt content stays local and is not included in the repo.
- Ignored JSON filenames include `contexts.json` and `prompt_library.json`.

