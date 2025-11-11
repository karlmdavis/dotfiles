#!/usr/bin/env bats

load '../helpers/test_helpers'

@test "config loads defaults when env vars not set" {
    unset WKFLW_NTFY_SERVER
    unset WKFLW_NTFY_NUSHELL_THRESHOLD
    unset WKFLW_NTFY_ESCALATION_DELAY
    unset WKFLW_NTFY_DEBUG

    source $WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config

    [[ "$WKFLW_NTFY_SERVER" == "https://ntfy.sh" ]]
    [[ "$WKFLW_NTFY_NUSHELL_THRESHOLD" == "90" ]]
    [[ "$WKFLW_NTFY_ESCALATION_DELAY" == "120" ]]
    [[ "$WKFLW_NTFY_DEBUG" == "0" ]]
}

@test "config respects env var overrides" {
    export WKFLW_NTFY_SERVER="https://custom.ntfy.sh"
    export WKFLW_NTFY_NUSHELL_THRESHOLD="120"
    export WKFLW_NTFY_ESCALATION_DELAY="300"
    export WKFLW_NTFY_DEBUG="1"

    source $WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config

    [[ "$WKFLW_NTFY_SERVER" == "https://custom.ntfy.sh" ]]
    [[ "$WKFLW_NTFY_NUSHELL_THRESHOLD" == "120" ]]
    [[ "$WKFLW_NTFY_ESCALATION_DELAY" == "300" ]]
    [[ "$WKFLW_NTFY_DEBUG" == "1" ]]
}

@test "config reads ntfy topic from state file if exists" {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    echo "WKFLW_NTFY_TOPIC=macbook-karl-abc123" > "$WKFLW_NTFY_STATE_DIR/config"

    source $WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config

    [[ "$WKFLW_NTFY_TOPIC" == "macbook-karl-abc123" ]]
}

@test "config warns if ntfy topic missing" {
    export WKFLW_NTFY_STATE_DIR="$BATS_TEST_TMPDIR/state"
    mkdir -p "$WKFLW_NTFY_STATE_DIR"
    # No config file

    unset WKFLW_NTFY_TOPIC
    source $WKFLW_NTFY_TEST_DIR/.local/lib/wkflw-ntfy/core/wkflw-ntfy-config 2>&1 | grep -q "WARNING"
}
