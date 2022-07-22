RELEASE_TYPE: patch

This patch improves the error message when you pass filenames to the :command:`hypothesis write`
CLI, which takes the name of a module or function (e.g. :command:`hypothesis write gzip` or 
:command:`hypothesis write package.some_function` rather than :command:`hypothesis write script.py`).

Thanks to Ed Rogers for implementing this as part of the SciPy 2022 sprints!