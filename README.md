# 🚀 Jira Quick Task Launcher

A lightweight, macOS-style launcher built with **PyQt5** that allows you to quickly create Jira tasks using a global hotkey (`Cmd + Shift + J`). The app supports both **mock mode** for local development and **live integration** with Jira and LLM services.

---

## ✨ Features

- 🖥️ Frameless, macOS-style floating launcher UI
- ⚡ Instant task creation with global hotkey
- 🔍 Automatically pre-fills summary from clipboard
- 🧠 LLM-powered task description generator
- 🐞 Real Jira API integration with project/component/type support
- ✅ Smart task preview with markdown formatting
- 🍞 Toast notifications and clipboard copy
- 🧪 Mock mode for testing without Jira or LLM
- 💡 Theme switching

---

## 🛠️ Installation

```bash
pip install -r requirements.txt
```
Make sure you have Python 3.8+ and PyQt5 installed.

## ⚙️ Configuration

Create a config file at config/config.yaml:

```yaml
mode: "mock"  # change to "live" for real Jira/LLM

jira:
  base_url: "https://yourcompany.atlassian.net"
  project_key: "CORE"
  username: "your_email@company.com"
  api_token: "your_api_token"

llm:
  base_url: "http://localhost:8000"
  endpoint: "/generate-jira"
  timeout: 10
  prompt_path: "resources/generate_jira_task.md"

ui:
  issue_types:
    - Task
    - Bug
    - Story
    - Spike
  components:
    - Core
    - UI
    - API Integration Layer
    - Machine Learning Pipeline

```

## 🚀 Usage

```bash
python main.py
```

- Press Cmd + Shift + J to open the launcher.
- Type a quick summary (or prefilled from your clipboard).
- Hit Enter to generate full task details.
- Press Ctrl + Enter to submit to Jira.
- The task key is copied to clipboard and a toast appears.

## 🧪 Mock Mode

When mode: mock is active:

- No Jira or LLM APIs are called.
- Fake task keys like MOCK-123 are generated.
- Great for UI development or offline demos.

## 🧠 LLM Integration

If mode: live, the summary is sent to an LLM endpoint (e.g., FastAPI or OpenAI).

The LLM must return a structured JSON like:

```json
{
  "summary": "Fix retry logic in webhook handler",
  "description": "# Fix retry logic...\n\n## Context...",
  "type": "Bug"
}
```

## 📦 Packaging (Optional)

You can use PyInstaller to bundle as a .app for macOS:

```bash
make build
```

## 📄 License

MIT – do whatever you want ✌️
