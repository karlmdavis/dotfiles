# To-Dos

This document is used to keep track of open ideas, tasks, etc. related to this project.

## Questions

(none at this time)

## Quick Tasks

- [ ] Add host name to prompts so I can tell when I'm on SSH.

## Larger Tasks

- [ ] Configure infinite history retention in zsh and bash.
- [ ] Consider applying this to all to `root` as well.
    - Mostly for the history retention part.
- [ ] Create a `nu --login` wrapper script and set it as zellij's `default_shell`.
    - `echo $nu.is-login` should be `true` in a login shell.
    - This caused the weird "char colon" errors in nushell that I had to workaround.
    - Might have other not-yet-found issues?
- [ ] Stop creation of `~/Library/Application Support/` on Linux.
