"""The rendered torrc: run the real entrypoint with a fake `tor` that captures
the config file it is handed, so the SocksPort flags are checked as shipped."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

ENTRYPOINT = Path(__file__).resolve().parents[2] / "module" / "containers" / "entrypoint.sh"


def _render(tmp_path: Path, env_extra: dict[str, str]) -> str:
    # A fake `tor` that copies its `-f <file>` argument to a known place and exits,
    # so exec'ing it ends the script cleanly instead of launching Tor.
    capture = tmp_path / "torrc.captured"
    bindir = tmp_path / "bin"
    bindir.mkdir()
    fake = bindir / "tor"
    fake.write_text(f'#!/bin/sh\n# args: -f <torrc>\ncp "$2" "{capture}"\nexit 0\n')
    fake.chmod(0o755)
    env = {**os.environ, "PATH": f"{bindir}:{os.environ['PATH']}", **env_extra}
    subprocess.run(["sh", str(ENTRYPOINT)], env=env, check=True, timeout=30)
    return capture.read_text()


def test_socksport_flags_are_present(tmp_path):
    torrc = _render(tmp_path, {})
    socks = next(line for line in torrc.splitlines() if line.startswith("SocksPort"))
    for flag in (
        "IsolateSOCKSAuth",
        "IsolateClientAddr",
        "KeepAliveIsolateSOCKSAuth",
        "ExtendedErrors",
    ):
        assert flag in socks, flag
    assert "ClientOnly 1" in torrc


def test_exit_country_is_pinned_when_asked(tmp_path):
    torrc = _render(tmp_path, {"KF_TOR_EXIT_COUNTRY": "de"})
    assert "ExitNodes {de}" in torrc
    assert "StrictNodes 1" in torrc


def test_no_exit_country_by_default(tmp_path):
    assert "ExitNodes" not in _render(tmp_path, {})


def test_only_and_never_lists(tmp_path):
    torrc = _render(
        tmp_path,
        {"KF_TOR_EXIT_NODES": "{de},{se},$" + "A" * 40, "KF_TOR_EXCLUDE_EXIT_NODES": "{hu},{us}"},
    )
    assert "ExitNodes {de},{se},$" + "A" * 40 in torrc
    assert "StrictNodes 1" in torrc
    assert "ExcludeExitNodes {hu},{us}" in torrc


def test_never_alone_leaves_the_exits_to_tor(tmp_path):
    torrc = _render(tmp_path, {"KF_TOR_EXCLUDE_EXIT_NODES": "{gb}"})
    assert "ExcludeExitNodes {gb}" in torrc and "ExitNodes {" not in torrc.replace(
        "ExcludeExitNodes", ""
    )


def test_every_relay_and_the_monitor(tmp_path):
    torrc = _render(tmp_path, {"KF_TOR_EXCLUDE_NODES": "{us},{gb}"})
    assert "ExcludeNodes {us},{gb}" in torrc and "StrictNodes 1" in torrc
    assert "ControlPort 127.0.0.1:9051" in torrc and "CookieAuthentication 1" in torrc
