#!/bin/bash

##
# Ensures the Rust toolchain (rustup + the stable toolchain) is installed, so `cargo` is available on
# every system — its PATH entry lives in the shared shell-env (.chezmoitemplates/shell-env.sh). Uses the
# official rustup-init installer rather than Homebrew, which is not recommended for managing the Rust
# toolchain. Idempotent: does nothing if cargo/rustup is already present.
#
# This is a run_onchange_ script: chezmoi records its content hash only after a successful (exit 0) run,
# so a failed install is NOT recorded and is retried on the next `chezmoi apply`, while a successful run
# stays quiet in `chezmoi status` until this script's contents change.
##

set -euo pipefail

# Already installed (by rustup or otherwise) — nothing to do.
if command -v cargo >/dev/null 2>&1 || [ -x "$HOME/.cargo/bin/cargo" ]; then
  exit 0
fi

# Install rustup + the stable toolchain. --no-modify-path because PATH is managed by shell-env.
# A failure here aborts `chezmoi apply` loudly (no error swallowing). A network/TLS/cert failure is
# unlikely — pulling the changes to apply already needed a network connection — and an unrecorded
# failure is retried on the next apply (see header).
if ! curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
  | sh -s -- -y --default-toolchain stable --profile default --no-modify-path; then
  echo "" >&2
  echo "rustup install failed (offline or TLS/cert issue?)." >&2
  echo "To apply the rest of your dotfiles now, continuing past this failure, run:" >&2
  echo "    chezmoi apply --keep-going" >&2
  exit 1
fi
