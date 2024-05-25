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
import statistics
from pathlib import Path

import matplotlib.pyplot as plt
import seaborn as sns

data_path = Path(__file__).parent / "data.json"
with open(data_path) as f:
    data = json.loads(f.read())

old_runs = data["old"]
new_runs = data["new"]
all_runs = old_runs + new_runs

# every run should involve the same functions
names = set()
for run in all_runs:
    names.add(frozenset(run.keys()))

intersection = frozenset.intersection(*names)
diff = frozenset.union(*[intersection.symmetric_difference(n) for n in names])

print(f"skipping these tests which were not present in all runs: {', '.join(diff)}")
names = list(intersection)

# the similar invariant for number of minimal calls per run is not true: functions
# may make a variable number of minimal() calls.
# it would be nice to compare identically just the ones which don't vary, to get
# a very fine grained comparison instead of averaging.
# sizes = []
# for run in all_runs:
#     sizes.append(tuple(len(value) for value in run.values()))
# assert len(set(sizes)) == 1

new_names = []
for name in names:
    if all(all(x == 0 for x in run[name]) for run in all_runs):
        print(f"no shrinks for {name}, skipping")
        continue
    new_names.append(name)
names = new_names


# name : average calls
old_values = {}
new_values = {}
for name in names:

    # mean across the different minimal() calls in a single test function, then
    # median across the n iterations we ran that for to reduce error
    old_vals = [statistics.mean(run[name]) for run in old_runs]
    new_vals = [statistics.mean(run[name]) for run in new_runs]
    old_values[name] = statistics.median(old_vals)
    new_values[name] = statistics.median(new_vals)

# name : (absolute difference, times difference)
diffs = {}
for name in names:
    old = old_values[name]
    new = new_values[name]
    diff = old - new
    diff_times = (old - new) / old
    if 0 < diff_times < 1:
        diff_times = (1 / (1 - diff_times)) - 1
    diffs[name] = (diff, diff_times)

    print(f"{name} {int(diff)} ({int(old)} -> {int(new)}, {round(diff_times, 1)}✕)")

diffs = dict(sorted(diffs.items(), key=lambda kv: kv[1][0]))
diffs_value = [v[0] for v in diffs.values()]
diffs_percentage = [v[1] for v in diffs.values()]

print(
    f"mean: {int(statistics.mean(diffs_value))}, median: {int(statistics.median(diffs_value))}"
)


# https://stackoverflow.com/a/65824524
def align_axes(ax1, ax2):
    ax1_ylims = ax1.axes.get_ylim()
    ax1_yratio = ax1_ylims[0] / ax1_ylims[1]

    ax2_ylims = ax2.axes.get_ylim()
    ax2_yratio = ax2_ylims[0] / ax2_ylims[1]

    if ax1_yratio < ax2_yratio:
        ax2.set_ylim(bottom=ax2_ylims[1] * ax1_yratio)
    else:
        ax1.set_ylim(bottom=ax1_ylims[1] * ax2_yratio)


ax1 = sns.barplot(diffs_value, color="b", alpha=0.7, label="shrink call change")
ax2 = plt.twinx()
sns.barplot(diffs_percentage, color="r", alpha=0.7, label=r"n✕ change", ax=ax2)

ax1.set_title("old shrinks - new shrinks (aka shrinks saved, higher is better)")
ax1.set_xticks([])
align_axes(ax1, ax2)
legend = ax1.legend(labels=["shrink call change", "n✕ change"])
legend.legend_handles[0].set_color("b")
legend.legend_handles[1].set_color("r")

plt.show()
