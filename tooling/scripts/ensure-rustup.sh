#!/usr/bin/env bash

set -o errexit
set -o nounset
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# shellcheck source=tooling/scripts/common.sh
source "$HERE/common.sh"

RUSTUP="$CARGO_HOME/bin/rustup"

if ! [ -e "$RUSTUP" ] ; then
  curl https://sh.rustup.rs -sSf | sh -s -- -y
fi

if ! "$RUSTUP" show | grep stable > /dev/null ; then
"  $RUSTUP" install stable
fi

"$RUSTUP" default stable

"$RUSTUP" update stable
