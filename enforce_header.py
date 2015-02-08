from glob import glob

HEADER_FILE = "src/hypothesis/header.py"

HEADER_SOURCE = open(HEADER_FILE).read().strip()


def main():
    files = (
        glob("src/**/*.py") +
        glob("tests/*.py") +
        glob("tests/**/*.py") +
        glob("hypothesis-extra/*/src/*.py") +
        glob("hypothesis-extra/*/src/**/*.py") +
        glob("hypothesis-extra/*/tests/*.py") +
        glob("hypothesis-extra/*/tests/**/*.py"))

    files.remove(HEADER_FILE)
    for f in files:
        lines = []
        with open(f) as o:
            for l in o.readlines():
                if 'END HEADER' in l:
                    lines = []
                else:
                    lines.append(l)
        source = ''.join(lines).strip()
        with open(f, "w") as o:
            o.write(HEADER_SOURCE)
            o.write("\n\n")
            o.write(source)
            o.write("\n")

if __name__ == '__main__':
    main()
