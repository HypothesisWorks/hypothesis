import pkg_resources

entry_points_loaded = False


def load_entry_points():
    global entry_points_loaded
    if entry_points_loaded:
        return
    entry_points_loaded = True
    for entry_point in pkg_resources.iter_entry_points(
        group='hypothesis.extra'
    ):
        entry_point.load()()
