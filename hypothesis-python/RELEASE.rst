RELEASE_TYPE: patch

use str for struct module function calls because the struct module is
documented as accepting only "format strings" and happens to implement
"format bytes", which can cause Warnings when run with `python -bb`
in some cases

see https://docs.python.org/3/library/struct.html#struct-format-strings
and https://bugs.python.org/issue41777
and https://github.com/pytest-dev/pytest-xdist/issues/596
and https://bugs.python.org/issue21071#msg292409
