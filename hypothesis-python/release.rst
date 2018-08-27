RELEASE_TYPE: minor

This release adds a CLI flag for verbosity `--hypothesis-verbosity` to `hypothesis.extra.pytestplugin`,
applied after loading the profile specified by `--hypothesis-profile`

available options for verbosity are:
quiet = 0
normal = 1
verbose = 2
debug = 3

Thanks to Bex Dunn (@BexDunn) for writing this patch at the PyCon Australia sprints!
