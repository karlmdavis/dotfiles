#!/bin/bash

##
# Ensures the Rust toolchain (rustup + the stable toolchain) is installed, so `cargo` is available on
# every system — its PATH entry lives in the shared shell-env (.chezmoitemplates/shell-env.sh). Uses the
# official rustup-init installer rather than Homebrew, which is not recommended for managing the Rust
# toolchain. Idempotent: does nothing if cargo/rustup is already present.
##

set -euo pipefail

# Already installed (by rustup or otherwise) — nothing to do.
if command -v cargo >/dev/null 2>&1 || [ -x "$HOME/.cargo/bin/cargo" ]; then
  exit 0
fi

# Install rustup + the stable toolchain. --no-modify-path because PATH is managed by shell-env.
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
  | sh -s -- -y --default-toolchain stable --profile default --no-modify-path
