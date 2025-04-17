import re

spec_file = "JiraQuickTask.spec"
replacement = '''app = BUNDLE(
    exe,
    name="JiraQuickTask.app",
    icon="resources/icon.icns",
    bundle_identifier="com.ingeniator.jiraquicktask",
    info_plist={
        "LSUIElement": "1",
        "CFBundleName": "JiraQuickTask",
        "CFBundleDisplayName": "Jira Quick Task",
        "CFBundleIconFile": "icon.icns",
    }
)'''

with open(spec_file, "r") as f:
    lines = f.read()

# Replace old BUNDLE block
new_lines = re.sub(r'app = BUNDLE\([\s\S]+?\)', replacement, lines)

with open(spec_file, "w") as f:
    f.write(new_lines)

print("✅ .spec file patched with LSUIElement and icon.icns")
