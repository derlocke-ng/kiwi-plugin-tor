"""The tor provider against the real kiwi-fox contract (loaded by conftest)."""

from __future__ import annotations

from kiwi_fox.core import podman
from kiwi_fox.core.models import ContainerSpec, Lease
from kiwi_fox.core.providers.base import Provider


def test_manifest(manifest):
    assert manifest.name == "tor"
    assert manifest.socks_port == 9050
    assert manifest.auth == "isolation"
    assert manifest.needs_account is False


def test_provider_satisfies_the_contract(provider):
    assert isinstance(provider, Provider)
    assert provider.name == "tor"


def test_container_spec_is_on_the_bridge(provider, ctx):
    spec = provider.container_spec(ctx, lease="de")
    assert isinstance(spec, ContainerSpec)
    assert spec.network == "kf-providers"
    assert spec.image == ctx.image
    assert spec.name == "kf-prov-tor-de"
    assert spec.env["KF_TOR_EXIT_COUNTRY"] == "de"


def test_country_comes_from_lease_or_country(provider, ctx):
    assert provider.container_spec(ctx, country="se").env["KF_TOR_EXIT_COUNTRY"] == "se"
    assert "KF_TOR_EXIT_COUNTRY" not in provider.container_spec(ctx).env


def test_rendered_args_are_sane(provider, ctx):
    args = podman.spec_args(provider.container_spec(ctx, lease="de"))
    assert args[:2] == ["run", "--replace"]
    assert "--privileged" not in args
    assert "--network" in args and "kf-providers" in args


def test_leases_are_country_codes(provider, ctx):
    leases = provider.leases(ctx)
    assert leases and all(isinstance(lease, Lease) for lease in leases)
    assert "de" in {lease.id for lease in leases}
    assert all(lease.id == lease.id.lower() for lease in leases)
