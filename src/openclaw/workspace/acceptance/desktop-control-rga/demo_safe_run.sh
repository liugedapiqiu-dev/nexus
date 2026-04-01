#!/usr/bin/env bash
set -euo pipefail

# Desktop-control / RGA safe demo runner
# Default behavior: dry-run only. No real message sending.

DRY_RUN="${DRY_RUN:-1}"
LIVE_RUN="${LIVE_RUN:-0}"
TARGET_APP="${TARGET_APP:-TextEdit}"
TARGET_KIND="${TARGET_KIND:-local-editor}"
MESSAGE_TEXT="${MESSAGE_TEXT:-【验收演示】这是一条 dry-run 测试消息，不应被真实外发。}"
LOG_DIR="${LOG_DIR:-./acceptance/desktop-control-rga/logs}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/demo-$TS.log"

mkdir -p "$LOG_DIR"

log() {
  printf '%s %s\n' "[$(date '+%F %T')]" "$*" | tee -a "$LOG_FILE"
}

fail() {
  log "FAIL: $*"
  exit 1
}

if [[ "$DRY_RUN" != "1" && "$DRY_RUN" != "0" ]]; then
  fail "DRY_RUN must be 0 or 1"
fi

if [[ "$LIVE_RUN" != "1" && "$LIVE_RUN" != "0" ]]; then
  fail "LIVE_RUN must be 0 or 1"
fi

if [[ "$DRY_RUN" == "1" && "$LIVE_RUN" == "1" ]]; then
  fail "DRY_RUN=1 and LIVE_RUN=1 cannot both be enabled"
fi

if [[ "$LIVE_RUN" == "1" ]]; then
  log "WARNING: LIVE_RUN requested"
  log "This script is intentionally conservative and still will NOT auto-send messages."
  log "Manual confirmation is required outside this script before any real send action."
fi

log "Desktop-control / RGA acceptance demo started"
log "Mode: $( [[ "$LIVE_RUN" == "1" ]] && echo 'LIVE-RUN (guarded)' || echo 'DRY-RUN' )"
log "Target app: $TARGET_APP"
log "Target kind: $TARGET_KIND"
log "Message preview: $MESSAGE_TEXT"

log "Step 1/8 - Dependency readiness (manual+tooling check placeholder)"
command -v osascript >/dev/null 2>&1 || fail "osascript not found on macOS"
command -v python3 >/dev/null 2>&1 || fail "python3 not found"
log "Dependencies minimally present: osascript, python3"

log "Step 2/8 - Chinese input path check"
python3 - <<'PY' || fail "python unicode smoke test failed"
text = "中文输入验证：桌面控制 dry-run"
assert "中文" in text
print(text)
PY
log "Unicode smoke test passed (this is NOT a real app IME verification)"

log "Step 3/8 - App activation plan"
log "Planned app activation target: $TARGET_APP"
log "Manual checkpoint: ensure the correct app/window is frontmost"

log "Step 4/8 - Target confirmation gate"
log "Manual checkpoint required: verify recipient/window/title/avatar/group before any message task"
log "If target is ambiguous, STOP"

log "Step 5/8 - Pre-send verification"
log "Manual checkpoint required: verify focus is in the correct input field"
log "Manual checkpoint required: verify message content matches expectation"
log "This script will not press Enter and will not click any send button"

log "Step 6/8 - Safe local staging"
TMP_FILE="$LOG_DIR/message-preview-$TS.txt"
printf '%s\n' "$MESSAGE_TEXT" > "$TMP_FILE"
log "Wrote local preview file: $TMP_FILE"
log "Rollback path: delete preview file or clear draft manually"

log "Step 7/8 - Post-send verification placeholder"
log "If a human performs a real send outside this script, they must capture screenshot + verify single-send result"
log "If result is unclear, mark MANUAL and do not resend automatically"

log "Step 8/8 - Failure stop rule"
log "Any mismatch in app activation / target confirmation / IME / focus should abort the run"

log "Result: SAFE-DEMO-COMPLETE"
log "No real external message was sent by this script"
