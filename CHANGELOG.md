# Changelog

All notable changes to kiwi-plugin-tor are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/); kiwi-updater installs the
latest tag matching `^v?[0-9]+(\.[0-9]+){0,3}$`.

## [Unreleased]

### Added
- Initial Tor provider module for kiwi-fox: a Tor client container exposing SOCKS5
  on the `kf-providers` bridge, with `IsolateSOCKSAuth` per-profile circuit
  isolation and optional `--country`/`--lease` exit selection.
- `module/provider.py` (`TorProvider`, `MANIFEST`), the container image
  (`module/containers/`), `kiwi.manifest`, `install.sh`, and unit tests against the
  kiwi-fox provider contract.
