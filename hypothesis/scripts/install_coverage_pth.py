import pathlib
import sysconfig

# See https://coverage.readthedocs.io/en/latest/subprocess.html for details

pathlib.Path(sysconfig.get_path("purelib"), "coverage_subprocess.pth").write_text(
    "import coverage; coverage.process_startup()\n", encoding="utf-8"
)
