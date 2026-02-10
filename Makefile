APP_NAME=CtrlLord
PLIST_SOURCE=./com.ingeniator.ctrllord.plist
PLIST_DEST=$(HOME)/Library/LaunchAgents/com.ingeniator.ctrllord.plist

.PHONY: test install reinstall uninstall clean nuke

test:
	@uv run pytest tests/ -v

install:
	@echo "📦 Installing $(APP_NAME) as Python package..."
	@uv pip install -e .
	@CTRLLORD_BIN=$$(uv run which ctrllord) && \
	echo "Found ctrllord at: $$CTRLLORD_BIN" && \
	sed "s|__CTRLLORD_BIN__|$$CTRLLORD_BIN|g" "$(PLIST_SOURCE)" > "$(PLIST_DEST)"
	@plutil -lint "$(PLIST_DEST)" || (echo "❌ Invalid .plist file" && false)
	@launchctl bootout gui/$$(id -u) "$(PLIST_DEST)" 2>/dev/null || true
	@launchctl bootstrap gui/$$(id -u) "$(PLIST_DEST)" || (echo "❌ Bootstrap failed!" && false)
	@echo "✅ Installed as package and loaded LaunchAgent."
	@echo "ℹ️  Grant Accessibility permission to your terminal in the window that opens."
	@open "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility"

reinstall: uninstall install

uninstall:
	@echo "🗑️  Uninstalling $(APP_NAME)..."
	@launchctl bootout gui/$(shell id -u) "$(PLIST_DEST)" 2>/dev/null || true
	@rm -f "$(PLIST_DEST)"
	@uv pip uninstall taskr 2>/dev/null || true
	@echo "✅ Uninstalled $(APP_NAME) package and LaunchAgent."

clean:
	@echo "🧹 Cleaning build artifacts..."
	@find . -name "__pycache__" -type d -exec rm -rf {} +
	@find . -type l -exec test ! -e {} \; -delete
	@echo "✅ Clean complete."

nuke: clean
	@echo "🔥 Removing .venv and cache..."
	@rm -rf .venv
	@rm -rf ~/.cache/uv ~/.cache/pip
	@echo "🧨 Environment fully nuked. Rebuild from scratch!"
