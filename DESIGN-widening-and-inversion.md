# Design: value-widening shrinks, and a path to general strategy inversion

Working document for a PR that combines the strictly-necessary parts of
[#4713](https://github.com/HypothesisWorks/hypothesis/pull/4713) (allow shrinking of
generated values into wider strategies) and
[#4743](https://github.com/HypothesisWorks/hypothesis/pull/4743) (internal
`SearchStrategy._invert`). This file is the deliverable for now; it will be deleted
once we agree on the design and replace it with code.

## 1. Goals and non-goals

**Goal (the feature).** When a user writes `wide | specific` — e.g.
`st.text() | some_grammar_strategy`, `st.integers() | st.just(5000)` — and the failing
value comes from the `specific` branch, the shrinker should be able to slip that value
across into the `wide` branch and shrink it as an arbitrary member of the wider space.
This is #4713's user-visible improvement, unchanged.

**Goal (the architecture).** Build the feature out of pieces that are each a small,
named step toward general inversion (`value → choice sequence`), so that later work —
non-primitive widening, "paste an externally-reported failure into `@example(...)` and
we'll shrink it", solver-assisted inversion of `.filter`/`.map` — is additive rather
than a rewrite.

**Non-goals for the first PR.**

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
2. **Choice-node insertion for `just`/`sampled_from`** — these strategies draw zero
   (`just`) or one index (`sampled_from`) choices, so their spans encode the value
   poorly. #4713 makes them append a *forced* choice node holding the value (or a
   forced `False` boolean for non-primitive values).
3. **A widening shrink pass** — find an integer node with `min_value == 0` and value
   `!= 0` (heuristically: a `one_of` branch selector) immediately followed by a span
   with a recorded value; propose replacing the selector with `0` and the span's
   choices with a single maximally-permissive node holding the recorded value. Replay
   against the earlier branch does the interpretation: if the branch's constraints
   permit the value, it's consumed as-is; if not, the attempt just fails harmlessly.
4. **`one_of` rewrite** — because piece 2 as written inserts a forced boolean for
   *every* `sampled_from` draw, and `one_of` internally uses
   `sampled_from(strategies)`, piece 2 regressed `one_of`; the rewrite makes `one_of`
   draw its index directly (plus new retry/fallback logic for empty branches).
5. **Explain-phase fix** — skip slices whose nodes are all forced (nothing can vary,
   so the "or any other generated value" comment would be false).

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

Everything in §6 is "make encode smarter": per-strategy `_invert` (multi-node
encodings, non-primitives), then consumers that have strategy objects in hand.

Two invariants make this safe to evolve, and every phase must preserve them:

1. **Inversion is best-effort; replay verifies.** Any consumer of an encoding runs it
   through the normal draw path and checks the outcome (shrinker: the failure
   predicate; future `@example` paste: value equality). A wrong encoding is a wasted
   attempt, never corruption. This is why `_invert`'s contract in #4743 already says
   "we expect, with high probability" rather than "guaranteed".
2. **Span annotations are sparse and optional.** `span_index -> annotation` maps
   default to "nothing recorded"; new annotation kinds (objects, strategy references)
   are additive and cost nothing when unused.

## 4. The minimal PR, piece by piece

### 4.1 Keep: span value recording (#4713 piece 1), with one framing change

`SpanRecord` gains an open-span stack and a sparse `dict[int, Any]` of recorded
values; `ConjectureData.draw` records the value returned by `do_draw` against the
just-closed span when `type(value)` is one of the five primitive types (exact type
check, tuple membership — this also conveniently never records symbolic values from
alternative backends, whose types differ from the builtins, so we never pin or realize
them). `Span` exposes it as a property returning `None` when absent.

Recording at the `ConjectureData.draw` level — not inside `just`/`sampled_from` — is
load-bearing: it's what lets `text() | st.builds(make_str, ...)` widen, because the
*compound* branch's span records the final `str` it produced. (#4713's
`test_widen_text_with_builds` covers this.)

Naming: propose `Span.recorded_value` / `SpanRecord.record_value_for_span(value)`,
dropping "primitive" from the public-ish name. The *policy* (primitives only, for now)
shouldn't be baked into the *mechanism's* name, since §6 relaxes the policy but keeps
the mechanism. Bikeshed freely.

### 4.2 Keep, narrowed: choice-node insertion for `just`/`sampled_from` — primitives only

`SampledFromStrategy.do_draw` (which `just` inherits) appends a forced choice node
holding the drawn value **iff the value is primitive**, via a
`ConjectureData.add_choice_node_for(value)` helper that is a no-op for non-primitive
values — dropping #4713's forced-`False` fallback.

Why insertion at all: `consider_new_nodes` only accepts sort-key-*smaller* sequences.
Without insertion, `just("xyzzy-plover")`'s span contributes zero nodes, so any
widened encoding (one string node) is strictly longer than what it replaces and is
rejected. The forced node makes the specific branch's encoding cost what the wide
branch's would, so widening becomes lowering the branch index — a genuine shrink. The
insertion and the widening pass are a matched pair.

