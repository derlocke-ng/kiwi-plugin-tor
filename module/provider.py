"""Tor provider: exit through the Tor network.

Tor already speaks SOCKS5, so there is no adapter — the daemon's SocksPort is the
exit. Per-exit credentials become circuit isolation: kiwi-proxy mints a stable
token per exit and the gateway forwarder sends it, so IsolateSOCKSAuth gives
each exit its own circuit (its own exit node), consistently across bring-ups.

Free, no account. An exit country can be requested with --country / --lease.
"""

from __future__ import annotations

from kiwi_proxy.models import ContainerSpec, Lease, ProviderManifest
from kiwi_proxy.providers.base import ContainerProvider

SOCKS_PORT = 9050

# Offered by name; Tor has exits in many more countries — any two-letter code
# works via --country. These are common, well-populated exit countries.
EXIT_COUNTRIES = {
    "de": "Germany",
    "us": "United States",
    "nl": "Netherlands",
    "se": "Sweden",
    "gb": "United Kingdom",
    "fr": "France",
    "ch": "Switzerland",
    "ca": "Canada",
}

MANIFEST = ProviderManifest(
    name="tor",
    title="Tor",
    description="exit through the Tor network",
    version="0.2.1",
    socks_port=SOCKS_PORT,
    auth="isolation",
    needs_account=False,
    requires=[],
    notes="free; per-exit circuit isolation; pick an exit country with --country/--lease",
)


class TorProvider(ContainerProvider):
    manifest = MANIFEST
    # A fresh circuit can take a while to bootstrap; wait for it before the window
    # opens so the first page load does not fail.
    ready_timeout = 120.0

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

    def leases(self, ctx):
        return [Lease(id=cc, country=cc.upper(), label=name) for cc, name in EXIT_COUNTRIES.items()]

    def ready(self, ctx, container):
        # The SOCKS port answers at once, but a circuit is only usable once Tor has
        # bootstrapped — wait for that marker in the log.
        from kiwi_proxy import podman

        return "Bootstrapped 100%" in podman.logs(container, tail=200)


PROVIDER = TorProvider()
