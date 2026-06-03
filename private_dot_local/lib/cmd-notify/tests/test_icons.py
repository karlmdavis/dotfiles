"""Unit tests for icon cache lookup + fetch.

No live network: cache-hit and .miss cases need none; the fetch-success path uses a local file://
URL (deterministic, mirrors the no-mock philosophy); the fetch-failure path uses an unreachable
.invalid URL with a short timeout.
"""

from __future__ import annotations

from cmd_notify import icons


def _icons_file(tmp_path, contents):
    path = tmp_path / "icons.txt"
    path.write_text(contents, encoding="utf-8")
    return str(path)


# --- lookup_url -----------------------------------------------------------------------------


def test_lookup_url_hit(tmp_path):
    f = _icons_file(tmp_path, "# comment\ncargo=http://example.test/cargo.png\ngh=http://x/gh.png\n")
    assert icons.lookup_url("cargo", f) == "http://example.test/cargo.png"


def test_lookup_url_miss(tmp_path):
    f = _icons_file(tmp_path, "gh=http://x/gh.png\n")
    assert icons.lookup_url("cargo", f) is None


def test_lookup_url_ignores_comments_and_blanks(tmp_path):
    f = _icons_file(tmp_path, "\n# cargo=commented-out\n\ncargo=http://real/c.png\n")
    assert icons.lookup_url("cargo", f) == "http://real/c.png"


def test_lookup_url_missing_file(tmp_path):
    assert icons.lookup_url("cargo", str(tmp_path / "nope.txt")) is None


# --- resolve --------------------------------------------------------------------------------


def test_resolve_cache_hit_no_fetch(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "cargo.png").write_text("fake-png", encoding="utf-8")
    # URL points at an unreachable host; a cache hit must not attempt a fetch.
    f = _icons_file(tmp_path, "cargo=http://example.invalid/should-not-fetch.png")
    assert icons.resolve("cargo", cache_dir=str(cache), icons_file=f) == str(cache / "cargo.png")


def test_resolve_miss_sentinel_no_fetch(tmp_path):
    cache = tmp_path / "cache"
    cache.mkdir()
    (cache / "cargo.miss").write_text("", encoding="utf-8")
    f = _icons_file(tmp_path, "cargo=http://example.invalid/cargo.png")
    assert icons.resolve("cargo", cache_dir=str(cache), icons_file=f) is None


def test_resolve_unknown_key_no_fetch(tmp_path):
    cache = tmp_path / "cache"
    f = _icons_file(tmp_path, "")  # empty table
    assert icons.resolve("cargo", cache_dir=str(cache), icons_file=f) is None


def test_resolve_fetch_success_caches(tmp_path):
    # Serve the icon from a local file:// URL so the fetch is deterministic and offline.
    src = tmp_path / "src-cargo.png"
    src.write_bytes(b"\x89PNG\r\n\x1a\n fake")
    cache = tmp_path / "cache"
    f = _icons_file(tmp_path, f"cargo={src.as_uri()}")

    result = icons.resolve("cargo", cache_dir=str(cache), icons_file=f)
    assert result == str(cache / "cargo.png")
    assert (cache / "cargo.png").read_bytes() == b"\x89PNG\r\n\x1a\n fake"


def test_ssl_context_returns_a_context():
    # Whether or not truststore is importable, we get a usable SSLContext (no exception).
    import ssl

    assert isinstance(icons._ssl_context(), ssl.SSLContext)


def test_resolve_fetch_failure_writes_miss(tmp_path):
    cache = tmp_path / "cache"
    # file:// to a nonexistent path fails fast (no network/timeout wait).
    f = _icons_file(tmp_path, f"cargo={(tmp_path / 'does-not-exist.png').as_uri()}")

    assert icons.resolve("cargo", cache_dir=str(cache), icons_file=f) is None
    assert (cache / "cargo.miss").is_file()
    # A second call sees the sentinel and stays None without retrying.
    assert icons.resolve("cargo", cache_dir=str(cache), icons_file=f) is None
