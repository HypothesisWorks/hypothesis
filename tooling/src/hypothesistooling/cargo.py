# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import re
import subprocess
from pathlib import Path

import tomli

from hypothesistooling import installers as install
from hypothesistooling.git import ROOT

RUST = ROOT / "hypothesis" / "rust"
CARGO_TOML = RUST / "Cargo.toml"

ci_version_rust = "1.96.1"
RUST_BUILD_ENV = {"RUSTUP_TOOLCHAIN": ci_version_rust}


def rust_msrv():
    return tomli.loads(CARGO_TOML.read_text(encoding="utf-8"))["package"][
        "rust-version"
    ]


def cargo(toolchain, args, *, components=(), targets=()):
    install.ensure_rustc(toolchain, components=components, targets=targets)
    subprocess.check_call([install.RUSTUP, "run", toolchain, "cargo", *args], cwd=RUST)


def write_version(cargo_toml_path: Path, new_version: str) -> None:
    content = cargo_toml_path.read_text(encoding="utf-8")
    content = re.sub(
        r'^version = "[^"]*"$',
        f'version = "{new_version}"',
        content,
        count=1,
        flags=re.MULTILINE,
    )
    cargo_toml_path.write_text(content, encoding="utf-8")


def update_lockfile() -> None:
    cargo(rust_msrv(), ["update", "--workspace", "--manifest-path", str(CARGO_TOML)])
