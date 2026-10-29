#!/bin/sh
# kiwi-fox tor provider — a Tor client exposing SOCKS5 on 0.0.0.0:9050, reachable
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
    if [ -n "${KF_TOR_EXIT_COUNTRY:-}" ]; then
        # The user asked for this country, so hold to it (StrictNodes) rather than
        # silently exiting elsewhere.
        echo "ExitNodes {${KF_TOR_EXIT_COUNTRY}}"
        echo "StrictNodes 1"
    fi
} > "$TORRC"

exec tor -f "$TORRC"
