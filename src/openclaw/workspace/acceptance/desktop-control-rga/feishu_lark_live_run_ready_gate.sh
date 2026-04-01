#!/usr/bin/env bash
set -euo pipefail

# Feishu / Lark live-run-ready final gate
# Purpose: validate readiness for a human-authorized single live-run without performing any real send.
# Default posture: conservative, no-send, no blind dispatch.

VERIFY_ONLY_PASS="${VERIFY_ONLY_PASS:-0}"
BASELINE_PASS="${BASELINE_PASS:-0}"
LIVE_RUN_READY_CHECK="${LIVE_RUN_READY_CHECK:-1}"
ALLOW_REAL_SEND="${ALLOW_REAL_SEND:-0}"
APP_NAME="${APP_NAME:-Feishu}"
TARGET_NAME="${TARGET_NAME:-}"
TARGET_KIND="${TARGET_KIND:-chat}"
TARGET_IS_WHITELISTED="${TARGET_IS_WHITELISTED:-0}"
SEND_METHOD="${SEND_METHOD:-UNKNOWN}"
MESSAGE_TEXT="${MESSAGE_TEXT:-}"
SINGLE_SEND_ONLY="${SINGLE_SEND_ONLY:-1}"
NO_RETRY_ON_UNCLEAR="${NO_RETRY_ON_UNCLEAR:-1}"
REQUIRE_HUMAN_TARGET_CONFIRM="${REQUIRE_HUMAN_TARGET_CONFIRM:-1}"
REQUIRE_HUMAN_DRAFT_CONFIRM="${REQUIRE_HUMAN_DRAFT_CONFIRM:-1}"
REQUIRE_HUMAN_SEND_METHOD_CONFIRM="${REQUIRE_HUMAN_SEND_METHOD_CONFIRM:-1}"
REQUIRE_HUMAN_LIVE_AUTH="${REQUIRE_HUMAN_LIVE_AUTH:-1}"
LOG_DIR="${LOG_DIR:-./acceptance/desktop-control-rga/logs}"
TS="$(date +%Y%m%d-%H%M%S)"
LOG_FILE="$LOG_DIR/feishu-lark-live-ready-gate-$TS.log"
CHECKLIST_FILE="$LOG_DIR/feishu-lark-live-ready-checklist-$TS.txt"
EVIDENCE_DIR="$LOG_DIR/live-ready-evidence-$TS"

mkdir -p "$LOG_DIR" "$EVIDENCE_DIR"

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

require_nonempty() {
  local name="$1"
  local value="$2"
  [[ -n "$value" ]] || fail "$name is required"
}

for pair in \
  "VERIFY_ONLY_PASS:$VERIFY_ONLY_PASS" \
  "BASELINE_PASS:$BASELINE_PASS" \
  "LIVE_RUN_READY_CHECK:$LIVE_RUN_READY_CHECK" \
  "ALLOW_REAL_SEND:$ALLOW_REAL_SEND" \
  "TARGET_IS_WHITELISTED:$TARGET_IS_WHITELISTED" \
  "SINGLE_SEND_ONLY:$SINGLE_SEND_ONLY" \
  "NO_RETRY_ON_UNCLEAR:$NO_RETRY_ON_UNCLEAR" \
  "REQUIRE_HUMAN_TARGET_CONFIRM:$REQUIRE_HUMAN_TARGET_CONFIRM" \
  "REQUIRE_HUMAN_DRAFT_CONFIRM:$REQUIRE_HUMAN_DRAFT_CONFIRM" \
  "REQUIRE_HUMAN_SEND_METHOD_CONFIRM:$REQUIRE_HUMAN_SEND_METHOD_CONFIRM" \
  "REQUIRE_HUMAN_LIVE_AUTH:$REQUIRE_HUMAN_LIVE_AUTH"
  do
  bool_guard "${pair%%:*}" "${pair#*:}"
done

