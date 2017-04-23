# We run this script as a system check to see if a version of Python is
# adequate for our purposes.

import sys

# We need virtualenv and pip to be installed so we import them here as a check
import virtualenv  # noqa
import pip  # noqa


if __name__ == '__main__':
    version = sys.version_info[:2]
    if version < (2, 7):
        sys.exit(1)
    elif (3, 0) <= version <= (3, 3):
        sys.exit(1)
    else:
        sys.exit(0)
