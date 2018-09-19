#!/usr/bin/env bash

set -o errexit
set -o nounset

if ! command -v rustup > /dev/null ; then
  curl https://sh.rustup.rs -sSf | sh -s -- -y
fi

if ! rustup show | grep stable > /dev/null ; then
  rustup install stable
fi

rustup default stable

rustup update stable
