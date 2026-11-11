"""Tor provider: exit through the Tor network.

Tor already speaks SOCKS5, so there is no adapter — the daemon's SocksPort is the
exit. Per-exit credentials become circuit isolation: kiwi-proxy mints a stable
token per exit and the gateway forwarder sends it, so IsolateSOCKSAuth gives
each exit its own circuit (its own exit node), consistently across bring-ups.

Free, no account. Where an exit may leave is chosen per exit: only some
countries and relays, never some countries (kiwi-proxy 0.9: `exit_selection`);
older kiwi-proxy versions ask for one country.
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
try:  # kiwi-proxy ≥ 0.9 offers the relays themselves
    from kiwi_proxy.providers.base import Node
except ImportError:  # pragma: no cover - older kiwi-proxy
    Node = None  # type: ignore[assignment,misc]

SOCKS_PORT = 9050

# The running exit relays, from the Tor project's own directory (Onionoo), cached
# for a day: the node list offers them (name, country, network, speed,
# fingerprint) and the country list counts them. Any country code works
# regardless — Tor just finds no circuit when there is no exit there.
ONIONOO = (
    "https://onionoo.torproject.org/details?type=relay&flag=Exit&running=true"
    "&fields=nickname,fingerprint,country,as_name,advertised_bandwidth"
)
CACHE_FILE = "exit-relays.json"
OLD_CACHE_FILE = "exit-countries.json"  # 0.3: counts only
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
    version="0.5.0",
    socks_port=SOCKS_PORT,
    auth="isolation",
    needs_account=False,
    requires=[],
    notes="free; per-exit circuit isolation; --country DE,SE --never HU --node FINGERPRINT",
)


class TorProvider(ContainerProvider):
    manifest = MANIFEST
    # A fresh circuit can take a while to bootstrap; wait for it before the window
    # opens so the first page load does not fail.
    ready_timeout = 120.0
    # Left out of kiwi-proxy's snapshots: a cache fetched again within a day.
    snapshot_exclude = (CACHE_FILE, OLD_CACHE_FILE)
    # kiwi-proxy 0.9 reads this with getattr: several countries and relays to exit
    # through only, countries never to exit through, per exit.
    exit_selection = True
    lease_noun = "relay"

    def container_spec(self, ctx, *, lease=None, country=None, selection=None):
        env = {}
        if selection is not None:
            exits = [f"{{{cc.lower()}}}" for cc in selection.only_countries]
            exits += [f"${fp}" for fp in selection.only_nodes]
            if exits:
                env["KF_TOR_EXIT_NODES"] = ",".join(exits)
            if selection.never_countries:
                env["KF_TOR_EXCLUDE_EXIT_NODES"] = ",".join(
                    f"{{{cc.lower()}}}" for cc in selection.never_countries
                )
            if getattr(selection, "control_password", ""):
                # Tor Browser's control port on the bridge, for the gateway's filter
                env["KF_TOR_CONTROL_PASSWORD"] = selection.control_password
            if getattr(selection, "never_anywhere", ()):
                env["KF_TOR_EXCLUDE_NODES"] = ",".join(
                    f"{{{cc.lower()}}}" for cc in selection.never_anywhere
                )
        else:
            # an older kiwi-proxy: one country, as a lease (before 0.4) or a country
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

    def relays(self, ctx) -> list[dict]:
        """The running exit relays from Onionoo, cached a day in the module's
        state; a stale cache when the directory is away; [] with neither."""
        cache = ctx.state_dir / CACHE_FILE
        try:
            if cache.exists() and time.time() - cache.stat().st_mtime < CACHE_SECONDS:
                return json.loads(cache.read_text())
        except (OSError, ValueError):
            pass
        try:
            found = _fetch_json(ONIONOO)
            relays = found.get("relays", []) if isinstance(found, dict) else []
            relays = [r for r in relays if isinstance(r, dict) and r.get("country")]
            if relays:
                ctx.state_dir.mkdir(parents=True, exist_ok=True)
                cache.write_text(json.dumps(relays))
                return relays
        except Exception:  # noqa: BLE001 - the directory, the network
            pass
        try:
            if cache.exists():
                return json.loads(cache.read_text())  # stale beats nothing
        except (OSError, ValueError):
            pass
        return []

    def exit_counts(self, ctx) -> dict[str, int]:
        """Running exit relays per country; {} when the directory was never
        reached (an 0.3 cache of counts is read then)."""
        relays = self.relays(ctx)
        if relays:
            counts = Counter(r["country"].upper() for r in relays)
            return dict(counts)
        try:
            return json.loads((ctx.state_dir / OLD_CACHE_FILE).read_text())
        except (OSError, ValueError):
            return {}

    def nodes(self, ctx):
        """The exit relays to choose from, fastest first (kiwi-proxy 0.9)."""
        if Node is None:  # pragma: no cover - an older kiwi-proxy never asks
            return []
        out = [
            Node(
                fingerprint=str(r.get("fingerprint", "")).upper(),
                name=str(r.get("nickname", "")),
                country=str(r.get("country", "")).upper(),
                operator=str(r.get("as_name") or ""),
                speed=int(r.get("advertised_bandwidth") or 0),
            )
            for r in self.relays(ctx)
            if r.get("fingerprint")
        ]
        return sorted(out, key=lambda n: (-n.speed, n.name.lower()))

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
