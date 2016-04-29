import subprocess
import os
import sys

HEADER_FILE = "scripts/header.py"

HEADER_SOURCE = open(HEADER_FILE).read().strip()


def all_python_files():
    lines = subprocess.check_output([
        "git", "ls-tree", "--full-tree", "-r", "HEAD",
    ]).decode('utf-8').split("\n")
    files = [
        l.split()[-1]
        for l in lines
        if l and 'hypothesislegacysupport' not in l
    ]
    return [
        f for f in files
        if f[-3:] == ".py"
    ]


def main():
    rootdir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    print("cd %r" % (rootdir,))
    os.chdir(rootdir)
    if len(sys.argv) > 1:
        files = sys.argv[1:]
    else:
        files = all_python_files()
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
            o.write("\n\n")
            o.write(source)
            o.write("\n")

if __name__ == '__main__':
    main()
