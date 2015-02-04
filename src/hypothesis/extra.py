import pkg_resources


def load_entry_points():
    for entry_point in pkg_resources.iter_entry_points(
        group='hypothesis.extra'
    ):
        entry_point.load()()  # pragma: no cover
