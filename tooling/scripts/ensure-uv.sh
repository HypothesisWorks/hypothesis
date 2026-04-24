#!/usr/bin/env bash

# Ensure `uv` is installed and on PATH. If it's already available via PATH
# or a well-known location, do nothing; otherwise fetch the standalone
# installer from astral.sh.

set -o errexit
set -o nounset

if [ -x "$HOME/.local/bin/uv" ] || command -v uv >/dev/null 2>&1 ; then
    exit 0
fi

if [ -n "${CI:-}" ] ; then echo "::group::Install uv" ; fi

curl -LsSf https://astral.sh/uv/install.sh | sh

if [ -n "${CI:-}" ] ; then echo "::endgroup::" ; fi
