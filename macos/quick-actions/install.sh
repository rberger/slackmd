#!/bin/bash
# Install macOS Quick Actions (Services) for slackmd, bound to a global hotkey later
# in System Settings. Each service is a "Run Shell Script" Automator workflow that
# invokes the venv CLI; the CLI reads and writes the clipboard itself, so the service
# takes no input.
#
#   bash macos/quick-actions/install.sh
#
# Then: System Settings > Keyboard > Keyboard Shortcuts > Services > General,
# assign a shortcut to "slackmd: Slack to Markdown" and "slackmd: Markdown to Slack".
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CLI="$REPO/.venv/bin/slackmd"
SERVICES="$HOME/Library/Services"

if [ ! -x "$CLI" ]; then
  echo "error: $CLI not found. Run 'make setup' first." >&2
  exit 1
fi
mkdir -p "$SERVICES"

make_service() {
  local name="$1" command="$2"
  local bundle="$SERVICES/$name.workflow"
  local wf="$bundle/Contents"
  rm -rf "$bundle"
  mkdir -p "$wf"
  local u1 u2 u3
  u1="$(uuidgen)"; u2="$(uuidgen)"; u3="$(uuidgen)"

  # Wrap the command with feedback: the CLI writes to the clipboard silently, so play a
  # sound (works regardless of notification permissions) plus a macOS notification, so a
  # successful run is perceptible. Keep the script free of &, <, > so it needs no XML
  # escaping in the workflow plist (afplay/osascript run foreground; their output is
  # discarded by the Quick Action).
  local body
  body="if ${command}; then afplay /System/Library/Sounds/Glass.aiff; osascript -e 'display notification \"Converted, now on your clipboard\" with title \"${name}\"'; else afplay /System/Library/Sounds/Basso.aiff; osascript -e 'display notification \"Nothing to convert on the clipboard\" with title \"${name}\"'; fi"

  cat > "$wf/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>NSServices</key>
	<array>
		<dict>
			<key>NSIconName</key>
			<string>NSActionTemplate</string>
			<key>NSMenuItem</key>
			<dict>
				<key>default</key>
				<string>$name</string>
			</dict>
			<key>NSMessage</key>
			<string>runWorkflowAsService</string>
			<key>NSSendTypes</key>
			<array/>
		</dict>
	</array>
</dict>
</plist>
PLIST

  cat > "$wf/document.wflow" <<WFLOW
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
	<key>AMApplicationBuild</key>
	<string>523</string>
	<key>AMApplicationVersion</key>
	<string>2.10</string>
	<key>AMDocumentVersion</key>
	<string>2</string>
	<key>actions</key>
	<array>
		<dict>
			<key>action</key>
			<dict>
				<key>AMAccepts</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Optional</key>
					<true/>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>AMActionVersion</key>
				<string>2.0.3</string>
				<key>AMApplication</key>
				<array>
					<string>Automator</string>
				</array>
				<key>AMProvides</key>
				<dict>
					<key>Container</key>
					<string>List</string>
					<key>Types</key>
					<array>
						<string>com.apple.cocoa.string</string>
					</array>
				</dict>
				<key>ActionBundlePath</key>
				<string>/System/Library/Automator/Run Shell Script.action</string>
				<key>ActionName</key>
				<string>Run Shell Script</string>
				<key>ActionParameters</key>
				<dict>
					<key>COMMAND_STRING</key>
					<string>$body</string>
					<key>CheckedForUserDefaultShell</key>
					<true/>
					<key>inputMethod</key>
					<integer>0</integer>
					<key>shell</key>
					<string>/bin/zsh</string>
					<key>source</key>
					<string></string>
				</dict>
				<key>BundleIdentifier</key>
				<string>com.apple.Automator.RunShellScript</string>
				<key>CFBundleVersion</key>
				<string>2.0.3</string>
				<key>CanShowSelectedItemsWhenRun</key>
				<false/>
				<key>CanShowWhenRun</key>
				<true/>
				<key>Category</key>
				<array>
					<string>AMCategoryUtilities</string>
				</array>
				<key>Class Name</key>
				<string>RunShellScriptAction</string>
				<key>InputUUID</key>
				<string>$u1</string>
				<key>Keywords</key>
				<array>
					<string>Shell</string>
					<string>Script</string>
					<string>Command</string>
					<string>Run</string>
					<string>Unix</string>
				</array>
				<key>OutputUUID</key>
				<string>$u2</string>
				<key>UUID</key>
				<string>$u3</string>
				<key>UnlocalizedApplications</key>
				<array>
					<string>Automator</string>
				</array>
				<key>conversionLabel</key>
				<integer>0</integer>
				<key>isViewVisible</key>
				<integer>1</integer>
				<key>location</key>
				<string>449.000000:253.000000</string>
				<key>nibPath</key>
				<string>/System/Library/Automator/Run Shell Script.action/Contents/Resources/main.nib</string>
			</dict>
			<key>isViewVisible</key>
			<integer>1</integer>
		</dict>
	</array>
	<key>connectors</key>
	<dict/>
	<key>workflowMetaData</key>
	<dict>
		<key>applicationBundleIDsByPath</key>
		<dict/>
		<key>applicationPaths</key>
		<array/>
		<key>inputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>outputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>presentationMode</key>
		<integer>11</integer>
		<key>processesInput</key>
		<false/>
		<key>serviceInputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>serviceOutputTypeIdentifier</key>
		<string>com.apple.Automator.nothing</string>
		<key>serviceProcessesInput</key>
		<false/>
		<key>systemImageName</key>
		<string>NSActionTemplate</string>
		<key>useAutomaticInputType</key>
		<false/>
		<key>workflowTypeIdentifier</key>
		<string>com.apple.Automator.servicesMenu</string>
	</dict>
</dict>
</plist>
WFLOW

  plutil -lint "$wf/Info.plist" >/dev/null
  plutil -lint "$wf/document.wflow" >/dev/null
  echo "installed: $bundle"
}

