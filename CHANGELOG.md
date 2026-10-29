# Changelog

All notable changes to kiwi-plugin-tor are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); kiwi-updater installs the
latest tag matching `^v?[0-9]+(\.[0-9]+){0,3}$`.

## [Unreleased]

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
