# Design: value-widening shrinks, and a path to general strategy inversion

Working document for the work that combines the strictly-necessary parts of
[#4713](https://github.com/HypothesisWorks/hypothesis/pull/4713) (allow shrinking of
generated values into wider strategies) and
[#4743](https://github.com/HypothesisWorks/hypothesis/pull/4743) (internal
`SearchStrategy._invert`). This file is the deliverable for now; it will be deleted
once we agree on the design and replace it with code.

The plan is a three-PR sequence:

1. **Span substrate** — track values on spans; migrate the explain-phase /
   pretty-printer bookkeeping onto spans (refactoring and prep, behavior-preserving).
2. **Widening pass** — the user-visible shrinking feature, with `_invert` debuting on
   the primitive strategies only, as the pass's encoding step.
3. **Growth** — `_invert` on compound strategies, additional consumers of inversion,
   recovering the accepted limitations. Ideas, not commitments.

## 1. Goals and non-goals

**Goal (the feature, PR 2).** When a user writes `wide | specific` — e.g.
`st.text() | some_grammar_strategy`, `st.integers() | st.sampled_from([...])` — and
the failing value comes from the `specific` branch, the shrinker should be able to
slip that value across into the `wide` branch and shrink it as an arbitrary member of
the wider space. This was #4713's motivating case ("you might want to not crash on
arbitrary bytes, but the interesting space corresponds to some grammar").

**Accepted limitation: `just()` does not slide.** A `just` span contains zero
choices, so any wide-branch encoding of its value makes the choice sequence *longer*,
which the shrinker's monotone ordering rejects (§3). #4713 solved this by inserting
artificial forced choice nodes into `just`/`sampled_from` spans — and that single
mechanism was the source of nearly all of that PR's complexity and compatibility
surface (§4.4). Accepting the limitation deletes the mechanism, and with it every
generation-side behavior change. The loss is small: a `just` value is a constant the
user wrote explicitly, so "it didn't shrink further" is far less surprising there
than for a grammar-generated blob — and §6 sketches two additive ways to recover
`just`-sliding later. Notably, `sampled_from` still slides *without* any insertion
(§3), so the limitation really is just `just`.

**Goal (the architecture).** Each PR is independently motivated and reviewable, and
each is a named step toward general inversion (`value → choice sequence`), so that
later work — non-primitive widening, "paste an externally-reported failure into
`@example(...)` and we'll shrink it", solver-assisted inversion of `.filter`/`.map` —
is additive rather than a rewrite.

**Non-goals for this sequence.** No inversion of non-primitive values, no
`map`/`filter` inversion, no solver anything, no change to what any strategy draws.

## 2. Background: the machinery we're touching

*Choice sequence & spans.* Every strategy draw appends `ChoiceNode`s (five primitive
types: `integer`, `float`, `boolean`, `string`, `bytes`) and opens/closes a `Span` — a
labelled `[start, end)` region of the choice sequence, stored compactly in
`SpanRecord`/`Spans` and materialized lazily after the test case completes. The
shrinker works purely on `(nodes, spans)`; **it has no access to strategy objects**,
and the conjecture layer must not import from the strategies layer (existing
exceptions are `TYPE_CHECKING`-only or function-local lazy imports, e.g.
`unwrap_strategies` in `data.py`). Its acceptance criterion is strict: a proposal is
taken only if `sort_key(new) < sort_key(old)`, where
`sort_key = (len(nodes), tuple(choice_to_index(...)))` — shorter wins, then
lexicographically-earlier-and-lower wins.

*Explain phase / pretty-printer.* `BuildContext.track_arg_label` measures
`len(data.nodes)` before and after each top-level argument draw and records the
`(start_node, end_node)` slice into `data.arg_slices` — hand-derived span boundaries,
computed that way only because spans aren't materialized until after the run. The
shrinker's explain phase re-runs the test varying each slice and writes
`data.slice_comments[(start, end)]` notes ("or any other generated value"); the
pretty-printer (`RepresentationPrinter.repr_call`) looks comments up by slice.
Separately, `BuildContext.record_call` registers id-keyed printers
(`known_object_printers`) so objects built by `builds`/`map` repr as calls — id-keying
is known-fragile for cached/interned objects (the code comments on small ints etc.).

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
   piece 2 regressed `one_of`; the rewrite makes it draw its index directly.
5. **Explain-phase fix** — skip slices whose nodes are all forced (nothing can vary,
   so the "or any other generated value" comment would be false). Needed because
   piece 2 makes `just(5)` as a top-level argument an all-forced slice.

We take pieces 1 and 3 (in PRs 1 and 2 respectively) and drop 2, 4, and 5 (§4.4).

