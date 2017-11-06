#!/usr/bin/env bash

set -o errexit
set -o nounset

if ! which rustup > /dev/null ; then 
  curl https://sh.rustup.rs -sSf | sh -s -- -y
fi

if ! rustup show | grep nightly > /dev/null ; then
  rustup install nightly
fi

rustup update