make_service "slackmd: Slack to Markdown" "$CLI from-slack --copy"
make_service "slackmd: Markdown to Slack" "$CLI to-slack --copy"

# Best-effort: pre-bind the recommended global shortcuts by writing the Services
# key_equivalent into the pbs preference domain. macOS may require a logout for this
# to take effect, and an app-level shortcut can shadow it, so the manual assignment in
# System Settings > Keyboard > Keyboard Shortcuts > Services is the reliable fallback.
# key_equivalent modifiers: @ = cmd, ~ = option, $ = shift, ^ = control.
# Pre-bind the recommended shortcuts by merging them into the pbs NSServicesStatus
# dict, preserving any other Services shortcuts. `defaults -dict-add` cannot REPLACE an
# existing key, so read-modify-write the whole dict via plistlib.
# key_equivalent modifiers: @ = cmd, ~ = option, $ = shift, ^ = control.
bind_hotkeys() {
  local tmp; tmp="$(mktemp)"
  defaults export pbs "$tmp" 2>/dev/null || printf '{}\n' > "$tmp"
  "$REPO/.venv/bin/python" - "$tmp" <<'PY'
import sys, plistlib
path = sys.argv[1]
try:
    with open(path, "rb") as f:
        d = plistlib.load(f)
except Exception:
    d = {}
st = d.get("NSServicesStatus", {}) or {}
def setk(name, keq):
    st[f"(null) - {name} - runWorkflowAsService"] = {
        "enabled_services_menu": True,
        "presentation_modes": {"ServicesMenu": True},
        "key_equivalent": keq,
    }
setk("slackmd: Slack to Markdown", "@~s")    # Cmd+Option+S
setk("slackmd: Markdown to Slack", "@~^m")   # Ctrl+Cmd+Option+M (plain Cmd+M is minimize)
d["NSServicesStatus"] = st
with open(path, "wb") as f:
    plistlib.dump(d, f)
PY
  defaults import pbs "$tmp"
  rm -f "$tmp"
}
bind_hotkeys

# Nudge the services registry so the new Quick Actions appear.
/System/Library/CoreServices/pbs -flush 2>/dev/null || true

echo
if defaults read pbs NSServicesStatus 2>/dev/null | grep -q "slackmd"; then
  echo "pre-bound shortcuts: Cmd+Option+S (Slack to Markdown), Ctrl+Cmd+Option+M (Markdown to Slack)."
  echo "If a shortcut is not active, set it in System Settings > Keyboard > Keyboard"
  echo "Shortcuts > Services > General (a logout may be needed for the pre-bind to apply)."
else
  echo "assign shortcuts in System Settings > Keyboard > Keyboard Shortcuts > Services > General."
fi