Why primitives only, when #4713 inserted for everything and Zac's review called
primitives-only "ugly and unprincipled"? The principled statement we're actually
after is: *a span's choices should encode its value at least as richly as the widest
strategy for the value's type could* — that's exactly what makes cross-branch movement
possible. For non-primitive values there is no such single-node encoding, and a forced
`False` boolean carries no information toward it; it's a placeholder that would be
replaced by real multi-node encodings when `_invert` lands (§6.3), i.e. churn twice.
Meanwhile the placeholder was the *sole* cause of three costs in #4713:

- the `one_of` regression (its internal `sampled_from(strategies)` samples
  non-primitives), which forced piece 4, the `one_of` rewrite — **dropped entirely**
  under this design, including its new empty-branch retry/fallback logic and
  distribution changes;
- most of the choice-sequence churn: stateful tests' `reproduce_failure` blobs
  changed, and the pandas argument-validation flake appeared, because *every*
  `just`/`sampled_from` in existence gained a node. Under primitives-only, only
  `just`/`sampled_from` over primitive values change shape;
- `st.none()` / `just(<sentinel>)` — extremely common as `one_of` branches — keep
  their "never touches the choice sequence" property, which was previously documented
  as a deliberate optimisation.

Cost we accept knowingly: `just(5)` and `sampled_from("abc")` spans change shape, so
stored database entries and `@reproduce_failure` blobs involving them are invalidated
(forced draws *do* consume from the replay prefix — `data.py` `_draw`/`_pop_choice` —
so alignment shifts). Misalignment is tolerated by design and the database re-finds
failures; `@reproduce_failure` is documented as version-fragile. Patch release, per
#4713.

Also accepted: the forced node's size counts toward the length budget, so
`sampled_from(<huge strings>)` gets marginally more expensive per draw. Fine.

### 4.3 Keep: the widening shrink pass (#4713 piece 3), reframed as primitive inversion

Port `widen_to_span_with_generated_primitive_value` and its node-synthesis helper
essentially as-is (master already has `spans_starting_at`; the port is mechanical).
Two presentational changes:

- Name and place the helper as what it is: inversion under the universal strategy of a
  primitive type. Suggest `choice_node_for_primitive(value)` next to the pass in
  `shrinker.py` (moving to `choice.py` if/when a second caller appears). Its docstring
  should state the §3 framing — this is the function that `_invert` generalizes — so
  the future direction is legible in the code.
- Keep the trigger heuristic (`integer node, min_value == 0, value != 0, followed by a
  value-carrying span`). With the `one_of` rewrite dropped, the selector node is the
  index drawn by `one_of`'s internal `sampled_from` — the node layout
  `[index][branch span...]` is unchanged, so the pass fires exactly as in #4713.
  False positives (any zero-based integer draw) cost one failed experiment; chooser
  passes tolerate that by construction.

### 4.4 Keep: explain-phase all-forced skip (#4713 piece 5)

Once `just(5)` as a top-level argument produces an all-forced slice, the explain phase
must skip it — the value provably *cannot* vary, so the "or any other generated value"
comment would be a lie. Small, and only needed because of 4.2; lands with it.

### 4.5 Tests and release note

- The `tests/quality/test_widening_shrinks.py` suite from #4713, as-is (it's the
  feature's spec: `just`, `sampled_from`, three-way `one_of`, inside `lists`,
  constrained wide branches, `builds` compound branch).
