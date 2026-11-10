"""Tor provider: exit through the Tor network.

Tor already speaks SOCKS5, so there is no adapter — the daemon's SocksPort is the
exit. Per-exit credentials become circuit isolation: kiwi-proxy mints a stable
token per exit and the gateway forwarder sends it, so IsolateSOCKSAuth gives
each exit its own circuit (its own exit node), consistently across bring-ups.

Free, no account. An exit country can be requested with --country / --lease.
"""

from __future__ import annotations

import json
import time
import urllib.request
from collections import Counter

from kiwi_proxy.models import ContainerSpec, ProviderManifest
from kiwi_proxy.providers.base import ContainerProvider

try:  # kiwi-proxy ≥ 0.4 asks modules where they can exit; older ones never do
    from kiwi_proxy import countries as _countries
    from kiwi_proxy.providers.base import Country
except ImportError:  # pragma: no cover - kiwi-proxy 0.3
    _countries = None
    Country = None  # type: ignore[assignment,misc]

SOCKS_PORT = 9050

# Where Tor has running exit relays, from the Tor project's own directory
# (Onionoo), counted per country and cached for a day; these are what the
# country list offers. Any country code works with --country regardless — Tor
# just finds no circuit when there is no exit there.
ONIONOO = "https://onionoo.torproject.org/details?type=relay&flag=Exit&running=true&fields=country"
CACHE_FILE = "exit-countries.json"
CACHE_SECONDS = 24 * 3600
# When the directory is out of reach and nothing is cached: the well-populated ones.
EXIT_COUNTRIES = {
    "de": "Germany",
    "us": "United States",
    "nl": "Netherlands",
    "se": "Sweden",
    "gb": "United Kingdom",
    "fr": "France",
    "ch": "Switzerland",
    "ca": "Canada",
    "at": "Austria",
    "no": "Norway",
    "ro": "Romania",
    "fi": "Finland",
}


def _fetch_json(url: str, timeout: float = 20) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as resp:  # noqa: S310
        return json.loads(resp.read().decode("utf-8", "replace"))


MANIFEST = ProviderManifest(
    name="tor",
    title="Tor",
    description="exit through the Tor network",
    version="0.3.1",
    socks_port=SOCKS_PORT,
    auth="isolation",
    needs_account=False,
    requires=[],
    notes="free; per-exit circuit isolation; pick an exit country with --country",
)


class TorProvider(ContainerProvider):
    manifest = MANIFEST
    # A fresh circuit can take a while to bootstrap; wait for it before the window
    # opens so the first page load does not fail.
    ready_timeout = 120.0
    # Left out of kiwi-proxy's snapshots: a cache fetched again within a day.
    snapshot_exclude = (CACHE_FILE,)

    def container_spec(self, ctx, *, lease=None, country=None):
        env = {}
        cc = (lease or country or "").lower()
        if cc:
            env["KF_TOR_EXIT_COUNTRY"] = cc
        return ContainerSpec(
            name=ctx.container_name(lease),
            image=ctx.image,
            network=ctx.network,
            env=env,
            cap_drop=["all"],
            security_opt=["no-new-privileges"],
            tmpfs=["/tmp"],  # torrc + DataDirectory, nothing persisted
            labels={"kiwi-proxy.module": self.name, "kiwi-proxy.role": "provider"},
        )

    def leases(self, ctx, *, country=None):
        # The country is the whole choice: Tor picks the relay. (Exits made with
        # `--lease de` by earlier versions still work: container_spec reads either.)
        return []

    def exit_counts(self, ctx) -> dict[str, int]:
        """Running exit relays per country, from Onionoo, cached a day in the
        module's state; the static list without counts when neither is there."""
        cache = ctx.state_dir / CACHE_FILE
        try:
            if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_SECONDS:
                return json.loads(cache.read_text())
        except (OSError, ValueError):
            pass
        try:
            found = _fetch_json(ONIONOO)
            relays = found.get("relays", []) if isinstance(found, dict) else []
            counts = Counter(r.get("country") for r in relays if r.get("country"))
            counts = {cc.upper(): n for cc, n in counts.items()}
            if counts:
                ctx.state_dir.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(counts))
                return counts
        except Exception:  # noqa: BLE001 - the directory, the network
            pass
        try:
            if cache.exists():
                return json.loads(cache.read_text())  # stale beats nothing
        except (OSError, ValueError):
            pass
        return {}

    def countries(self, ctx):
        if Country is None:  # pragma: no cover - kiwi-proxy 0.3 never asks
            return []
        counts = self.exit_counts(ctx)
        if counts:
            return [Country(cc, _countries.name(cc), n) for cc, n in counts.items()]
        return [Country(cc.upper(), name) for cc, name in EXIT_COUNTRIES.items()]

    def ready(self, ctx, container):
        # The SOCKS port answers at once, but a circuit is only usable once Tor has
        # bootstrapped — wait for that marker in the log.
        from kiwi_proxy import podman

        return "Bootstrapped 100%" in podman.logs(container, tail=200)


PROVIDER = TorProvider()
