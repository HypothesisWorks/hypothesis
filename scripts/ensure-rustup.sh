#!/usr/bin/env bash

set -e -x

if which rustup > /dev/null ; then 
  rustup update
else
  curl https://sh.rustup.rs -sSf | sh -s -- --yes
fi
