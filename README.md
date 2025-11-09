The dotfiles of Karl M. Davis
=============================

This repo contains my dotfiles: the configuration/settings files used on the systems I login to.
I manage these files using [chezmoi](https://www.chezmoi.io/).

On a new system, run the following to install and initialize this whole setup:

    $ brew install chezmoi
    $ chezmoi init karlmdavis

That will automatically find and clone this `karlmdavis/dotfiles` repository from GitHub
  to `~/.local/share/chezmoi/` on the local system.

To push out the files in this repo to your home directory as dotfiles, run:

    $ chezmoi status
    $ chezmoi diff
    $ chezmoi apply

To manage a new file with chezmoi, run:

    $ chezmoi add <FILE>

Please note: chezmoi supports templating of files using Golang templates.
Do not edit a templated file directly, unless you want to deal with merging your changes later.
Instead, run this:

    $ chezmoi edit <FILE>

I've set chezmoi to automatically commit and push any changes to its managed files.
There's obviously a surprise vs. consistency tradeoff there, but I think it's the safer move.
See `[.chezmoi.toml.tmpl](./.chezmoi.toml.tmpl)` to adjust that, if needed.

## Long-Running Task Notifications

This dotfiles repo includes a notification system that alerts you when:
- **Claude Code** finishes work after 3+ minutes
- **Shell commands** complete after 3+ minutes

### How It Works

The system uses **hybrid presence detection** to avoid notification spam:
- ✅ **Sends notification** when you're away (unfocused terminal OR idle for 10+ seconds)
- ⏱️ **30-second grace period** if you're currently focused (gives you time to switch back)
- ❌ **No notification** if you return within the grace period

Notifications are delivered via [ntfy](https://ntfy.sh) to your phone/tablet.

### Setup

1. **Install ntfy app on your devices:**
   - iOS: https://apps.apple.com/us/app/ntfy/id1625396347
   - Android: https://play.google.com/store/apps/details?id=io.heckel.ntfy

2. **Apply dotfiles:**
   ```bash
   chezmoi apply
   ```
   This generates a unique notification topic (stored in `~/.local/share/ntfy-topic`).

3. **Subscribe to your topic:**
   - Check the output from step 2 for your topic UUID
   - Open ntfy app → tap **+** → paste your topic → Subscribe

4. **You're done!** Notifications will appear automatically when:
   - You walk away from a long-running task
   - The terminal loses focus while work completes
   - You go idle for 10+ seconds

### Configuration

- **Duration threshold:** 30 seconds - configurable in hook scripts
- **Grace period:** 30 seconds - configurable in `ntfy-alert-if-unfocused.sh`
- **Idle threshold:** 10 seconds - configurable in `ntfy-alert-if-unfocused.sh`
- **Topic file:** `~/.local/share/ntfy-topic` (NOT in git - regenerate with `chezmoi apply --force`)

For implementation details, see `private_dot_local/bin/ntfy-*.sh` and `private_dot_local/lib/ntfy-nu-hooks.nu`.

## License

This project is licensed under the [GNU General Public License, Version 3](./LICENSE).

