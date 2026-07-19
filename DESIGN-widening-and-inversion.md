# Design: value-widening shrinks, and a path to general strategy inversion

Working document for a PR that combines the strictly-necessary parts of
[#4713](https://github.com/HypothesisWorks/hypothesis/pull/4713) (allow shrinking of
generated values into wider strategies) and
[#4743](https://github.com/HypothesisWorks/hypothesis/pull/4743) (internal
`SearchStrategy._invert`). This file is the deliverable for now; it will be deleted
once we agree on the design and replace it with code.

## 1. Goals and non-goals

**Goal (the feature).** When a user writes `wide | specific` — e.g.
`st.text() | some_grammar_strategy`, `st.integers() | st.sampled_from([...])` — and
the failing value comes from the `specific` branch, the shrinker should be able to
slip that value across into the `wide` branch and shrink it as an arbitrary member of
the wider space. This was #4713's motivating case ("you might want to not crash on
arbitrary bytes, but the interesting space corresponds to some grammar").

**Accepted limitation: `just()` does not slide.** We deliberately give up
`text() | just("...")`-style widening. A `just` span contains zero choices, so any
wide-branch encoding of its value makes the choice sequence *longer*, which the
shrinker's monotone ordering rejects (§3). #4713 solved this by inserting artificial
forced choice nodes into `just`/`sampled_from` spans — and that single mechanism was
the source of nearly all of that PR's complexity and compatibility surface (§4.5).
Accepting the limitation deletes the mechanism. The loss is small: a `just` value is a
constant the user wrote explicitly, so "it didn't shrink further" is far less
surprising there than for a grammar-generated blob — and §6 sketches two additive ways
to recover `just`-sliding later. Notably, `sampled_from` still slides *without* any
insertion (§3), so the limitation really is just `just`.

**Goal (the architecture).** Build the feature out of pieces that are each a small,
named step toward general inversion (`value → choice sequence`), so that later work —
non-primitive widening, "paste an externally-reported failure into `@example(...)` and
we'll shrink it", solver-assisted inversion of `.filter`/`.map` — is additive rather
than a rewrite.

**Non-goals for the first PR.**

- No generation-side behavior changes at all: no strategy draws differently, no choice
  sequence changes shape. The PR is span *metadata* plus a shrink pass.
- No `SearchStrategy._invert` method lands yet. It has no call site in the minimal
  feature, and we've agreed not to write code that isn't immediately useful. #4743
  (rebased and trimmed per its review) becomes the *second* PR, landing together with
  its first real consumer (§6).
- No inversion of non-primitive values, no `map`/`filter` inversion, no solver anything.
- No unification of the explain-phase bookkeeping (`arg_slices`/`slice_comments`) with
  spans in this PR — but we design the new span annotation so that unification is a
  mechanical follow-up (§5).

## 2. Background: the machinery we're touching

*Choice sequence & spans.* Every strategy draw appends `ChoiceNode`s (five primitive
types: `integer`, `float`, `boolean`, `string`, `bytes`) and opens/closes a `Span` — a
labelled `[start, end)` region of the choice sequence, stored compactly in
`SpanRecord`/`Spans` and materialized lazily after the test case completes. The
shrinker works purely on `(nodes, spans)`; **it has no access to strategy objects**.
Its acceptance criterion is strict: a proposal is taken only if
`sort_key(new) < sort_key(old)`, where
`sort_key = (len(nodes), tuple(choice_to_index(...)))` — shorter wins, then
lexicographically-earlier-and-lower wins.

*Explain phase / pretty-printer.* `BuildContext.track_arg_label` records a
`(start_node, end_node)` slice per top-level argument into `data.arg_slices`;
the shrinker's explain phase re-runs the test varying each slice and writes
`data.slice_comments[(start, end)] = "or any other generated value"`-style notes; the
pretty-printer (`RepresentationPrinter.repr_call`) looks comments up by slice.
Separately, `BuildContext.record_call` registers id-keyed printers so objects built by
`builds`/`map` repr as calls. This is the "spans and objects for the explain-phase
pretty-printer" machinery — note that `arg_slices` entries are exactly the boundaries
of the corresponding top-level spans, computed by hand because `BuildContext` runs
before spans are materialized.

