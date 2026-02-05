APP_NAME=CtrlLord
DIST_DIR := dist
APP_BUNDLE=$(DIST_DIR)/$(APP_NAME).app
DEST_APP=/Applications/$(APP_NAME).app
PLIST_SOURCE=./com.ingeniator.ctrllord.plist
PLIST_DEST=$(HOME)/Library/LaunchAgents/com.ingeniator.ctrllord.plist
DMG_NAME := $(APP_NAME)-Installer.dmg
DMG_SETTINGS := dmg_settings.py
RELEASE_DIR := release
TARGET_ARCH ?= universal2
ARCHFLAGS := "-arch arm64 -arch x86_64"

.PHONY: venv dmg clean-dmg install build uninstall rebuild test

test:
	@uv run pytest tests/ -v

venv:
	python3 -m venv venv && . venv/bin/activate

dmg: $(RELEASE_DIR)/$(DMG_NAME)
	@tar -cvf - ./release/CtrlLord-Installer.dmg | split -b 25m -d - "archive_part_"

$(RELEASE_DIR)/$(DMG_NAME): $(DMG_SETTINGS) $(APP_BUNDLE)
	mkdir -p ./release && uv run dmgbuild -s $(DMG_SETTINGS) "$(APP_NAME) Installer" $@

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
	@ARCHFLAGS="-arch arm64 -arch x86_64" WRAPT_EXTENSIONS=false uv pip install --force-reinstall --no-binary :all: wrapt
	@$(MAKE) $(APP_BUNDLE)

# ➊ Первая фаза – генерация .spec без onefile
$(APP_NAME).spec: ctrllord.py
	@echo "🔧 Building app with pyinstaller..."
	@test -f config/config.toml || (echo "❌ Missing config/config.toml!" && false)
	@echo "🔧 (phase 1) generate spec..."
	@uv run pyinstaller \
		--noconfirm \
		--windowed \
		--hidden-import=PySide6.QtWidgets \
		--hidden-import=PySide6.QtGui \
		--hidden-import=PySide6.QtCore \
		--icon resources/icon.icns \
		--add-data "config:config" \
		--add-data "resources:resources" \
		--target-arch $(TARGET_ARCH) \
		--name $(APP_NAME) \
		--onedir $<

# ➋ Вторая фаза – сборка по .spec (можно патчить icon/LSUIElement как у вас)
$(APP_BUNDLE): $(APP_NAME).spec
	@echo "🔧 (phase 2) freeze..."
	@find dist -name "_internal" -type d -exec rm -rf {} +
	@uv run pyinstaller --clean --noconfirm $(APP_NAME).spec
	@echo "🛠️  Patching LSUIElement in Info.plist..."
	@/usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$(APP_BUNDLE)/Contents/Info.plist"  || \
	/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$(APP_BUNDLE)/Contents/Info.plist" || true
	@echo "🔏 codesign..."
	@$(MAKE) sign-app


sign-app:
	@echo "🔏 Signing app with ad-hoc identity..."
	@codesign --remove-signature dist/CtrlLord.app  
	@codesign -s - --deep --force --verbose=2 dist/CtrlLord.app

test_build: 
	for f in $(APP_BUNDLE)/Contents/MacOS/* $(APP_BUNDLE)/Contents/Frameworks/*.dylib; do
	lipo -info "$f" | grep -q 'arm64 x86_64' || echo "🚨 $f not universal"
	done

build_old:	
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
	@rm -rf build/ dist/ release/ *.spec
	@$(MAKE) build
	@$(MAKE) dmg

clean:
	@echo "🧹 Cleaning build artifacts, specs, dist, and symlinks..."
	@killall $(APP_NAME) 2>/dev/null || true
	@rm -rf build/ dist/ *.spec __pycache__/
	@find . -name "__pycache__" -type d -exec rm -rf {} +
	@find dist -name "_internal" -type d -exec rm -rf {} +
	@find . -type l -exec test ! -e {} \; -delete
	@echo "✅ Clean complete."

nuke: clean
	@echo "🔥 Removing .venv and cache..."
	@rm -rf .venv
	@rm -rf ~/.cache/uv ~/.cache/pip
	@echo "🧨 Environment fully nuked. Rebuild from scratch!"