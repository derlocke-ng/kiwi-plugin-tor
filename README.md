# kiwi-plugin-tor

A [kiwi-proxy](https://github.com/derlocke-ng/kiwi-proxy) provider module: send an
exit — a kiwi-fox browser identity, kiwi-pentesting's tools, a SOCKS5 port on
the host — through the **Tor network**.

Tor already speaks SOCKS5, so this module is just a Tor client in a container,
exposing its SocksPort on the `kf-providers` bridge where a kiwi-proxy gateway can
reach it. Each exit gets its **own circuit** — kiwi-proxy sends a stable
per-exit credential and Tor's `IsolateSOCKSAuth` isolates on it — so two
exits on Tor do not share a circuit.

Free; no account.

## Install

```sh
kiwi install kiwi-plugin-tor          # drops the module into kiwi-proxy's modules dir
kiwi-proxy module setup tor             # builds kiwi-proxy/tor:latest  (or: kiwi-proxy setup)
```

## Use

```sh
kiwi-proxy module list                  # tor should appear
kiwi-proxy module leases tor            # a few common exit countries
kiwi-proxy add work --module tor --country de   # an exit: `kiwi-proxy up work`, --expose PORT for the host
kiwi-fox new work --module tor --country de    # Tor produces the endpoint
kiwi-fox run work

# or bring the provider up yourself and point a profile at it:
kiwi-proxy module up tor --lease de
kiwi-fox new work socks5://<ip>:9050 --module tor --lease de
```

An exit country (`--country` / `--lease`, a two-letter code) is held with
`StrictNodes`, so the exit really is in that country or the circuit fails rather
than silently exiting elsewhere. Omit it to let Tor choose.

## How it fits

```
Tor client container ── kf-providers bridge ── kiwi-proxy gateway ── browser (joins gateway netns)
  SocksPort 0.0.0.0:9050                        permits only <tor-ip>:9050
  IsolateSOCKSAuth (per-exit circuits)          forwarder adds the per-exit token
```

The container runs unprivileged (`cap-drop all`, `no-new-privileges`); the torrc
and data directory live on a tmpfs and nothing is persisted. A shared Tor
container serves every exit on the same exit country and is torn down once no
running gateway still uses it.

See kiwi-proxy's [docs/plugin-system.md](https://github.com/derlocke-ng/kiwi-proxy/blob/main/docs/plugin-system.md)
for the provider contract.

## Development

```sh
make setup && make test     # needs a kiwi-proxy checkout beside this repo (or KIWI_PROXY_SRC)
make lint
```

## License

GPL-3.0-or-later — see [LICENSE](LICENSE).
