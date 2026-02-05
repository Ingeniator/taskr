# CtrlLord — Jira Quick Task Launcher

A lightweight, macOS-style launcher built with **PySide6** that allows you to quickly create Jira tasks using a global hotkey (`Cmd + L`). The app supports both **mock mode** for local development and **live integration** with Jira and LLM services.

---

## Features

- Frameless, macOS-style floating launcher UI
- Instant task creation with configurable global hotkey
- Automatically pre-fills summary from clipboard
- LLM-powered task description generator
- Real Jira API integration with project/component/type support
- Smart task preview with markdown formatting
- Toast notifications and clipboard copy
- Mock mode for testing without Jira or LLM
- System tray icon with settings editor

---

## Installation

```bash
brew install jpeg webp zlib libtiff freetype little-cms2
uv sync
```

Requires Python 3.13+ and PySide6.

## Configuration

Config is stored at `~/.config/CtrlLord/config/config.toml` (created automatically on first run from defaults):

```toml
[jira]
mode = "mock"
base_url = "https://jira.yourcompany.com"
project_key = "CORE"
username = "your_jira_user"
token = "your_jira_personal_access_token"

[llm]
mode = "mock"
base_url = "http://localhost:8001"
endpoint = "/generate-jira"
timeout = 10
prompt_path = "resources/generate_jira_task.md"

[ui]
issue_types = ["Task", "Bug", "Story"]
components = ["Core", "UI", "API Integration Layer", "Machine Learning Pipeline"]
hotkey = "<cmd>+l"
```

## Usage

```bash
python ctrllord.py
```

- Press `Cmd + L` to open the launcher (configurable via `hotkey` in config).
- Type a quick summary (or prefilled from your clipboard).
- Hit Enter to generate full task details.
- Press Shift + Enter to submit to Jira.
- The task key is copied to clipboard and a toast appears.

## Mock Mode

When `mode = "mock"` is set in `[jira]` and/or `[llm]`:

- No Jira or LLM APIs are called.
- Fake task keys like MOCK-123 are generated.
- Great for UI development or offline demos.

## LLM Integration

If `mode = "live"` in `[llm]`, the summary is sent to an LLM endpoint (e.g., FastAPI or OpenAI).

The LLM must return a structured JSON like:

```json
{
  "summary": "Fix retry logic in webhook handler",
  "description": "# Fix retry logic...\n\n## Context...",
  "type": "Bug"
}
```

## Packaging (Optional)

You can use PyInstaller to bundle as a .app for macOS:

```bash
make build
```

## License

MIT
