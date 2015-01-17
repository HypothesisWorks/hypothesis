"""A module controlling settings for Hypothesis to use in falsification.

Either an explicit Settings object can be used or the default object on
this module can be modified.

"""
import os


class Settings(object):

    """A settings object controls a variety of parameters that are used in
    falsification. There is a single default settings object that all other
    Settings will use as its values s defaults.

    Not all settings parameters are guaranteed to be stable. However the
    following are:

    max_examples: Once this many examples have been considered without finding
        any counter-example, falsify will terminate
    timeout: Once this amount of time has passed, falsify will terminate even
        if it has not found many examples. This is a soft rather than a hard
        limit - Hypothesis won't e.g. interrupt execution of the called
        function to stop it.
    derandomize: If this is True then hypothesis will run in deterministic mode
        where each falsification uses a random number generator that is seeded
        based on the hypothesis to falsify, which will be consistent across
        multiple runs. This has the advantage that it will eliminate any
        randomness from your tests, which may be preferable for some situations
        . It does have the disadvantage of making your tests less likely to
        find novel breakages.

    """
    # pylint: disable=too-many-arguments

    def __init__(
            self,
            min_satisfying_examples=None,
            max_examples=None,
            max_skipped_examples=None,
            timeout=None,
            derandomize=None,
            database=None,
    ):
        self.min_satisfying_examples = (
            min_satisfying_examples or default.min_satisfying_examples)
        self.max_examples = max_examples or default.max_examples
        self.timeout = timeout or default.timeout
        self.database = database or default.database
        self.max_skipped_examples = (
            max_skipped_examples or default.max_skipped_examples)
        if derandomize is None:
            self.derandomize = default.derandomize
        else:
            self.derandomize = derandomize


default = Settings(
    min_satisfying_examples=5,
    max_examples=200,
    timeout=60,
    max_skipped_examples=50,
    derandomize=False,
    # Silly hack so that we don't have it try to look up a value on itself
    # before it has been assigned.
    database=object(),
)
default.database = None

DATABASE_OVERRIDE = os.getenv('HYPOTHESIS_DATABASE_FILE')

# This is tested outside the main tests which run coverage because it is per
# process
if DATABASE_OVERRIDE:
    from hypothesis.database import ExampleDatabase
    from hypothesis.database.backend import SQLiteBackend
    default.database = ExampleDatabase(
        backend=SQLiteBackend(DATABASE_OVERRIDE)
    )
