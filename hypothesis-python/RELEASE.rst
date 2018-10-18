RELEASE_TYPE: minor

This release adds a CLI flag for verbosity ``--hypothesis-verbosity`` to
the Hypothesis pytest plugin, applied after loading the profile specified by
``--hypothesis-profile``. Valid options are the names of verbosity settings,
quiet, normal, verbose or debug.

Thanks to Bex Dunn for writing this patch at the PyCon Australia
sprints!

The pytest header now correctly reports the current profile if
``--hypothesis-profile`` has been used.

Thanks to Mathieu Paturel for the contribution at the Canberra Python
Hacktoberfest.