*What #4713 does*, in five separable pieces:

1. **Span value recording** — `ConjectureData.draw` records the drawn value on the
   just-closed span, iff it is one of the five primitive Python types.
2. **Choice-node insertion for `just`/`sampled_from`** — append a *forced* choice node
   holding the drawn value (or a forced `False` boolean for non-primitive values), so
   those spans aren't "artificially simpler" than their values and widening can be a
   length-neutral replacement.
3. **A widening shrink pass** — find an integer node with `min_value == 0` and value
   `!= 0` (heuristically: a `one_of` branch selector) immediately followed by a span
   with a recorded value; propose replacing the selector with `0` and the span's
   choices with a single maximally-permissive node holding the recorded value. Replay
   against the earlier branch does the interpretation: if the branch's constraints
   permit the value, it's consumed as-is; if not, the attempt just fails harmlessly.
4. **`one_of` rewrite** — because piece 2 inserts a forced boolean for *every*
   `sampled_from` draw, and `one_of` internally uses `sampled_from(strategies)`,
   piece 2 regressed `one_of`; the rewrite makes it draw its index directly (plus new
   retry/fallback logic for empty branches).
5. **Explain-phase fix** — skip slices whose nodes are all forced (nothing can vary,
   so the "or any other generated value" comment would be false). Needed because
   piece 2 makes `just(5)` as a top-level argument an all-forced slice.

*What #4743 does:* adds internal `_invert(value) -> tuple[ChoiceT, ...]` ("return
choices that replay to this value, best-effort") to ~20 strategies, a
`CannotInvert`/`CannotInvertYet`/`DefinitelyCannotInvert` exception hierarchy,
NaN-aware `deep_equal`, and an `invert_many` mirror of `cu.many`. Explicitly
infrastructure-only: nothing calls it.

## 3. The unifying model

The two PRs are the two directions of the same arrow:

- **Spans decode:** a span maps a region of the choice sequence to the value it
  produced. #4713's span value recording makes the decode direction *queryable after
  the fact*.
- **`_invert` encodes:** it maps a value back to a choice-sequence region that would
  reproduce it under a given strategy.

