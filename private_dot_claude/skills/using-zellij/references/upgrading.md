# Upgrading Zellij

Upgrading ends every session, and with them every shell and Claude Code session inside, including
  the one doing the upgrade.
`zellij-upgrade` does the whole cycle and puts everything back.
Its source and guide are in the dotfiles repo at `private_dot_local/lib/zellij-upgrade/`
  (`CLAUDE.md` there says what it does and checks).

## Run it

1. Read the new version's release notes for anything that changes the picture.
2. Preview: `zellij-upgrade --dry-run`.
    It shows what is running and how each Claude session would be resumed, lists as problems the
    panes it cannot resume, and changes nothing.
3. Run it only when the user has asked for the upgrade: `zellij-upgrade`.
    It asks before ending anything; `--yes` skips that question, so pass it only when the user has
    already said to go ahead.
    Started inside Zellij, it carries on in a new terminal window (or a detached process), waits
    for every Claude session to finish its turn, and ends the session you are in.
    End your turn after starting it.
4. When it has brought everything back, it types a message into the pane it was started from.
    Read the report it names and check the result: `zellij --version`, `zellij list-sessions`, and
    each Claude pane.

Its exit status is 1, and the old version stays installed, when anything did not come back.
The report then says, for each pane, what to type by hand.

## What it does not do

- A Claude session that has never taken a turn has no saved conversation, so it cannot be resumed.
    The preview lists it; start it again by hand afterwards.
- A pane where Claude asks a question at startup (whether to trust the folder, for one) is reported
    as not running. Answering that question is the user's decision.
- Sessions resumed by id on a slow machine can come back reporting no status to Zellij
    (a Claude Code startup timing bug seen on `scaleway-mini`). Exiting such a session and resuming
    it from the `claude --resume` picker fixes it.

## What is kept, and rollback

Each run keeps `inventory.json`, `run.log`, `report.md`, a copy of Zellij's saved sessions and the
  old binary under `~/.local/state/zellij-upgrade/<time>/`.

- To go back a version: `brew unlink zellij`, then link the kept binary (`zellij-before-upgrade`)
    at Homebrew's `bin/zellij`.
- A lost layout can be opened from the copy with
    `zellij --layout <state folder>/session-cache/session_info/<folder>/session-layout.kdl -s <name>`.

## Other machines

Run it on each machine.
Where iTerm2 is open, sessions come back in iTerm2 windows; elsewhere, detached in the background.
The dotfiles' package script runs `brew bundle --no-upgrade`, so `chezmoi apply` never upgrades
  Zellij on its own.
