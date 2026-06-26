# Mosh remote-host setup

This repo's iTerm2 profiles for remote systems use [Mosh](https://mosh.org/) instead of plain
  `ssh`/`it2ssh` so that sessions survive laptop suspend/wake, Wi-Fi drops, and IP changes.
Mosh is only the client half of that.
Each host you connect to must also run `mosh-server`, which is what this runbook sets up.

## How it works

Mosh uses your normal `ssh` to log in and launch `mosh-server` on the remote host (so your existing
  keys, agent, and `~/.ssh/config` apply to the login).
It then hands the session to a UDP-based protocol on a port in the range **60000–61000** (one port
  per concurrent session), which is what survives roaming and suspend.
The client invocation is just `mosh user@host`; the iTerm2 profiles set their `Command` to that.

Mosh requires a **UTF-8 locale** on the server, or `mosh-server` refuses to start.
It survives network changes and suspend, but **not** a server reboot — when `mosh-server` dies, its
  session is gone.
Layer a persistent remote `zellij`/`tmux` if you need reboot survival.

## macOS server (e.g. `scaleway-mini`, a Scaleway Mac mini)

- Enable Remote Login (SSH) in System Settings → General → Sharing.
- Install mosh with Homebrew: `brew install mosh` (no `sudo` needed; Apple-silicon Homebrew puts
    `mosh-server` in `/opt/homebrew/bin`).
- **PATH caveat:** `mosh` runs `mosh-server` over a non-interactive ssh session, which may not have
    `/opt/homebrew/bin` on `PATH`.
    If `mosh host` reports it can't find `mosh-server`, either add `/opt/homebrew/bin` to the login
      `PATH` or invoke `mosh --server=/opt/homebrew/bin/mosh-server user@host`.
    (On `scaleway-mini` the non-interactive ssh `PATH` already includes `/opt/homebrew/bin`, so no
      workaround is needed there.)
- Firewall (the subtle one): if the macOS **Application Firewall** is enabled, it **silently drops
    inbound UDP to `mosh-server`** because it's an unlisted Homebrew binary — on a headless Mac the
    "allow incoming connections?" prompt can never be answered, so it's blocked (and
    `socketfilterfw --getappblocked` misleadingly reports "permitted"). Symptom: mosh's SSH bootstrap
    works but the UDP session fails with "did not make a successful connection", even though plain
    UDP to an Apple-signed binary on the same host gets through. Fix — explicitly allow it:
    `sudo /usr/libexec/ApplicationFirewall/socketfilterfw --add /opt/homebrew/bin/mosh-server` then
    `--unblockapp /opt/homebrew/bin/mosh-server` (re-run after `brew upgrade mosh`, since the
    resolved Cellar path changes). Or disable the app firewall entirely on a tailnet-only host.
- Locale: macOS defaults to a UTF-8 locale, so nothing to do.
- Networking: see the Tailscale note below — reached over the tailnet, no public UDP ports are needed.

## Linux server (e.g. `eddings`, Ubuntu reached over Tailscale)

- Install mosh: `sudo apt-get update && sudo apt-get install -y mosh` (puts `mosh-server` in
    `/usr/bin`, always on `PATH`).
    On boxes managed by this dotfiles repo this is handled automatically — `mosh` is in the
      `ubuntu.apt` list of `.chezmoidata/system_packages_autoinstall.yaml`, so `chezmoi apply`
      installs it.
- Ensure `openssh-server` is running.
- Firewall (`ufw`), scoped to the tailnet rather than the public internet:
    `sudo ufw allow in on tailscale0 to any port 60000:61000 proto udp`.
- Locale: confirm `locale` shows a UTF-8 value (e.g. `LANG=en_US.UTF-8`); if not,
    `sudo update-locale LANG=C.UTF-8` and reconnect.

## Tailscale note

When you connect via a MagicDNS name like `eddings.tail26736d.ts.net` (or a Tailscale short name),
  the mosh UDP traffic rides the tailnet.
Tailscale handles NAT traversal, and the default ACL permits traffic between your own devices, so
  **no public UDP ports need opening** — only the host firewall matters, and it should be scoped to
  the `tailscale0` interface as shown above.
Prefer this over exposing UDP 60000–61000 on a public IP / cloud security group.

## Client side (iTerm2 DynamicProfiles)

The iTerm2 profiles run their `Command` directly in iTerm's GUI launch environment, whose PATH is
  just `/usr/bin:/bin:/usr/sbin:/sbin`. So use the **absolute binary path** `/opt/homebrew/bin/mosh`
  (a bare `mosh` yields "No such file or directory" — the `zellij` parent profile uses an absolute
  path for the same reason).

So each profile's command looks like `/opt/homebrew/bin/mosh <host>` (plus
  `--server=/opt/homebrew/bin/mosh-server` when the *target* is a macOS host reached via regular
  sshd, e.g. mantis, whose inbound PATH is likewise bare).

iTerm already exports a UTF-8 `LANG`, so no locale wrapper is needed in the command.

### macOS Local Network privacy (the gotcha that looks like a network error)

On macOS 26 (Tahoe) / Sequoia, `mosh-client` is silently blocked from sending to the Tailscale
  range (`100.64.0.0/10`) unless the launching app has **Local Network** permission — packets are
  dropped with no error, which presents exactly like "mosh did not make a successful connection /
  UDP port firewalled" even though the firewall, ACL, and raw UDP are all fine.
Fix: System Settings → Privacy & Security → **Local Network** → enable **iTerm** (and Tailscale,
  and Terminal if used). This is a per-machine privacy grant, not chezmoi-managed.

## Verify

- `mosh user@host` connects to an interactive shell.
- With the session open, toggle Wi-Fi off/on and sleep/wake the laptop; the session should show
    `[mosh] …` reconnecting and resume intact instead of the terminal closing.
