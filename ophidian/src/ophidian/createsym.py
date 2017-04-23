import sys
import os
import glob


def fixpath(p):
    p = os.path.abspath(p)
    if '*' in p:
        parts = glob.glob(p)
        if len(parts) != 1:
            print("Ambiguous path", p, file=sys.stderr)
            sys.exit(1)
        p = parts[0]
    return p


if __name__ == '__main__':
    _, source, target = sys.argv
    try:
        os.symlink(
            fixpath(source), fixpath(target)
        )
    except FileExistsError:
        pass