The widening feature is `encode(wide_strategy, decode(specific_span))` followed by a
standard shrink experiment. The minimal PR implements the encode direction only for
the *universal strategy of each primitive type* — "any int", "any string", … — which
needs no strategy object at all: it's a single choice node with maximally-permissive
constraints (#4713's `_choice_node_for_value`). That is real inversion, just for the
five easiest strategies in the library, and it is all the feature needs, because
replay-time constraint checking specializes the universal encoding to whatever the
wide branch actually accepts.

**Which branches can slide is decided by arithmetic, not policy.** The universal
encoding always costs exactly one node, and the pass also lowers the `one_of` selector
(an earlier position in the sequence). Under the shrinker's sort key:

| specific branch's span | widened sequence | verdict |
| --- | --- | --- |
| ≥ 2 nodes (grammar, `builds`, any compound) | strictly shorter | accepted |
| exactly 1 node (`sampled_from`'s index draw) | equal length, selector strictly lower ⇒ lexicographically smaller | accepted |
| 0 nodes (`just`) | one node longer | **rejected** |

#4713's node insertion existed to move `just` (and, uniformly, `sampled_from`) out of
the bottom rows by pre-paying the node cost at generation time. Accepting that `just`
doesn't slide means we never touch generation at all — and the table shows
`sampled_from` and every compound branch slide anyway. (That `sampled_from` needs no
insertion is a prediction from the sort key, not something #4713 demonstrated — it
must be verified empirically first, §8 Q1.)

Two invariants make this design safe to evolve, and every phase must preserve them:

1. **Inversion is best-effort; replay verifies.** Any consumer of an encoding runs it
   through the normal draw path and checks the outcome (shrinker: sort-key check, then
   the failure predicate; future `@example` paste: value equality). A wrong encoding
   is a wasted attempt, never corruption. This is why `_invert`'s contract in #4743
   already says "we expect, with high probability" rather than "guaranteed".
2. **Span annotations are sparse and optional.** `span_index -> annotation` maps
   default to "nothing recorded"; new annotation kinds (objects, strategy references)
   are additive and cost nothing when unused.

## 4. The minimal PR: two orthogonal additions

### 4.1 Span value recording (#4713 piece 1), with one framing change

`SpanRecord` gains an open-span stack and a sparse `dict[int, Any]` of recorded
values; `ConjectureData.draw` records the value returned by `do_draw` against the
just-closed span when `type(value)` is one of the five primitive types (exact type
check, tuple membership — this also conveniently never records symbolic values from
alternative backends, whose types differ from the builtins, so we never pin or realize
them). `Span` exposes it as a property returning `None` when absent.

Recording at the `ConjectureData.draw` level — not inside individual strategies — is
load-bearing: it's what lets `text() | st.builds(make_str, ...)` widen, because the
*compound* branch's span records the final `str` it produced. (#4713's
`test_widen_text_with_builds` covers this.)

Naming: propose `Span.recorded_value` / `SpanRecord.record_value_for_span(value)`,
dropping "primitive" from the name. The *policy* (primitives only, for now) shouldn't
be baked into the *mechanism's* name, since §6 relaxes the policy but keeps the
mechanism. Bikeshed freely.

### 4.2 The widening shrink pass (#4713 piece 3), reframed as primitive inversion

Port `widen_to_span_with_generated_primitive_value` and its node-synthesis helper
essentially as-is (master already has `spans_starting_at`; the port is mechanical).
Three presentational changes:

- Name and place the helper as what it is: inversion under the universal strategy of a
  primitive type. Suggest `choice_node_for_primitive(value)` next to the pass in
  `shrinker.py` (moving to `choice.py` if/when a second caller appears). Its docstring
  should state the §3 framing — this is the function that `_invert` generalizes — so
  the future direction is legible in the code.
- Keep the trigger heuristic (`integer node, min_value == 0, value != 0, followed by a
  value-carrying span`). With no `one_of` rewrite, the selector node is the index
  drawn by `one_of`'s internal `sampled_from` — the node layout
  `[selector][branch span...]` is exactly what the pass expects. False positives (any
  zero-based integer draw) cost one sort-key comparison; chooser passes tolerate that
  by construction.
- Optionally pre-filter candidate spans on `choice_count > 0`: zero-node (`just`)
  spans are known-futile (§3), so skip them rather than synthesizing a
  guaranteed-rejected proposal. Purely cosmetic — the sort-key check already rejects
  them before any test execution.

### 4.3 Tests and release note

- The `tests/quality/test_widening_shrinks.py` suite from #4713, with the
  `just`-branch cases converted to `sampled_from`/compound equivalents (they're now
  the feature's spec), and one or two added grammar-ish composite cases, since
  "grammar strategy sliding into `binary()`/`text()`" is the headline motivation.
- Unit tests for span recording, adapted from #4713's `test_test_data.py` additions.
- A regression test pinning the accepted limitation: `wide | just(v)` does *not*
  slide, and generation behavior of `just`/`sampled_from`/`one_of` is byte-for-byte
  unchanged (e.g. `just` still draws nothing — #4713 deleted
  `test_just_strategy_does_not_draw`; we keep it).
- RELEASE.rst: patch. Reword #4713's note, which promised `just`-sliding.

### 4.4 What this PR deliberately does not contain

| Piece | From | Why dropped |
| --- | --- | --- |
| Forced-node insertion in `just`/`sampled_from` | #4713 | Only needed for `just`-sliding, which we've accepted losing; sole source of all generation-side churn (§4.5) |
| `one_of` rewrite + empty-branch retry logic | #4713 | Only needed to dodge insertion's forced-`False` in `sampled_from(strategies)` |
| Explain-phase all-forced-slice skip | #4713 | Only needed once insertion creates all-forced slices. (It's *also* a latent fix for rare all-forced slices on master, e.g. `sampled_from`'s exhaustive-fallback forced index — worth a tiny standalone PR, but not this one) |
| `test_stateful.py` / `reproduce_failure` blob churn | #4713 | Consequence of insertion; vanishes with it |
| `SearchStrategy._invert` + per-strategy impls | #4743 | No call site yet; lands as PR 2 with its first consumer (§6) |
| Exception hierarchy, `deep_equal`, `invert_many` | #4743 | Only used by `_invert`; move with it |

### 4.5 What accepting the `just` limitation bought

For the record, since this is the design's key trade: insertion was the only
generation-side behavior change in #4713, and it transitively caused *all* of the
following, none of which exist in this design:

- the `one_of` regression and rewrite (new draw shape, retry logic, distribution
  change, extra events);
- invalidation of stored database entries and `@reproduce_failure` blobs for every
  test using `just`/`sampled_from` (forced draws consume from the replay prefix, so
  extra forced nodes shift alignment);
- distribution shifts in downstream suites (the pandas-overflow flake #4713 hit);
- losing `just`/`none`'s documented "never touches the choice sequence" property;
- forced-node size counting against the length budget for large sampled values;
- the "primitives-only insertion is ugly/unprincipled" design argument — mooted,
  there is no insertion policy to argue about.

## 5. Code sharing with the explain-phase / pretty-printer tracking

Short answer: a little now, real convergence in a designated follow-up, and the new
mechanism is deliberately the *substrate* the old ones migrate onto — not a third
parallel system.

There are currently three "which region/object came from where" bookkeepers:

1. `data.arg_slices` + `data.slice_comments` — node-index slices, per top-level
   argument, keyed by `(start, end)` tuples across `BuildContext`, the shrinker's
   explain phase, and the pretty-printer.
2. `known_object_printers` — id-keyed object→call reprs from `record_call`
   (`builds`/`map`), final-replay only.
3. (new) span recorded values — `span_index -> value`.

(1) is spans re-derived by hand: `track_arg_label` measures `len(data.nodes)` before
and after a draw precisely because spans aren't materialized until after the test
completes. The open-span stack added in §4.1 removes that limitation at the recording
level: `SpanRecord` now knows the current span index *during* the run.

**Follow-up refactor (separate PR, before or with §6's PR 4):** key the explain-phase
data by span index instead of node slices — `track_arg_label` marks "current span is
reportable argument *k*", `arg_slices` becomes derived data, `slice_comments` becomes
`dict[span_index, str]`, and the pretty-printer resolves span→slice at print time.
This deletes the manual index arithmetic, gives the explain phase span metadata for
free (it currently can't tell a discarded region from a real one), and means the
widening pass, the explain phase, and the printer all read from one annotation store.
It is pure churn from the user's perspective, which is why it is *not* in the minimal
PR.

(2) stays as-is. It plausibly becomes a span annotation too ("span → constructed
object + call info"), but it's final-replay-only by design (arbitrary user objects
must not be pinned in cached `ConjectureResult`s), and unifying lifetimes buys little
today. Revisit when §6's PR 3/4 forces us to answer the object-lifetime question
anyway.

## 6. Evolution path: where inversion goes next

Each phase is additive over the previous; none reworks a prior phase's interfaces.

**PR 2 — `_invert` core, with a consumer.** #4743 rebased, trimmed to the strategies
its consumer exercises, plus the review threads (add_note breadcrumb trail for
debuggability, strict-type-check unification, `LimitedStrategy`/`SharedStrategy`
raising `CannotInvertYet`). The recommended first consumer is the **generation-side**
one, because strategies are in hand there and the shrinker needs no changes:
*reproduce-and-shrink-from-value* — internally, `_invert` the pasted/`@example` value
to a choice sequence, seed the engine with it, and let normal shrinking (including the
new widening pass) take over. This is the "paste an externally-reported failure"
feature, and it exercises `_invert` end-to-end through `ConjectureData.for_choices`
replay, which is exactly the verification loop invariant 1 requires. At this point
`choice_node_for_primitive` gets a docstring cross-reference (or becomes a helper
shared with `FloatStrategy._invert` etc., if that falls out naturally — not forced).

**PR 3 — recovering `just()`-sliding, if we still want it.** Two additive options,
in increasing order of power:

- *(a) Reinstate insertion, scoped to `JustStrategy` + primitive values only.* A
  one-method change once this PR's machinery exists; `sampled_from` never needs it
  (§3), so `one_of` internals are unaffected and the compat surface is limited to
  `just(<primitive>)` users. This is #4713's mechanism at its minimum viable scope.
- *(b) A post-shrink slide experiment, outside the monotone ordering.* The explain
  phase already demonstrates the pattern: after shrinking stabilizes, run experiments
  that are *not* sort-key decreasing, under an explicit termination guard. A slide
  experiment ("re-encode span under earlier branch, then re-shrink") terminates
  because the branch selector strictly decreases each time. This handles `just`
  without ever touching generation, and is the natural home for *non-primitive*
  cross-branch movement too — which makes it likely we want (b) eventually
  regardless, and (a) only if users ask before then.

**PR 4 — cross-branch inversion in the shrinker (the hard one).** Widening
non-primitive values into non-universal wide branches requires strategy access at
shrink time, which the shrinker architecturally lacks — this is the "very intrusive
reworking" concern from #4713's thread. Two candidate designs, both compatible with
the span annotation store, decision explicitly deferred:

- *(i) record `(strategy_ref, value)` on spans during generation.* Simple for the
  shrinker, but pins strategies and user objects in every cached `ConjectureResult`;
  needs a lifetime policy (weakrefs, or record only on interesting results).
- *(ii) invert-on-replay:* the shrinker attaches guidance to the next test-case run
  ("at span *i*, branch *j*: try `_invert`ing this value first"), and `one_of.do_draw`
  performs the inversion inline, where strategies naturally live. No new lifetimes;
  more plumbing between shrinker and engine. Composes with PR 3(b)'s experiment loop.

**Later — smarter encoders.** `.map` inversion via a registry of known inverses
(`"".join`, dataclass constructors, `operator.neg`, …), `.filter` via
check-and-delegate (already in #4743), search/solver-assisted inversion for opaque
predicates. All of these are internal upgrades behind the same
`value → choices, raising CannotInvert` contract, invisible to every caller.

Nothing in phases 2+ requires revisiting the minimal PR: the span store already
accepts `Any`, the widening pass already treats encodings as fallible experiments, and
generation-side behavior was never changed, so there's nothing to un-change.

## 7. Risks

- **The `sampled_from`-slides-without-insertion prediction (§3) could be wrong.**
  It follows directly from the sort key, but #4713 only demonstrated widening *with*
  insertion. Verify with a quick prototype before committing to this design; the
  fallback position (only compound branches slide in PR 1) is still coherent and
  still covers the original grammar motivation, but weakens the feature.
- **Shrinker time**: the pass is chooser-gated and precondition-heavy
  (`min_value == 0`, non-forced, value ≠ 0, following span has a recorded value), so
  it's near-free when irrelevant — #4713's claim, which its narrow trigger justifies.
- **Memory**: recorded values are references to primitives that are (for multi-node
  spans) largely already alive elsewhere; the sparse dict is per-result. `sampled_from`
  over large strings is the one case where the recorded value is *not* otherwise in
  the choice sequence — still just a reference to the user's own constant. Negligible.
- **Compatibility**: none. No choice sequence changes shape; databases and
  `@reproduce_failure` blobs are untouched. (This line is the point of the design.)

## 8. Open questions for review

1. **Empirical check before anything else**: prototype the pass on master and confirm
   `integers() | sampled_from([4991, ...])` and the `builds` compound case slide
   without insertion, per the §3 table. If yes, the design stands as written.
2. Is losing `wide | just(v)` sliding acceptable? (This design says yes, with §6
   PR 3 as the recovery path. #4713's quality tests featured it heavily, so this
   needs explicit sign-off rather than silent dropping.)
3. Naming: `Span.recorded_value` vs `generated_primitive_value`;
   `choice_node_for_primitive` vs `_choice_node_for_value`.
4. First `_invert` consumer for PR 2: reproduce-and-shrink-from-value as recommended,
   or something smaller?
5. Should the §5 span-keyed explain-phase refactor land *before* PR 2 (cleaner
   substrate first) or lazily before PR 4 (only when forced)? Recommendation: lazily —
   it's churn with no user-visible payoff until then.
