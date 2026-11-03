#!/usr/bin/env bash
# Builds the engine image and runs unoserver for the engine tests. Ctrl+C stops it.
set -e

# Go to the repo root, where the Dockerfile is, wherever the script is run from.
cd "$(dirname "$0")/.."

docker build -t diplex-core .

# Published on this machine's loopback only; inside the container unoserver listens on all interfaces.
docker run --rm --name diplex-unoserver -p 127.0.0.1:2003:2003 diplex-core unoserver --interface 0.0.0.0 --uno-interface 127.0.0.1
