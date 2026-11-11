"""The tor provider against the real kiwi-proxy contract (loaded by conftest)."""

from __future__ import annotations

import json

from kiwi_proxy import podman
from kiwi_proxy.models import ContainerSpec
from kiwi_proxy.providers.base import Country, Provider


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


def test_the_country_is_the_whole_choice(provider, ctx):
    # No leases: Tor picks the relay, the user picks the country.
    assert provider.leases(ctx) == [] and provider.leases(ctx, country="de") == []


def _directory(*countries):
    return {"relays": [{"country": cc} for cc in countries]}


def test_countries_come_from_the_directory_with_counts(module, provider, ctx, monkeypatch):
    asked = []

    def fetch(url, timeout=20):
        asked.append(url)
        return _directory("de", "de", "nl", "de", "us")

    monkeypatch.setattr(module, "_fetch_json", fetch)
    found = provider.countries(ctx)
    assert all(isinstance(c, Country) for c in found)
    assert sorted((c.code, c.name, c.count) for c in found) == [
        ("DE", "Germany", 3),
        ("NL", "Netherlands", 1),
        ("US", "United States", 1),
    ]
    assert asked == [module.ONIONOO] and "flag=Exit" in asked[0] and "running=true" in asked[0]
    cache = json.loads((ctx.state_dir / module.CACHE_FILE).read_text())
    assert sorted(r["country"] for r in cache) == ["de", "de", "de", "nl", "us"]


def test_countries_are_cached_for_a_day(module, provider, ctx, monkeypatch):
    monkeypatch.setattr(module, "_fetch_json", lambda url, timeout=20: _directory("se", "se"))
    assert [(c.code, c.count) for c in provider.countries(ctx)] == [("SE", 2)]

    def gone(url, timeout=20):
        raise OSError("offline")

    monkeypatch.setattr(module, "_fetch_json", gone)
    assert [(c.code, c.count) for c in provider.countries(ctx)] == [("SE", 2)]  # the cache
    # A stale cache is refreshed — and kept when the directory is away.
    import os

    cache = ctx.state_dir / module.CACHE_FILE
    os.utime(cache, (0, 0))
    assert [(c.code, c.count) for c in provider.countries(ctx)] == [("SE", 2)]
    monkeypatch.setattr(module, "_fetch_json", lambda url, timeout=20: _directory("at"))
    assert [(c.code, c.count) for c in provider.countries(ctx)] == [("AT", 1)]


def test_countries_fall_back_to_the_well_populated_ones(module, provider, ctx, monkeypatch):
    def gone(url, timeout=20):
        raise OSError("offline")

    monkeypatch.setattr(module, "_fetch_json", gone)
    found = provider.countries(ctx)
    assert [c.code for c in found] == [cc.upper() for cc in module.EXIT_COUNTRIES]
    assert all(c.count is None for c in found) and found[0].name == "Germany"


def test_snapshots_leave_out_what_the_module_rebuilds():
    """kiwi-proxy 0.8 reads this with getattr; older versions ignore it."""
    from module.provider import PROVIDER

    assert {"exit-relays.json", "exit-countries.json"} <= set(PROVIDER.snapshot_exclude)


def _relay(nick, cc, fp, asn="AS1", bw=100):
    return {
        "nickname": nick,
        "country": cc,
        "fingerprint": fp,
        "as_name": asn,
        "advertised_bandwidth": bw,
    }


def test_nodes_come_from_the_directory_fastest_first(module, provider, ctx, monkeypatch):
    fp = "A" * 40
    monkeypatch.setattr(
        module,
        "_fetch_json",
        lambda url, timeout=20: {
            "relays": [
                _relay("slow", "de", "b" * 40, bw=10),
                _relay("fast", "se", fp.lower(), "Bahnhof", 900),
            ]
        },
    )
    nodes = provider.nodes(ctx)
    assert [(n.name, n.country, n.operator, n.speed) for n in nodes] == [
        ("fast", "SE", "Bahnhof", 900),
        ("slow", "DE", "AS1", 10),
    ]
    assert nodes[0].fingerprint == fp  # upper case, as Tor takes it after a $
    assert {c.code: c.count for c in provider.countries(ctx)} == {"SE": 1, "DE": 1}


def test_a_selection_becomes_the_container_env(provider, ctx):
    from types import SimpleNamespace

    sel = SimpleNamespace(
        only_countries=("DE", "SE"), only_nodes=("A" * 40,), never_countries=("HU", "US")
    )
    env = provider.container_spec(ctx, lease="xabc", selection=sel).env
    assert env == {
        "KF_TOR_EXIT_NODES": "{de},{se},$" + "A" * 40,
        "KF_TOR_EXCLUDE_EXIT_NODES": "{hu},{us}",
    }
    never_only = SimpleNamespace(only_countries=(), only_nodes=(), never_countries=("GB",))
    assert provider.container_spec(ctx, selection=never_only).env == {
        "KF_TOR_EXCLUDE_EXIT_NODES": "{gb}"
    }
    # what an older kiwi-proxy asks for
    assert provider.container_spec(ctx, country="nl").env == {"KF_TOR_EXIT_COUNTRY": "nl"}
    assert provider.exit_selection is True
