#!/bin/sh
# kiwi-proxy tor provider — a Tor client exposing SOCKS5 on 0.0.0.0:9050, reachable
# on the providers bridge at this container's address. IsolateSOCKSAuth turns the
# per-profile credentials the gateway forwarder sends into per-profile circuits.
set -eu

DATA=/tmp/tor-data
TORRC=/tmp/torrc
mkdir -p "$DATA"

{
    # IsolateSOCKSAuth turns the per-profile credentials the gateway forwarder
    # sends into per-profile circuits; with the forwarder in passthrough mode it
    # also gives Tor Browser a circuit per first-party site. KeepAliveIsolateSOCKSAuth
    # keeps a site's circuit alive while it still has open streams (past the usual
    # MaxCircuitDirtiness), and ExtendedErrors maps .onion failures to the SOCKS5
    # reply codes the forwarder relays back. Both match Tor Browser's own
    # extensions.torlauncher.socks_port_flags.
    echo "SocksPort 0.0.0.0:9050 IsolateSOCKSAuth IsolateClientAddr KeepAliveIsolateSOCKSAuth ExtendedErrors"
    echo "DataDirectory $DATA"
    echo "ClientOnly 1"
    echo "Log notice stdout"
    # Where the exit may leave. Only these countries ({de}) and relays ($FP), held
    # to (StrictNodes) rather than silently exiting elsewhere; never these
    # countries, which win over the first list in Tor.
    if [ -n "${KF_TOR_EXIT_NODES:-}" ]; then
        echo "ExitNodes ${KF_TOR_EXIT_NODES}"
        echo "StrictNodes 1"
    elif [ -n "${KF_TOR_EXIT_COUNTRY:-}" ]; then
        # an older kiwi-proxy: one country
        echo "ExitNodes {${KF_TOR_EXIT_COUNTRY}}"
        echo "StrictNodes 1"
    fi
    if [ -n "${KF_TOR_EXCLUDE_EXIT_NODES:-}" ]; then
        echo "ExcludeExitNodes ${KF_TOR_EXCLUDE_EXIT_NODES}"
    fi
    # never any relay of a circuit in these countries (entry, middle, exit), held to
    if [ -n "${KF_TOR_EXCLUDE_NODES:-}" ]; then
        echo "ExcludeNodes ${KF_TOR_EXCLUDE_NODES}"
        echo "StrictNodes 1"
    fi
    # Tor's monitor (nyx, `kiwi-proxy nyx EXIT`) inside this container only: the
    # control port listens on the container's own loopback, with a cookie.
    echo "ControlPort 127.0.0.1:9051"
    echo "CookieAuthentication 1"
    # A Tor exit for Tor Browser: a control port on the providers bridge for its
    # gateway's filter (New Identity, the circuit display, onion-site keys),
    # password-protected; nothing else is let through that filter.
    if [ -n "${KF_TOR_CONTROL_PASSWORD:-}" ]; then
        echo "ControlPort 0.0.0.0:9052"
        echo "HashedControlPassword $(tor --quiet --hash-password "$KF_TOR_CONTROL_PASSWORD" | tail -1)"
    fi
} > "$TORRC"

exec tor -f "$TORRC"