*What #4743 does:* adds internal `_invert(value) -> tuple[ChoiceT, ...]` ("return
choices that replay to this value, best-effort") to ~20 strategies, a
`CannotInvert`/`CannotInvertYet`/`DefinitelyCannotInvert` exception hierarchy,
NaN-aware `deep_equal`, and an `invert_many` mirror of `cu.many`. Explicitly
infrastructure-only: nothing calls it. We take the exception hierarchy, the base
method, and the five primitive-strategy implementations (PR 2); everything else
waits for a consumer (§6).

## 3. The unifying model

The two PRs are the two directions of the same arrow:

- **Spans decode:** a span maps a region of the choice sequence to the value it
  produced. Span value recording makes the decode direction *queryable after the
  fact*.
- **`_invert` encodes:** it maps a value back to a choice-sequence region that would
  reproduce it under a given strategy.

The widening feature is `encode(wide_strategy, decode(specific_span))` followed by a
standard shrink experiment. PR 2 implements the encode direction only for the
*universal strategy of each primitive type* — "any int", "any string", … — whose
inversions are single choices with maximally-permissive constraints. That is all the
feature needs, because replay-time constraint checking specializes the universal
encoding to whatever the wide branch actually accepts.

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

## 4. The plan

### 4.1 PR 1 — span substrate: track values on spans; migrate explain/pprint onto them

Behavior-preserving refactor plus new metadata. Three parts, in one PR (or split
1a/1b if review prefers):

**(1a) The annotation store.** `SpanRecord` gains an open-span stack (it currently
has no live notion of "current span") and a sparse `dict[span_index, Any]` of
recorded values, populated by `ConjectureData.draw` from the value `do_draw` returns:

- *Always*: values whose `type(...)` is one of the five primitive types (exact type
  check — this also conveniently never records symbolic values from alternative
  backends, whose types differ from the builtins, so we never pin or realize them).
- *Final replay only* (`is_final` BuildContext): all values. Cached
  `ConjectureResult`s must not pin arbitrary user objects, but the final replay's
  data is short-lived and already holds these objects for printing.

`Span` exposes `recorded_value` (returns `None` when absent). Recording at the
`ConjectureData.draw` level — not inside individual strategies — is load-bearing for
PR 2: it's what lets `text() | st.builds(make_str, ...)` widen, because the
*compound* branch's span records the final `str` it produced.

**(1b) Explain/pprint migration.** Key the explain-phase data by span rather than by
hand-computed node slices: `track_arg_label` marks "current span is reportable
argument *k*" via the open-span stack; `arg_slices` becomes data derived from span
boundaries; `slice_comments` becomes span-keyed; the pretty-printer resolves span →
slice at print time. This deletes the manual `len(data.nodes)` arithmetic in
`BuildContext`, gives the explain phase span metadata it currently can't see (e.g.
discarded regions), and establishes spans as the single "which region produced what"
substrate that PR 2 then reads from. No user-visible change.

**(1c — optional, can trail)** With final-replay values recorded on spans,
`repr_call`'s argument values and slices can come from child spans instead of the
objects captured at `record_call` time, reducing (not yet removing) reliance on
id-keyed `known_object_printers`, whose id-keying is fragile for interned objects.
This is the "object ids associated with choice-sequence-spans, shared with
call-pprinting" idea from #4713's review thread. Include only if it falls out
simply; the printer is object-driven, so some id-keyed lookup survives regardless.

*Honesty note:* the always-recorded *primitive* values have their first real consumer
in PR 2 — PR 1's pprint payoff comes from the open-span stack, the store, and
(1b)/(1c). If reviewers object to landing that one dict-write early, it moves to PR 2
trivially; we prefer it in PR 1 so PR 2 is purely "a shrink pass plus `_invert`".

### 4.2 PR 2 — the widening pass, with `_invert` on primitive strategies

The feature PR, now small because the substrate exists:

**`SearchStrategy._invert(value) -> tuple[ChoiceT, ...]`** lands with #4743's
contract (best-effort, caller verifies by replay) and exception hierarchy
(`CannotInvert`, `CannotInvertYet` as the base-class default, `DefinitelyCannotInvert`
for provably-out-of-image), implemented **only** on the five primitive strategies:
`IntegersStrategy`, `FloatStrategy`, `BooleansStrategy`, `BytesStrategy`, and
`TextStrategy`/`OneCharStringStrategy` (the one-char-alphabet fast path; other
element strategies raise `CannotInvertYet`). Each checks its constraints
(NaN-aware where relevant) and returns `(value,)` or raises. These are #4743's
implementations, roundtrip tests included, minus everything compound.

