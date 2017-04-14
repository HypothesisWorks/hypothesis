from datetime import datetime
import os
import sys

HEADER_FILE = "scripts/header.py"

CURRENT_YEAR = datetime.utcnow().year

HEADER_SOURCE = open(HEADER_FILE).read().strip().format(year=CURRENT_YEAR)


def main():
    rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    os.chdir(rootdir)
    files = sys.argv[1:]
    try:
        files.remove("scripts/enforce_header.py")
    except ValueError:
        pass

    for f in files:
        print(f)
        lines = []
        with open(f, encoding="utf-8") as o:
            shebang = None
            first = True
            for l in o.readlines():
                if first:
                    first = False
                    if l[:2] == '#!':
                        shebang = l
                        continue
                if 'END HEADER' in l:
                    lines = []
                else:
                    lines.append(l)
        source = ''.join(lines).strip()
        with open(f, "w", encoding="utf-8") as o:
            if shebang is not None:
                o.write(shebang)
                o.write("\n")
            o.write(HEADER_SOURCE)
            if source:
                o.write("\n\n")
                o.write(source)
            o.write("\n")


if __name__ == '__main__':
    main()
