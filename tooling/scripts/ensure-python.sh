#!/usr/bin/env bash

set -o errexit
set -o nounset
set -x

HERE="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

# shellcheck source=tooling/scripts/common.sh
source "$HERE/common.sh"

# This is to guard against multiple builds in parallel. The various installers will tend
# to stomp all over each other if you do this and they haven't previously successfully
# succeeded. We use a lock file to block progress so only one install runs at a time.
# This script should be pretty fast once files are cached, so the loss of concurrency
# is not a major problem.
# This should be using the lockfile command, but that's not available on the
# containerized travis and we can't install it without sudo.
# It is unclear if this is actually useful. I was seeing behaviour that suggested
# concurrent runs of the installer, but I can't seem to find any evidence of this lock
# ever not being acquired.

VERSION="$1"
TARGET=$(pythonloc "$VERSION")

if [ ! -e "$TARGET/bin/python" ] ; then 
    mkdir -p "$BASE"

    LOCKFILE="$BASE/.install-lockfile"
    while true; do
      if mkdir "$LOCKFILE" 2>/dev/null; then
        echo "Successfully acquired installer."
        break
      else
        echo "Failed to acquire lock. Is another installer running? Waiting a bit."
      fi

      sleep $(( ( RANDOM % 10 ) + 1 )).$(( RANDOM % 100 ))s

      if (( $(date '+%s') > 300 + $(stat --format=%X "$LOCKFILE") )); then
        echo "We've waited long enough"
        rm -rf "$LOCKFILE"
      fi
    done
    trap 'rm -rf $LOCKFILE' EXIT

    # shellcheck disable=SC2072
    if [[ ! "$VERSION" < "3.7" ]] ; then
        if [ ! -e "$OPENSSL_DIR/lib/libssl.a" ] ; then
            rm -rf "$OPENSSL_DIR"
            OPENSSL_BUILD_DIR="$BASE/openssl-builddir"
            pushd "$BASE"
            rm -rf "$OPENSSL_BUILD_DIR"
            mkdir -p "$OPENSSL_BUILD_DIR"
            cd "$OPENSSL_BUILD_DIR"
            curl -O https://www.openssl.org/source/openssl-1.0.2o.tar.gz
            tar -xf openssl-1.0.2o.tar.gz
            cd openssl-1.0.2o
            if [ "$DARWIN" = "true" ] ; then
                ./Configure darwin64-x86_64-cc --openssldir="$OPENSSL_DIR"
            else
                ./config --openssldir="$OPENSSL_DIR" --shared
            fi
            make install
            popd
        fi

        export CFLAGS="-I$OPENSSL_DIR/include"
        export LDFLAGS="-L$OPENSSL_DIR/lib -lssl -lcrypto"
        export CONFIGURE_OPTS="--with-openssl=$OPENSSL_DIR"
    fi

    if [ ! -d "$PYENV/.git" ]; then
      rm -rf "$PYENV"
      git clone https://github.com/yyuu/pyenv.git "$PYENV"
    else
      back=$PWD
      cd "$PYENV"
      git fetch || echo "Update failed to complete. Ignoring"
      git reset --hard origin/master
      cd "$back"
    fi

    "$BASE/pyenv/plugins/python-build/bin/python-build" --verbose "$VERSION" "$TARGET"
fi
