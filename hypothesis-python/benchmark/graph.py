# This file is part of Hypothesis, which may be found at
# https://github.com/HypothesisWorks/hypothesis/
#
# Copyright the Hypothesis Authors.
# Individual contributors are listed in AUTHORS.rst and the git log.
#
# This Source Code Form is subject to the terms of the Mozilla Public License,
# v. 2.0. If a copy of the MPL was not distributed with this file, You can
# obtain one at https://mozilla.org/MPL/2.0/.

import json
import math
import statistics
from pathlib import Path

import click


def plot_vega(vega_spec, data, *, to, parameters=None):
    import vl_convert

    parameters = parameters or {}

    spec = json.loads(vega_spec.read_text())
    spec["data"].insert(0, {"name": "source", "values": data})
    if "signals" not in spec:
        spec["signals"] = []

    for key, value in parameters.items():
        spec["signals"].append({"name": key, "value": value})

    with open(to, "wb") as f:
        # default ppi is 72, which is somewhat blurry.
        f.write(vl_convert.vega_to_png(spec, ppi=200))


def _mean_difference_ci(n1, n2, *, confidence):
    from scipy import stats

    var1 = statistics.variance(n1)
    var2 = statistics.variance(n2)
    df = len(n1) + len(n2) - 2
    # this assumes equal variances between the populations of n1 and n2. This
    # is not necessarily true (new might be more consistent than old), but it's
    # good enough.
    pooled_std = math.sqrt(((len(n1) - 1) * var1 + (len(n2) - 1) * var2) / df)
    se = pooled_std * math.sqrt(1 / len(n1) + 1 / len(n2))
    t_crit = stats.t.ppf((1 + confidence) / 2, df)
    return t_crit * se


def _process_benchmark_data(data):
    assert set(data) == {"old", "new"}
    old_calls = data["old"]["calls"]
    new_calls = data["new"]["calls"]
    assert set(old_calls) == set(new_calls), set(old_calls).symmetric_difference(
        set(new_calls)
    )

    graph_data = []

    def _diff_times(old, new):
        if old == 0 and new == 0:
            return 0
        if old == 0:
            # there aren't any great options here, but 0 is more reasonable than inf.
            return 0
        v = (old - new) / old
        if 0 < v < 1:
            v = (1 / (1 - v)) - 1
        return v

    sums = {"old": 0, "new": 0}
    for node_id in old_calls:
        old = old_calls[node_id]
        new = new_calls[node_id]
        if set(old) | set(new) == {0} or len(old) != len(new):
            print(f"skipping {node_id}")
            continue

        sums["old"] += statistics.mean(old)
        sums["new"] += statistics.mean(new)
        diffs = [n_old - n_new for n_old, n_new in zip(old, new)]
        diffs_times = [_diff_times(n_old, n_new) for n_old, n_new in zip(old, new)]
        ci_shrink = (
            _mean_difference_ci(old, new, confidence=0.95) if len(old) > 1 else 0
        )

        graph_data.append(
            {
                "node_id": node_id,
                "absolute": statistics.mean(diffs),
                "absolute_ci_lower": ci_shrink,
                "absolute_ci_upper": ci_shrink,
                "nx": statistics.mean(diffs_times),
                "nx_ci_lower": 0,
                "nx_ci_upper": 0,
            }
        )

    graph_data = sorted(graph_data, key=lambda d: d["absolute"])
    return graph_data, sums


@click.command()
@click.argument("data", type=click.Path(exists=True, path_type=Path))
@click.argument("out", type=click.Path(path_type=Path))
def plot(data, out):
    data = json.loads(data.read_text())
    data, sums = _process_benchmark_data(data)
    plot_vega(
        Path(__file__).parent / "spec.json",
        data=data,
        to=out,
        parameters={
            "title": "Shrinking benchmark (calls)",
            "sum_old": sums["old"],
            "sum_new": sums["new"],
            "absolute_axis_title": ("shrink call change (old - new, larger is good)"),
        },
    )


if __name__ == "__main__":
    plot()
