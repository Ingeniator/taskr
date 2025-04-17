APP_NAME=JiraQuickTask
APP_BUNDLE=dist/$(APP_NAME).app
DEST_APP=/Applications/$(APP_NAME).app
PLIST_SOURCE=./com.ingeniator.jiraquicktask.plist
PLIST_DEST=$(HOME)/Library/LaunchAgents/com.ingeniator.jiraquicktask.plist

install: build
	@set -x
	@echo "📦 Installing $(APP_NAME) app..."
	@cp -R "$(APP_BUNDLE)" "$(DEST_APP)"
	@xattr -rd com.apple.quarantine "$(DEST_APP)"
	@sleep 0.5
	@cp "$(PLIST_SOURCE)" "$(PLIST_DEST)"
	@plutil -lint "$(PLIST_DEST)" || (echo "❌ Invalid .plist file" && false)
	@launchctl bootout gui/$(shell id -u) "$(PLIST_DEST)" 2>/dev/null || true
	@launchctl bootstrap gui/$(shell id -u) "$(PLIST_DEST)" || (echo "❌ Bootstrap failed! Check logs or quarantine flags." && false)
	@echo "✅ Installed and loaded LaunchAgent for app."

build:
	@echo "🔧 Building app with pyinstaller..."
	@uv run pyinstaller --windowed --onefile --name $(APP_NAME) launch_jira.py

	@echo "🩹 Patching .spec with icon and LSUIElement..."
	@uv run python scripts/patch_spec.py

	@echo "🚀 Rebuilding with patched spec..."
	@rm -rf build/ dist/
	@uv run pyinstaller $(APP_NAME).spec

	@echo "🛠️  Patching LSUIElement in Info.plist..."
	@/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$(APP_BUNDLE)/Contents/Info.plist" || \
	/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$(APP_BUNDLE)/Contents/Info.plist"

uninstall:
	@launchctl bootout gui/$(shell id -u) "$(PLIST_DEST)" || true
	@rm -rf "$(PLIST_DEST)"
	@rm -rf "$(DEST_APP)"
	@echo "🗑️  Uninstalled $(APP_NAME)."

rebuild:
	@echo "Cleaning mac's cache"
	@killall $(APP_NAME) 2>/dev/null || true
	@echo "♻️ Rebuilding $(APP_NAME)..."
	@rm -rf build/ dist/ *.spec
	@$(MAKE) install