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
    fake.write_text(
        "#!/bin/sh\n"
        '# args: -f <torrc>\n'
        f'cp "$2" "{capture}"\n'
        "exit 0\n"
    )
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
