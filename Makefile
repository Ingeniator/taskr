APP_NAME=JiraQuickTask
DIST_DIR := dist
APP_BUNDLE=$(DIST_DIR)//$(APP_NAME).app
DEST_APP=/Applications/$(APP_NAME).app
PLIST_SOURCE=./com.ingeniator.jiraquicktask.plist
PLIST_DEST=$(HOME)/Library/LaunchAgents/com.ingeniator.jiraquicktask.plist
DMG_NAME := $(APP_NAME)-Installer.dmg
DMG_SETTINGS := dmg_settings.py
RELEASE_DIR := release

.PHONY: dmg clean-dmg install build uninstall rebuild

dmg: $(RELEASE_DIR)/$(DMG_NAME)

$(RELEASE_DIR)/$(DMG_NAME): $(DMG_SETTINGS) $(APP_BUNDLE)
	uv run dmgbuild -s $(DMG_SETTINGS) "$(APP_NAME) Installer" $@

clean-dmg:
	rm -f $(DIST_DIR)/$(DMG_NAME)

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
	@test -f config/config.yaml || (echo "❌ Missing config/config.yaml!" && false)
	@uv run pyinstaller --windowed --add-data "config:config" --onefile --name $(APP_NAME) launch_jira.py

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
	@$(MAKE) build
	@./dist/JiraQuickTask