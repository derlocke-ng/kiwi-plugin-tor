#!/usr/bin/env bash
# Build the module's image the way `kiwi-proxy module setup tor` does and run it
# once. The 0.2.x provider images shipped without anyone having built them — the
# unit tests never touch a Containerfile — and a build can succeed and leave an
# image with nothing in it, so the binary is run and the entrypoint is started.
#
#   tests/smoke/images.sh [podman build flags]      images.yml passes --no-cache
#
# A distinct tag: kiwi-proxy/tor:latest, the one kiwi-proxy runs, is left alone.
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")/../.."

IMAGE=kiwi-proxy/tor:smoke
NAME=kf-smoke-tor
fail() { printf 'smoke: FAIL: %s\n' "$*" >&2; podman logs "$NAME" >&2 2>&1 || true; exit 1; }
cleanup() { podman rm -f -t 0 "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
cleanup

echo "== build $IMAGE"
podman build "$@" -t "$IMAGE" -f module/containers/Containerfile module/containers

echo "== tor is in the image, runs, and the image runs unprivileged"
# No `head` or `grep -q` on podman's own output: their early exit gives podman
# a SIGPIPE, which pipefail reports as a failure (exit 141) — so the pipe runs in
# the container, and grep reads to the end.
podman run --rm --entrypoint sh "$IMAGE" -c 'tor --version | head -1'
test "$(podman run --rm --entrypoint id "$IMAGE" -un)" = tor || fail "the image does not run as the tor user"

echo "== the entrypoint's torrc is accepted and the SOCKS port opens"
podman run --detach --name "$NAME" "$IMAGE" >/dev/null
for _ in $(seq 1 40); do
    if podman logs "$NAME" 2>&1 | grep -F 'Opened Socks listener connection (ready) on 0.0.0.0:9050' >/dev/null; then
        echo "ok: tor opened its SOCKS listener on 0.0.0.0:9050"
        exit 0
    fi
    [ "$(podman inspect -f '{{.State.Running}}' "$NAME")" = true ] || fail "tor exited during startup"
    sleep 0.5
done
fail "tor did not open its SOCKS listener within 20 s"
