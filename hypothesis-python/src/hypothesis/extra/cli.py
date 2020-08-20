# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Most of this work is copyright (C) 2013-2020 David R. MacIver
# (david@drmaciver.com), but it contains contributions by others. See
# CONTRIBUTING.rst for a full list of people who may hold copyright, and
# consult the git log if you need to determine who owns an individual
# contribution.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.
#
# END HEADER

"""
.. _hypothesis-cli:

----------------
hypothesis[cli]
----------------

This module provides Hypothesis' command-line interface, for e.g.
:doc:`'ghostwriting' tests <ghostwriter>` via the terminal.
It requires the :pypi:`click` package.

Run :command:`hypothesis --help` in your terminal for details.
"""

import builtins
import importlib
import sys
from difflib import get_close_matches

from hypothesis.extra import ghostwriter

try:
    import click
except ImportError:

    def main():
        """If `click` is not installed, tell the user to install it then exit."""
        sys.stderr.write(
            """
The Hypothesis command-line interface requires the `click` package,
which you do not have installed.  Run:

    python -m pip install --upgrade hypothesis[cli]

and try again.
"""
        )
        sys.exit(1)


else:
    # Ensure that Python scripts in the current working directory are importable,
    # on the principle that Ghostwriter should 'just work' for novice users.  Note
    # that we append rather than prepend to the module search path, so this will
    # never shadow the stdlib or installed packages.
    sys.path.append(".")

    @click.group(context_settings={"help_option_names": ("-h", "--help")})
    @click.version_option()
    def main():
        pass

    def obj_name(s: str) -> object:
        """This "type" imports whatever object is named by a dotted string."""
        try:
            return importlib.import_module(s)
        except ImportError:
            pass
        if "." not in s:
            modulename, module, funcname = "builtins", builtins, s
        else:
            modulename, funcname = s.rsplit(".", 1)
            try:
                module = importlib.import_module(modulename)
            except ImportError:
                raise click.UsageError(
                    f"Failed to import the {modulename} module for introspection.  "
                    "Check spelling and your Python import path, or use the Python API?"
                )
        try:
            return getattr(module, funcname)
        except AttributeError:
            public_names = [name for name in vars(module) if not name.startswith("_")]
            matches = get_close_matches(funcname, public_names)
            raise click.UsageError(
                f"Found the {modulename!r} module, but it doesn't have a "
                f"{funcname!r} attribute."
                + (f"  Closest matches: {matches!r}" if matches else "")
            )

    @main.command()  # type: ignore  # Click adds the .command attribute
    @click.argument("func", type=obj_name, required=True, nargs=-1)
    @click.option("--idempotent", "writer", flag_value="idempotent")
    @click.option("--binary-op", "writer", flag_value="binary_operation")
    @click.option("--equivalent", "writer", flag_value="equivalent")
    @click.option("--roundtrip", "writer", flag_value="roundtrip")
    # Note: we deliberately omit a --ufunc flag, because the magic()
    # detection of ufuncs is both precise and complete.
    @click.option(
        "--style",
        type=click.Choice(["pytest", "unittest"]),
        default="pytest",
        help="pytest-style function, or unittest-style method?",
    )
    @click.option(
        "-e",
        "--except",
        "except_",
        type=obj_name,
        multiple=True,
        help="dotted name of exception(s) to ignore",
    )
    def write(func, writer, except_, style):  # noqa: D301  # \b disables autowrap
        """`hypothesis write` writes property-based tests for you!

        Type annotations are helpful but not required for our advanced introspection
        and templating logic.  Try running the examples below to see how it works:

        \b
            hypothesis write gzip
            hypothesis write re.compile --except re.error
            hypothesis write --style=unittest --idempotent sorted
            hypothesis write --binary-op operator.add
            hypothesis write --equivalent ast.literal_eval eval
            hypothesis write --roundtrip json.dumps json.loads
        """
        # NOTE: if you want to call this function from Python, look instead at the
        # ``hypothesis.extra.ghostwriter`` module.  Click-decorated functions have
        # a different calling convention, and raise SystemExit instead of returning.
        if writer is None:
            writer = "magic"
        elif writer == "idempotent" and len(func) > 1:
            raise click.UsageError("Test functions for idempotence one at a time.")
        elif writer == "roundtrip" and len(func) == 1:
            writer = "idempotent"
        elif writer == "equivalent" and len(func) == 1:
            writer = "fuzz"

        print(getattr(ghostwriter, writer)(*func, except_=except_ or (), style=style))
