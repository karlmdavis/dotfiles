#!/usr/bin/env nu
# E2E tests for nushell command notification hooks

# Source the hooks to test (from deployed location)
source ~/.local/lib/ntfy-nu-hooks.nu

# Test: format-duration function
def test_format_duration [] {
    # Test minutes + seconds
    let result1 = (format-duration 185)
    if $result1 != "3m 5s" {
        error make {msg: $"format-duration failed: expected '3m 5s', got '($result1)'"}
    }

    # Test seconds only
    let result2 = (format-duration 45)
    if $result2 != "45s" {
        error make {msg: $"format-duration failed: expected '45s', got '($result2)'"}
    }

    # Test large duration
    let result3 = (format-duration 3665)
    if $result3 != "61m 5s" {
        error make {msg: $"format-duration failed: expected '61m 5s', got '($result3)'"}
    }

    print "✓ format-duration tests passed"
}

# Note: Comprehensive E2E notification tests are in test_claude_hooks.bats
# These nushell tests focus on verifying the helper functions work correctly

# Run all tests
def main [] {
    print "Running nushell hook tests..."
    print ""

    test_format_duration

    print ""
    print "All nushell tests passed! ✓"
}
