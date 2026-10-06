#!/bin/sh
# kiwi-fox tor provider — a Tor client exposing SOCKS5 on 0.0.0.0:9050, reachable
# on the providers bridge at this container's address. IsolateSOCKSAuth turns the
# per-profile credentials the gateway forwarder sends into per-profile circuits.
set -eu

DATA=/tmp/tor-data
TORRC=/tmp/torrc
mkdir -p "$DATA"

{
    echo "SocksPort 0.0.0.0:9050 IsolateSOCKSAuth IsolateClientAddr"
    echo "DataDirectory $DATA"
    echo "ClientOnly 1"
    echo "Log notice stdout"
    if [ -n "${KF_TOR_EXIT_COUNTRY:-}" ]; then
        # The user asked for this country, so hold to it (StrictNodes) rather than
        # silently exiting elsewhere.
        echo "ExitNodes {${KF_TOR_EXIT_COUNTRY}}"
        echo "StrictNodes 1"
    fi
} > "$TORRC"

exec tor -f "$TORRC"
