import subprocess
import os

HEADER_FILE = "misc/header.py"

HEADER_SOURCE = open(HEADER_FILE).read().strip()


def all_python_files():
    lines = subprocess.check_output([
        "git", "ls-tree", "--full-tree", "-r", "HEAD",
    ]).decode('utf-8').split("\n")
    files = [
        l.split()[-1]
        for l in lines
        if l
    ]
    return [
        f for f in files
        if f[-3:] == ".py"
    ]


def main():
    rootdir = os.path.abspath(os.path.dirname(__file__))
    print("cd %r" % (rootdir,))
    os.chdir(rootdir)
    files = all_python_files()
    files.remove("enforce_header.py")

    for f in files:
        print(f)
        lines = []
        with open(f, encoding="utf-8") as o:
            for l in o.readlines():
                if 'END HEADER' in l:
                    lines = []
                else:
                    lines.append(l)
        source = ''.join(lines).strip()
        with open(f, "w", encoding="utf-8") as o:
            o.write(HEADER_SOURCE)
            o.write("\n\n")
            o.write(source)
            o.write("\n")

if __name__ == '__main__':
    main()