[[ "$LIVE_RUN_READY_CHECK" == "1" ]] || fail "LIVE_RUN_READY_CHECK must stay 1"
[[ "$ALLOW_REAL_SEND" == "0" ]] || fail "ALLOW_REAL_SEND must stay 0 in this gate"
[[ "$VERIFY_ONLY_PASS" == "1" ]] || fail "verify-only must already be marked PASS"
[[ "$BASELINE_PASS" == "1" ]] || fail "acceptance baseline must already be marked PASS"
[[ "$TARGET_IS_WHITELISTED" == "1" ]] || fail "target must be an approved whitelist test object"
[[ "$SINGLE_SEND_ONLY" == "1" ]] || fail "single-send-only constraint must stay enabled"
[[ "$NO_RETRY_ON_UNCLEAR" == "1" ]] || fail "no-retry-on-unclear must stay enabled"

require_nonempty TARGET_NAME "$TARGET_NAME"
require_nonempty TARGET_KIND "$TARGET_KIND"
require_nonempty MESSAGE_TEXT "$MESSAGE_TEXT"
[[ "$SEND_METHOD" != "UNKNOWN" ]] || fail "SEND_METHOD must be explicitly set (e.g. ENTER, CMD_ENTER, CLICK_SEND)"

command -v osascript >/dev/null 2>&1 || fail "osascript not found"
command -v python3 >/dev/null 2>&1 || fail "python3 not found"

log "Feishu/Lark live-run-ready final gate started"
log "App: $APP_NAME"
log "Target name: $TARGET_NAME"
log "Target kind: $TARGET_KIND"
log "Target whitelist: YES"
log "Send method (declared): $SEND_METHOD"
log "Policy: NO real send, NO blind dispatch, SINGLE SEND ONLY, NO RETRY ON UNCLEAR"
log "Evidence dir: $EVIDENCE_DIR"

python3 - <<'PY' || fail "unicode readiness validation failed"
text = "live-run-ready 最终安全闸：仍默认不真实外发"
assert "不真实外发" in text
print(text)
PY

cat > "$CHECKLIST_FILE" <<EOF
[ ] Baseline already PASS
[ ] Feishu/Lark verify-only already PASS
[ ] Current target is whitelist-approved: $TARGET_NAME
[ ] Target type is correct: $TARGET_KIND
[ ] Frontmost app is $APP_NAME
[ ] Correct chat/session is visible
[ ] Focus is in message input field, not search box
[ ] Draft matches expected content exactly
[ ] Declared send method is confirmed: $SEND_METHOD
[ ] This run remains NO-SEND by default
[ ] If human later authorizes live-run, it must be single-send only
[ ] If result is unclear, STOP and do not retry
EOF

cat > "$EVIDENCE_DIR/README.txt" <<EOF
Required evidence before human-authorized live-run:
1. screenshot_before_target.png   - target/session visible
2. screenshot_before_draft.png    - draft visible in input field
3. screenshot_before_ready.png    - ready state before any real send
4. screenshot_after_send.png      - only if a human separately authorizes and performs one real send
5. notes.txt                      - operator notes / target / send method / outcome
EOF

cat > "$EVIDENCE_DIR/notes.txt" <<EOF
Target: $TARGET_NAME
Target kind: $TARGET_KIND
Whitelist approved: YES
Declared send method: $SEND_METHOD
Single send only: YES
Retry on unclear allowed: NO
Message preview:
$MESSAGE_TEXT
EOF

log "Checklist file created: $CHECKLIST_FILE"
log "Evidence scaffold created: $EVIDENCE_DIR"

[[ "$REQUIRE_HUMAN_TARGET_CONFIRM" == "1" ]] && log "HUMAN CHECKPOINT: confirm target/session is exactly '$TARGET_NAME'"
[[ "$REQUIRE_HUMAN_DRAFT_CONFIRM" == "1" ]] && log "HUMAN CHECKPOINT: confirm full draft content is correct and complete"
[[ "$REQUIRE_HUMAN_SEND_METHOD_CONFIRM" == "1" ]] && log "HUMAN CHECKPOINT: confirm '$SEND_METHOD' is the true send action on this machine"
[[ "$REQUIRE_HUMAN_LIVE_AUTH" == "1" ]] && log "HUMAN CHECKPOINT: if later proceeding, explicit live-run authorization is still required"

log "Final gate verdict: READY-FOR-HUMAN-AUTH (not auto-send)"
log "This script does not press Enter / Cmd+Enter / click send and cannot enable real external sending"
pass "Live-run-ready gate completed; system may proceed only to human authorization, not autonomous send"
