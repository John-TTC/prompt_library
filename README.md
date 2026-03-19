# LLM Prompt and Agent Library

A lightweight, local-first workspace for organizing, editing, and reusing prompts and structured agent components across LLM sessions.

This app helps you keep your favorite prompt building blocks in one place so you can quickly retrieve, edit, copy, and assemble them without relying on cloud storage or heavyweight tooling.

## What this is

**LLM Prompt and Agent Library** is a self-hosted Flask web app for managing two kinds of reusable LLM assets:

- **Prompts** — single reusable text blocks stored in JSON
- **Agents** — structured multi-section prompt definitions stored as Markdown files in folders on disk

It is designed to stay:

- lightweight
- local-first
- fast to use
- clipboard-oriented
- easy to understand
- visually simple

This is **not** a full autonomous agent runner. It is a **prompt and agent authoring / construction workspace**.

---

## Core concepts

### Prompts

A **Prompt** is a single reusable block of text.

Prompts are useful for:
- reusable system prompts
- role instructions
- style guides
- boilerplate task setup
- frequently reused context blocks

Prompts are stored in the JSON file configured by `data_file` in `launch-config.ini`.

### Agents

An **Agent** is a structured prompt made up of multiple named sections.

Typical sections might include:
- `Role`
- `Rules`
- `Process`
- `Output`

Agents are useful when you want a reusable prompt template that is split into logical parts and can be assembled into:
- a **full agent prompt**
- a **single section prompt**

Agents are stored on disk as folders containing Markdown files.

---

## Features

### Prompt features

- Create, view, edit, and delete prompts
- Organize prompts into groups
- Drag and drop prompts between groups
- Reorder prompts
- Expand/collapse prompt cards
- Inline editing with save/cancel flow
- Copy prompt text to clipboard
- Dirty-state protection for copy/cancel flows
- Prompt metadata editing from the UI
- Saved-state character and estimated token counts

### Agent features

- Create agents from the UI
- Store agents as portable filesystem folders
- Organize agents into groups
- Drag and drop agents between groups
- Reorder agents
- Expand/collapse agent cards
- Keep multiple agent cards expanded at once
- Edit agent sections inline
- Add new sections/tabs from the UI
- Construct a full agent prompt from all sections
- Construct a prompt from only the active section
- Construct preview/copy dialog flow
- Dirty-state protection for save/cancel/construct flows
- Agent metadata editing from the UI
- Saved-state character and estimated token counts

### Group features

- Separate group systems for Prompts and Agents
- Create groups from the UI
- Reorder groups
- Delete groups from a context menu
- On delete, move contained items to **No Group**

---

## Storage model

### Prompt storage

Prompts remain JSON-backed.

Configured by:

- `data_file` in `launch-config.ini`

### Agent storage

Agents are filesystem-backed and scoped by user.

Typical structure:

```text
agents/<user>/<group>/<agent>/
  agent.json
  role.md
  rules.md
  process.md
  output.md
```

Agent groups are also persisted on disk per user.

Example:

```text
agents/<user>/agent-groups.json
```

This keeps agents portable and easy to inspect, back up, or move manually.

---

## UI overview

The app is split into two modes:

* **Prompts**
* **Agents**

You can switch between modes in the UI and work with each independently.

### Left navigation

The left sidebar shows groups for the current mode.

Prompts and Agents have separate group lists.

### Main pane

The main pane displays prompt cards or agent cards for the selected group.

The page uses normal browser scrolling, so long lists can extend naturally down the page.

### Editing behavior

Expanded cards support inline editing with explicit save/cancel flows.

Counts shown in headers are based on the **last saved state**, not live unsaved edits.

---

## Character and token counts

The app displays saved-state counts in the UI for clarity and low overhead.

Displayed counts include:

* Prompt header counts
* Agent total counts
* Active section/tab counts

Rules:

* **Character count** = exact string length
* **Token estimate** = approximate `chars / 4`

These counts update **only when content is saved**.

---

## Requirements

* Python 3.x
* Flask

Install Flask:

```powershell
pip install flask
```

Using a virtual environment is recommended, but not required.

---

## Quick start

### Windows

1. Copy `launch-config.example.ini` to `launch-config.ini`
2. Edit `launch-config.ini` for your machine
3. Start the app by either:

   * double-clicking `start-prompt-library.vbs`
   * or running:

```powershell
python server.py
```

4. Open the configured URL in your browser

Example:

```text
http://127.0.0.1:5000
```

---

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

Both `start-prompt-library.vbs` and `python server.py` use this file.

### Config keys

* `listen_port` — port the app listens on
* `open_scheme` — usually `http`
* `open_host` — host/IP to open in the browser
* `data_file` — prompt JSON storage file
* `agents_root` — root folder for agent storage
* `users` — comma-separated list of users shown in the app

---

## Local network access

`server.py` runs on `0.0.0.0`, so other devices on your LAN can access it if:

* they can reach your machine’s LAN IP
* your firewall allows inbound traffic on the configured port

Example:

```ini
open_host=192.168.x.x
```

---

## Project files

* `server.py` — Flask server and app routes
* `agent_service.py` — filesystem-backed agent storage/service layer
* `templates/prompt_library.html` — main UI template
* `start-prompt-library.vbs` — Windows launcher
* `stop-server-5000.vbs` — helper for stopping a process on port 5000
* `launch-config.example.ini` — sample config

---

## Design goals

This app is intentionally opinionated:

* **local-first** — your data stays on your machine
* **simple** — no heavy frontend framework
* **fast** — optimized for practical prompt reuse, not complex orchestration
* **portable** — agent definitions live as ordinary files/folders
* **incremental** — designed to evolve without becoming bloated

---

## Current limitations / planned improvements

The app already supports prompt and agent authoring well, but some features may still be expanded over time.

Examples of future work may include:

* agent zip export
* agent section rename/delete/reorder UX
* agent group rename UX
* additional polish around transport/import workflows

---

## Git / local data notes

* `launch-config.ini` should remain git-ignored so machine-specific settings stay local
* prompt data files can remain git-ignored so your prompt content stays private
* agent content folders may also be kept local/private unless you intentionally choose to version them

---

## Summary

**LLM Prompt and Agent Library** is a fast local workbench for managing reusable prompts and structured agent components.

It gives you:

* JSON-backed prompts
* filesystem-backed agents
* explicit save/cancel workflows
* copy/construct flows
* organized group-based navigation
* local ownership of your prompt assets

