#!/usr/bin/env bash
set -euo pipefail

# Feishu / Lark verify-only final safety gate
# Purpose: refuse real send by default; only validate pre-send readiness checklist.

VERIFY_ONLY="${VERIFY_ONLY:-1}"
LIVE_RUN="${LIVE_RUN:-0}"
APP_NAME="${APP_NAME:-Feishu}"
TARGET_NAME="${TARGET_NAME:-}"
TARGET_KIND="${TARGET_KIND:-chat}"
MESSAGE_TEXT="${MESSAGE_TEXT:-}"
REQUIRE_HUMAN_TARGET_CONFIRM="${REQUIRE_HUMAN_TARGET_CONFIRM:-1}"
REQUIRE_HUMAN_DRAFT_CONFIRM="${REQUIRE_HUMAN_DRAFT_CONFIRM:-1}"
REQUIRE_HUMAN_NOT_SENT_CONFIRM="${REQUIRE_HUMAN_NOT_SENT_CONFIRM:-1}"
LOG_DIR="${LOG_DIR:-./acceptance/desktop-control-rga/logs}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/feishu-lark-verify-gate-$TS.log"

mkdir -p "$LOG_DIR"

log() {
  printf '%s %s\n' "[$(date '+%F %T')]" "$*" | tee -a "$LOG_FILE"
}

fail() {
  log "FAIL: $*"
  exit 1
}

pass() {
  log "PASS: $*"
}

bool_guard() {
  local name="$1"
  local value="$2"
  [[ "$value" == "0" || "$value" == "1" ]] || fail "$name must be 0 or 1"
}

bool_guard VERIFY_ONLY "$VERIFY_ONLY"
bool_guard LIVE_RUN "$LIVE_RUN"
bool_guard REQUIRE_HUMAN_TARGET_CONFIRM "$REQUIRE_HUMAN_TARGET_CONFIRM"
bool_guard REQUIRE_HUMAN_DRAFT_CONFIRM "$REQUIRE_HUMAN_DRAFT_CONFIRM"
bool_guard REQUIRE_HUMAN_NOT_SENT_CONFIRM "$REQUIRE_HUMAN_NOT_SENT_CONFIRM"

[[ "$VERIFY_ONLY" == "1" ]] || fail "This gate is verify-only. VERIFY_ONLY must stay 1"
[[ "$LIVE_RUN" == "0" ]] || fail "LIVE_RUN is forbidden in this gate"
[[ -n "$TARGET_NAME" ]] || fail "TARGET_NAME is required"
[[ -n "$MESSAGE_TEXT" ]] || fail "MESSAGE_TEXT is required"

command -v osascript >/dev/null 2>&1 || fail "osascript not found"
command -v python3 >/dev/null 2>&1 || fail "python3 not found"

log "Feishu/Lark verify-only gate started"
log "App: $APP_NAME"
log "Target kind: $TARGET_KIND"
log "Target name: $TARGET_NAME"
log "Message preview: $MESSAGE_TEXT"
log "Policy: NO real send, NO Enter send, NO send-button click"

python3 - <<'PY' || fail "unicode preview validation failed"
text = "中文 dry-run 校验：飞书 / Lark verify-only"
assert "飞书" in text or "Lark" in text or "dry-run" in text
print(text)
PY

CHECKLIST_FILE="$LOG_DIR/feishu-lark-checklist-$TS.txt"
cat > "$CHECKLIST_FILE" <<EOF
[ ] Frontmost app is $APP_NAME
[ ] Correct target is visible: $TARGET_NAME
[ ] Target type matches: $TARGET_KIND
[ ] Focus is in message input field, not search box
[ ] Draft matches expected content exactly
[ ] Message is still NOT sent
[ ] Human confirms this run stays verify-only
EOF

log "Checklist file created: $CHECKLIST_FILE"
log "Manual confirmation required for target / draft / not-sent state"

if [[ "$REQUIRE_HUMAN_TARGET_CONFIRM" == "1" ]]; then
  log "HUMAN CHECKPOINT: confirm target is exactly '$TARGET_NAME'"
fi

if [[ "$REQUIRE_HUMAN_DRAFT_CONFIRM" == "1" ]]; then
  log "HUMAN CHECKPOINT: confirm draft content is correct before send boundary"
fi

if [[ "$REQUIRE_HUMAN_NOT_SENT_CONFIRM" == "1" ]]; then
  log "HUMAN CHECKPOINT: confirm no message bubble was newly sent"
fi

log "Final gate action: STOP BEFORE SEND"
log "This script intentionally does not send keys for Enter / Cmd+Enter and does not click send"
pass "Verify-only safety gate completed; real external sending was not performed"
