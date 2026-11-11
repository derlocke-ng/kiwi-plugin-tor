# Changelog

All notable changes to kiwi-plugin-tor are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); kiwi-updater installs the
latest tag matching `^v?[0-9]+(\.[0-9]+){0,3}$`.

## [Unreleased]

## [0.4.1] - 2026-11-11

### Added
- `ExcludeNodes` for the Eyes group at every position when kiwi-proxy 0.9.3's
  preference asks for it.
- nyx in the image and a control port on the container's own loopback (cookie
  authentication), for `kiwi-proxy nyx EXIT`. The image builds without nyx too.

## [0.4.0] - 2026-11-11

### Added
- **Several exit countries and relays, and countries never to use** (kiwi-proxy
  0.9: `exit_selection`): the container's torrc gets `ExitNodes {de},{se},$FP`
  with `StrictNodes 1` and `ExcludeExitNodes {hu},…`. An older kiwi-proxy still
  asks for one country, which still works.
- **The relays themselves:** the running exit relays from Onionoo with nickname,
  fingerprint, country, network and advertised speed, cached a day
  (`exit-relays.json`, left out of snapshots like the old count cache); the
  country counts come from the same list.

## [0.3.1] - 2026-11-10

- Snapshots (kiwi-proxy 0.8) leave out the exit-country cache; it is fetched again
  within a day (`snapshot_exclude`).

## [0.3.0] - 2026-11-07

### Changed
- **Every exit country, not eight.** The module tells kiwi-proxy 0.4 where Tor
  has running exit relays — from the Tor project's directory (Onionoo), counted
  per country and cached for a day in the module's state — and the exit editor
  offers that as a searchable list with names and counts (`kiwi-proxy module
  countries tor`). With the directory out of reach and nothing cached, the
  twelve well-populated countries are offered.
- The country is the whole choice: `leases()` is empty, Tor picks the relay.
  Exits made with `--lease de` by earlier versions keep working.

## [0.2.1] - 2026-10-29

### Changed
- Wording: kiwi-proxy works per exit, not per kiwi-fox profile, and the module's
  texts now say so.

## [0.2.0] - 2026-10-29

### Changed
- Now a **kiwi-proxy** provider module: kiwi-fox's proxy engine moved to
  [kiwi-proxy](https://github.com/derlocke-ng/kiwi-proxy), which loads this module
  for every consumer (kiwi-fox, kiwi-pentesting, exits published on the host). The
  module imports `kiwi_proxy.models` / `kiwi_proxy.providers.base` (was
  `kiwi_fox.core.…`), installs into `~/.local/share/kiwi-proxy/modules/`, labels its
  containers `kiwi-proxy.*`, builds `kiwi-proxy/…` images, and depends on kiwi-proxy.
- `install.sh` removes the copy under kiwi-fox's old modules directory and takes its
  module state along.

## [0.1.1] - 2026-10-29

### Changed
- torrc SocksPort now also sets `KeepAliveIsolateSOCKSAuth` and `ExtendedErrors`,
  matching Tor Browser's own launcher flags: a site's circuit survives while it has
  open streams, and `.onion` failures map to the SOCKS5 reply codes the gateway
  forwarder relays back. Harmless for existing Camoufox/Firefox profiles; it is what
  lets the coming Tor Browser engine keep a circuit per first-party site.

## [0.1.0] - 2026-10-28

### Added
- Initial Tor provider module for kiwi-fox: a Tor client container exposing SOCKS5
  on the `kf-providers` bridge, with `IsolateSOCKSAuth` per-profile circuit
  isolation and optional `--country`/`--lease` exit selection.
- `module/provider.py` (`TorProvider`, `MANIFEST`), the container image
  (`module/containers/`), `kiwi.manifest`, `install.sh`, and unit tests against the
  kiwi-fox provider contract.