- Unit tests for span recording (adapted from #4713's `test_test_data.py` additions)
  and for primitives-only insertion, including: `st.none()` still draws nothing;
  `one_of` over non-primitive strategies inserts nothing.
- RELEASE.rst: patch, #4713's wording.

### 4.6 Dropped, and why

| Piece | From | Why dropped |
| --- | --- | --- |
| `one_of` rewrite + empty-branch retry logic | #4713 | Only needed to dodge forced-`False` insertion, which we no longer do (§4.2) |
| Forced-`False` node for non-primitive `just`/`sampled_from` | #4713 | No information content; sole cause of the `one_of` regression and most compat churn; superseded by real encodings in §6.3 |
| `test_stateful.py` formatting churn | #4713 | Unrelated reformatting; and with §4.2 most/all `encode_failure` updates should vanish (verify empirically) |
| `SearchStrategy._invert` + per-strategy impls | #4743 | No call site yet; lands as PR 2 with its first consumer (§6) |
| Exception hierarchy, `deep_equal`, `invert_many` | #4743 | Only used by `_invert`; move with it |

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

**Follow-up refactor (separate PR, before or with §6.3):** key the explain-phase data
by span index instead of node slices — `track_arg_label` marks "current span is
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
today. Revisit when §6.3 forces us to answer the object-lifetime question anyway.

## 6. Evolution path: where inversion goes next

Each phase is additive over the previous; none reworks a prior phase's interfaces.

**PR 2 — `_invert` core, with a consumer.** #4743 rebased, trimmed to the strategies
its consumer exercises, plus the review threads (add_note breadcrumb trail for
debuggability, strict-type-check unification, `LimitedStrategy`/`SharedStrategy`
raising `CannotInvertYet`). The recommended first consumer is the **generation-side**
one, because strategies are in hand there and the shrinker needs no changes:
*reproduce-and-shrink-from-value* — internally, `_invert` the pasted/`@example` value
to a choice sequence, seed the engine with it, and let normal shrinking (including the
new widening pass) take over. This is Zac's "paste an externally-reported failure"
feature, and it exercises `_invert` end-to-end through `ConjectureData.for_choices`
replay, which is exactly the verification loop invariant 1 requires. At this point
`choice_node_for_primitive` gets a docstring cross-reference (or becomes a helper
shared with `FloatStrategy._invert` etc., if that falls out naturally — not forced).

**PR 3 — non-primitive encodings for `just`/`sampled_from`.** Replace "insert nothing
for non-primitive values" with "insert the value's `_invert`-style encoding when one
is cheap" — or, more conservatively, keep insertion as-is and instead record
non-primitive span values *conditionally* (see below) so the widening pass can handle
them. This is where Zac's "unprincipled" objection gets its real answer: the principle
(§4.2) was always "encode the value as richly as the widest same-type strategy";
non-primitives simply need PR 2's machinery to say what that means.

**PR 4 — cross-branch inversion in the shrinker (the hard one).** Widening
non-primitive values into non-universal wide branches requires strategy access at
shrink time, which the shrinker architecturally lacks — this is the "very intrusive
reworking" DRMacIver flagged. Two candidate designs, both compatible with the span
annotation store, decision explicitly deferred:

- *(a) record `(strategy_ref, value)` on spans during generation.* Simple for the
  shrinker, but pins strategies and user objects in every cached `ConjectureResult`;
  needs a lifetime policy (weakrefs, or record only on interesting results).
- *(b) invert-on-replay:* the shrinker attaches guidance to the next test-case run
  ("at span *i*, branch *j*: try `_invert`ing this value first"), and `one_of.do_draw`
  performs the inversion inline, where strategies naturally live. No new lifetimes;
  more plumbing between shrinker and engine.

**Later — smarter encoders.** `.map` inversion via a registry of known inverses
(`"".join`, dataclass constructors, `operator.neg`, …), `.filter` via
check-and-delegate (already in #4743), search/solver-assisted inversion for opaque
predicates. All of these are internal upgrades behind the same
`value → choices, raising CannotInvert` contract, invisible to every caller.

Nothing in phases 2+ requires revisiting the minimal PR: the span store already
accepts `Any`, the widening pass already treats encodings as fallible experiments, and
the insertion policy is a one-line predicate that each phase widens.

## 7. Risks

- **Database/`reproduce_failure` invalidation** for primitive `just`/`sampled_from`
  users: accepted, patch-level, see §4.2. Much smaller blast radius than #4713.
- **Distribution shift** in existing test suites (the pandas-overflow flake class):
  proportionally reduced but not zero; the forced node shifts subsequent draw
  positions for affected strategies. Watch CI on the real PR.
- **Shrinker time**: the pass is chooser-gated and precondition-heavy
  (`min_value == 0`, non-forced, value ≠ 0, following span has a recorded value), so
  it's near-free when irrelevant — #4713's claim, which its narrow trigger justifies.
- **Memory**: recorded values are references to already-live primitives (the same
  objects are usually in `nodes` post-insertion); the sparse dict is per-result.
  Negligible.

## 8. Open questions for review

1. **Primitives-only insertion** (§4.2) is the load-bearing departure from #4713 —
   it's what lets us drop the `one_of` rewrite. Does DRMacIver buy the "placeholder
   nodes would be churn twice" argument, given he originally chose uniform insertion?
2. Naming: `Span.recorded_value` vs `generated_primitive_value`;
   `choice_node_for_primitive` vs `_choice_node_for_value`; `add_choice_node_for` vs
   something like `record_forced_choice`.
3. First `_invert` consumer for PR 2: reproduce-and-shrink-from-value as recommended,
   or something smaller (e.g. exact-replay assertions in our own test suite only)?
4. Should the §5 span-keyed explain-phase refactor land *before* PR 2 (cleaner
   substrate first) or lazily before PR 4 (only when forced)? Recommendation: lazily —
   it's churn with no user-visible payoff until then.
5. Any appetite for making the widening pass's trigger less heuristic now (e.g.
   labelling `one_of` selector nodes explicitly via their span label) versus keeping
   #4713's shape? Recommendation: keep #4713's shape; revisit in PR 4 which touches
   the same code.
