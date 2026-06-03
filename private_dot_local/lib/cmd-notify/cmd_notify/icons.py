"""Optional per-command icons: cache lookup + lazy fetch.

Icons are keyed by a command's leading token (its basename). A URL map lives in a `key=url` file
(default ~/.local/share/cmd-notify/icons.txt). The first successful fetch caches the image at
<cache_dir>/<key>.png; a sibling <key>.miss sentinel prevents retrying a failed download.

This module holds the only network / filesystem-writing I/O in cmd-notify. The fetch uses stdlib
urllib (no curl dependency), mirroring the old `curl --max-time 5 --fail --location` semantics: a
5s timeout, redirects followed by default, and any non-2xx / error leaving a .miss sentinel.

TLS trust: urllib normally verifies against Python's bundled CA store, which omits
corporate-MITM roots (e.g. Zscaler) that live in the OS keychain — so fetches would fail on such
machines where the old curl-based version (which trusts the system store) succeeded. We use
`truststore` to back urllib's verification with the OS trust store (macOS Keychain, Linux system
certs). It's declared as a dep on the shim; if it's somehow unavailable we fall back to default
verification rather than failing to import.
"""

from __future__ import annotations

import os
import ssl
import tempfile
import urllib.request

FETCH_TIMEOUT_SECONDS = 5


def _ssl_context() -> ssl.SSLContext:
    """An SSL context that trusts the OS trust store when `truststore` is available.

    Falls back to the stdlib default context (bundled CAs) if truststore can't be imported, so the
    module stays usable in environments where it isn't installed.
    """
    try:
        import truststore

        return truststore.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    except Exception:
        return ssl.create_default_context()


def lookup_url(cmd_base: str, icons_file: str) -> str | None:
    """Return the icon URL mapped to `cmd_base` in the `key=url` icons file, or None.

    Lines are `key=url`; `#` comments and blank lines are ignored. First match wins.
    """
    try:
        with open(icons_file, encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                key, sep, url = line.partition("=")
                if sep and key == cmd_base and url:
                    return url
    except FileNotFoundError:
        return None
    return None


def _fetch(url: str, dest: str) -> bool:
    """Download `url` to `dest` (atomic via temp file + replace). True on success.

    Mirrors curl `--fail` (non-2xx raises), `--location` (urllib follows redirects), and
    `--max-time 5` (per-connection timeout). Any error is swallowed and reported as False.
    """
    dest_dir = os.path.dirname(dest)
    tmp_fd, tmp_path = tempfile.mkstemp(prefix=".fetch.", dir=dest_dir)
    try:
        with urllib.request.urlopen(
            url, timeout=FETCH_TIMEOUT_SECONDS, context=_ssl_context()
        ) as response:
            # urlopen raises HTTPError for 4xx/5xx, so reaching here means a 2xx.
            with os.fdopen(tmp_fd, "wb") as out:
                out.write(response.read())
        os.replace(tmp_path, dest)
        return True
    except Exception:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        return False


def resolve(cmd_base: str, *, cache_dir: str, icons_file: str) -> str | None:
    """Resolve an icon path for `cmd_base`, fetching once if needed.

    Returns a cached PNG path, or None when there's no icon (no mapping, prior failed fetch
    recorded by a .miss sentinel, or this fetch fails). Never raises on network/FS errors.
    """
    icon_path = os.path.join(cache_dir, f"{cmd_base}.png")
    miss_path = os.path.join(cache_dir, f"{cmd_base}.miss")

    if os.path.isfile(icon_path):
        return icon_path
    if os.path.isfile(miss_path):
        return None

    url = lookup_url(cmd_base, icons_file)
    if not url:
        return None

    os.makedirs(cache_dir, exist_ok=True)
    if _fetch(url, icon_path):
        return icon_path
    # Record the miss so we don't retry on every subsequent command.
    try:
        open(miss_path, "w").close()
    except OSError:
        pass
    return None