**The widening pass** ports #4713's piece 3 (master already has
`spans_starting_at`; the port is mechanical), with its encoding step expressed as
inversion under the universal strategies:

- The pass lazy-imports and caches canonical wide-open instances (unwrapped
  `st.integers()`, `st.floats()`, `st.booleans()`, `st.text()`, `st.binary()`) and
  calls `_invert(recorded_value)` on the one matching the value's type. Lazy import
  is the sanctioned pattern for this layering cycle (`data.py` already does it for
  `unwrap_strategies`).
- `_invert` returns *choices*; wrapping them in `ChoiceNode`s with
  maximally-permissive constraints (for sort-key purposes — replay re-derives the
  wide branch's real constraints) stays a conjecture-layer helper, essentially
  #4713's `_choice_node_for_value`. This division of labor is deliberate and
  permanent: `_invert` never needs to know about nodes or constraints-for-sorting,
  so future multi-choice inversions from compound strategies slot straight in.
- Trigger heuristic unchanged from #4713 (`integer node, min_value == 0, value != 0,
  followed by a value-carrying span`), plus a `choice_count > 0` pre-filter on
  candidate spans, since zero-node (`just`) spans are known-futile (§3).

**Tests:** #4713's `tests/quality/test_widening_shrinks.py` with `just`-branch cases
converted to `sampled_from`/compound equivalents, plus a grammar-ish composite case
(the headline motivation); #4743's roundtrip + out-of-image tests for the five
primitive `_invert`s; a regression test pinning that `wide | just(v)` does not slide
and that generation behavior is byte-for-byte unchanged (keep
`test_just_strategy_does_not_draw`, which #4713 deleted). RELEASE.rst: patch;
reword #4713's note, which promised `just`-sliding.

*Honesty note:* in PR 2, `_invert` is only ever *called* on unconstrained instances,
where it degenerates to a type-and-permittedness check plus `return (value,)`. The
constrained code paths (e.g. `integers(0, 10)._invert(-5)` raising) are exercised by
tests but not by the feature until PR 3 consumers arrive. We think that's fine — the
implementations are small, the contract is the point — but it's the main "code not
yet earning its keep" objection someone could raise, and routing the pass through
`_invert` (rather than a private helper) is exactly what makes the interface real
rather than speculative.

### 4.3 Sequencing trade-offs (vs. shipping the feature first)

What this ordering buys: the churny refactor (1b) is reviewed on its own,
behavior-preserving merits instead of riding inside a feature diff; PR 2 becomes a
small, legible "one shrink pass + one method on five classes"; and `_invert` debuts
at minimum scope with a real consumer on day one. What it costs: the user-visible
feature waits behind prep work, and PR 1 is the largest review. We accept that trade
so long as PR 1 stays disciplined — no scope creep beyond 1a/1b(/1c).

### 4.4 What this sequence deliberately does not contain

| Piece | From | Why dropped |
| --- | --- | --- |
| Forced-node insertion in `just`/`sampled_from` | #4713 | Only needed for `just`-sliding, which we've accepted losing; sole source of all generation-side churn (§4.5) |
| `one_of` rewrite + empty-branch retry logic | #4713 | Only needed to dodge insertion's forced-`False` in `sampled_from(strategies)` |
| Explain-phase all-forced-slice skip | #4713 | Only needed once insertion creates all-forced slices. (It's *also* a latent fix for rare all-forced slices on master, e.g. `sampled_from`'s exhaustive-fallback forced index — worth a tiny standalone PR, but not this sequence) |
| `test_stateful.py` / `reproduce_failure` blob churn | #4713 | Consequence of insertion; vanishes with it |
| `_invert` on compound strategies (~15 of #4743's 20) | #4743 | No consumer until PR 3; includes `invert_many`, `deep_equal`, and the wrapper delegations (`Lazy`/`Deferred`/…), none of which PR 2's universal instances need |

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

## 5. Where the old bookkeeping ends up

After PR 1 there is one substrate instead of three parallel ones:

1. `arg_slices` / `slice_comments` — become span-derived / span-keyed (PR 1b).
2. `known_object_printers` — stays id-keyed for now (the printer is object-driven);
   partially fed from span-recorded final-replay values if 1c lands. Full unification
   is possible but low-value until PR 3 forces the object-lifetime question anyway.
3. Span recorded values — the new store; read by the widening pass (PR 2), the
   printer (1c), and every future consumer in §6.

## 6. PR 3 and beyond: growth, not commitments

Each item is additive; none reworks PR 1/2 interfaces.

**More `_invert` implementations, each landing with a consumer.** The flagship
consumer is generation-side, where strategies are in hand and the shrinker needs no
changes: *reproduce-and-shrink-from-value* — `_invert` a pasted/`@example` value to a
choice sequence, seed the engine, and let normal shrinking (including the widening
pass) take over. That consumer immediately justifies the compound implementations
from #4743 (`tuples`, `lists` + `invert_many`, `one_of` delegation, `datetimes`, …,
plus `deep_equal` for `just`/`sampled_from` equality) — rebased and trimmed per that
PR's existing review threads (add_note breadcrumbs, strict-type-check unification).

**Recovering `just()`-sliding, if users ask.** Two additive options:
*(a)* reinstate insertion scoped to `JustStrategy` + primitive values — a one-method
change; `sampled_from` never needs it (§3), so `one_of` internals stay untouched and
the compat surface is limited to `just(<primitive>)` users. *(b)* a post-shrink slide
experiment outside the monotone ordering — the explain phase already demonstrates the
pattern of non-shrinking experiments after shrinking stabilizes; a slide experiment
("re-encode span under earlier branch, then re-shrink") terminates because the branch
selector strictly decreases. (b) never touches generation and is also the natural
home for *non-primitive* cross-branch movement, so we likely want it eventually
regardless, and (a) only as a stopgap.

**Cross-branch inversion in the shrinker (the hard one).** Widening non-primitive
values into non-universal wide branches requires strategy access at shrink time,
which the shrinker architecturally lacks — the "very intrusive reworking" concern
from #4713's thread. Two candidate designs, both compatible with the span store,
decision deferred: *(i)* record `(strategy_ref, value)` on spans during generation
(simple for the shrinker; needs a lifetime policy for cached results); *(ii)*
invert-on-replay — the shrinker attaches guidance to the next run ("at span *i*,
branch *j*: try `_invert`ing this value first") and `one_of.do_draw` inverts inline,
where strategies naturally live. (ii) composes with (b) above.

**Smarter encoders.** `.map` inversion via a registry of known inverses (`"".join`,
dataclass constructors, …), `.filter` via check-and-delegate (already in #4743),
search/solver-assisted inversion for opaque predicates. All internal upgrades behind
the same `value → choices, raising CannotInvert` contract, invisible to callers.

## 7. Risks

- **The `sampled_from`-slides-without-insertion prediction (§3) could be wrong.**
  It follows directly from the sort key, but #4713 only demonstrated widening *with*
  insertion. Verify with a quick prototype before PR 1 lands, since the whole
  sequence is premised on never touching generation; the fallback position (only
  compound branches slide) still covers the grammar motivation but weakens PR 2.
- **PR 1 scope creep.** The explain/pprint migration touches `control.py`,
  `data.py`, `shrinker.py`, and `vendor/pretty.py`; it must stay behavior-preserving
  and mechanical, or it will absorb the whole sequence's review budget.
- **Layering.** PR 2's pass calls `_invert` across the conjecture→strategies
  boundary via a cached lazy import — precedented (`data.py`'s `unwrap_strategies`)
  but worth a comment in code; the node-wrapping helper deliberately stays on the
  conjecture side so the dependency is one thin, one-way call.
- **Shrinker time**: the pass is chooser-gated and precondition-heavy, near-free when
  irrelevant — #4713's claim, which its narrow trigger justifies.
- **Memory**: primitive recorded values are references, and full-object recording is
  final-replay-only by design. Negligible.
- **Compatibility**: none. No choice sequence changes shape; databases and
  `@reproduce_failure` blobs are untouched. (This line is the point of the design.)

## 8. Open questions for review

1. **Empirical check before anything else**: prototype the pass on master and confirm
   `integers() | sampled_from([4991, ...])` and the `builds` compound case slide
   without insertion, per the §3 table. If yes, the design stands as written.
2. Is losing `wide | just(v)` sliding acceptable? (This design says yes, with §6 as
   the recovery path. #4713's quality tests featured it heavily, so this needs
   explicit sign-off rather than silent dropping.)
3. PR 1 scope: is 1c (span-fed call reprs) in or out? In makes "values on spans, used
   for pprinting" literally true in PR 1; out keeps PR 1 smaller and leaves the
   primitive-value recording's first consumer to PR 2. Recommendation: out, unless it
   falls out in a few lines.
4. PR 2 wiring: `_invert` called via lazy-imported universal instances (recommended,
   precedented) vs. keeping a conjecture-layer free function and letting `_invert`
   land later with a generation-side consumer. The former honors "the pass is
   implemented via `_invert`"; the latter is stricter about layering purity.
5. Naming: `Span.recorded_value` vs `generated_primitive_value`; and does the
   node-wrapping helper live in `shrinker.py` or `choice.py`?
