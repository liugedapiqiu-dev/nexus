#!/bin/bash
set -euo pipefail

LABEL="ai.vectorbrain.openclaw-api"
PLIST="$HOME/Library/LaunchAgents/${LABEL}.plist"
PYTHON_BIN="$(command -v python3)"
SCRIPT="$HOME/.vectorbrain/service_bridges/openclaw_control_plane.py"
LOG_DIR="$HOME/.vectorbrain/logs"
PORT="${OPENCLAW_VB_API_PORT:-18991}"
HOST="${OPENCLAW_VB_API_HOST:-127.0.0.1}"

mkdir -p "$LOG_DIR" "$HOME/Library/LaunchAgents"

write_plist() {
  cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
  <dict>
    <key>Label</key>
    <string>${LABEL}</string>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>ThrottleInterval</key>
    <integer>5</integer>
    <key>ProgramArguments</key>
    <array>
      <string>${PYTHON_BIN}</string>
      <string>${SCRIPT}</string>
      <string>--host</string>
      <string>${HOST}</string>
      <string>--port</string>
      <string>${PORT}</string>
    </array>
    <key>WorkingDirectory</key>
    <string>${HOME}/.vectorbrain</string>
    <key>EnvironmentVariables</key>
    <dict>
      <key>HOME</key>
      <string>${HOME}</string>
      <key>PATH</key>
      <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:${HOME}/.local/bin:${HOME}/.npm-global/bin</string>
      <key>PYTHONUNBUFFERED</key>
      <string>1</string>
      <key>OPENCLAW_VB_API_HOST</key>
      <string>${HOST}</string>
      <key>OPENCLAW_VB_API_PORT</key>
      <string>${PORT}</string>
    </dict>
    <key>StandardOutPath</key>
    <string>${LOG_DIR}/openclaw_api_control_plane.launchd.out.log</string>
    <key>StandardErrorPath</key>
    <string>${LOG_DIR}/openclaw_api_control_plane.launchd.err.log</string>
  </dict>
</plist>
PLIST
}

case "${1:-}" in
  install)
    write_plist
    launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    launchctl kickstart -k "gui/$(id -u)/${LABEL}"
    echo "installed: $LABEL"
    ;;
  uninstall)
    launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
    rm -f "$PLIST"
    echo "uninstalled: $LABEL"
    ;;
  restart)
    write_plist
    launchctl bootout "gui/$(id -u)/${LABEL}" >/dev/null 2>&1 || true
    launchctl bootstrap "gui/$(id -u)" "$PLIST"
    launchctl kickstart -k "gui/$(id -u)/${LABEL}"
    echo "restarted: $LABEL"
    ;;
  status)
    launchctl print "gui/$(id -u)/${LABEL}" 2>/dev/null || echo "not loaded: $LABEL"
    ;;
  write-plist)
    write_plist
    echo "$PLIST"
    ;;
  *)
    echo "usage: $0 {install|restart|status|uninstall|write-plist}" >&2
    exit 1
    ;;
esac
