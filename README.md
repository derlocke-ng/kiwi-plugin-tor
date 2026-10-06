# kiwi-plugin-tor

A [kiwi-fox](https://github.com/derlocke-ng/kiwi-fox) provider module: exit a
browser identity through the **Tor network**.

Tor already speaks SOCKS5, so this module is just a Tor client in a container,
exposing its SocksPort on the `kf-providers` bridge where a kiwi-fox gateway can
reach it. Each profile gets its **own circuit** — kiwi-fox sends a stable
per-profile credential and Tor's `IsolateSOCKSAuth` isolates on it — so two
profiles on Tor do not share an exit.

Free; no account.

## Install

```sh
kiwi install kiwi-plugin-tor          # drops the module into kiwi-fox's modules dir
kiwi-fox module setup tor             # builds kiwi-fox/tor:latest  (or: kiwi-fox setup)
```

## Use

```sh
kiwi-fox module list                  # tor should appear
kiwi-fox module leases tor            # a few common exit countries
kiwi-fox new work --module tor --country de    # Tor produces the endpoint
kiwi-fox run work

# or bring the provider up yourself and point a profile at it:
kiwi-fox module up tor --lease de
kiwi-fox new work socks5://<ip>:9050 --module tor --lease de
```

An exit country (`--country` / `--lease`, a two-letter code) is held with
`StrictNodes`, so the exit really is in that country or the circuit fails rather
than silently exiting elsewhere. Omit it to let Tor choose.

## How it fits

```
Tor client container ── kf-providers bridge ── kiwi-fox gateway ── browser (joins gateway netns)
  SocksPort 0.0.0.0:9050                        permits only <tor-ip>:9050
  IsolateSOCKSAuth (per-profile circuits)       forwarder adds the per-profile token
```

The container runs unprivileged (`cap-drop all`, `no-new-privileges`); the torrc
and data directory live on a tmpfs and nothing is persisted. A shared Tor
container serves every profile on the same exit country and is torn down once no
running gateway still uses it.

See kiwi-fox's [docs/plugin-system.md](https://github.com/derlocke-ng/kiwi-fox/blob/main/docs/plugin-system.md)
for the provider contract.

## Development

```sh
make setup && make test     # needs a kiwi-fox checkout beside this repo (or KIWI_FOX_SRC)
make lint
```

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
