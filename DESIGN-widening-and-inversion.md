# Design: value-widening shrinks, and a path to general strategy inversion

Working document for the work that combines the strictly-necessary parts of
[#4713](https://github.com/HypothesisWorks/hypothesis/pull/4713) (allow shrinking of
generated values into wider strategies) and
[#4743](https://github.com/HypothesisWorks/hypothesis/pull/4743) (internal
`SearchStrategy._invert`). This file is the deliverable for now; it will be deleted
once we agree on the design and replace it with code.

The plan is a three-PR sequence:

1. **Span substrate** — migrate the explain-phase / pretty-printer bookkeeping from
   hand-computed node slices onto spans, and land the explain-phase all-forced-slice
   fix (a latent master bug). Refactoring and prep, behavior-preserving.
2. **Widening pass** — the user-visible shrinking feature: span value recording, plus
   `_invert` debuting on the primitive strategies only, as the pass's encoding step.
3. **Growth** — `_invert` on compound strategies, additional consumers of inversion,
   recovering the accepted limitations. Ideas, not commitments.

**Status: the §3 arithmetic is prototype-verified** (2026-07-19, patch in session
scratchpad, `pr2-widening-prototype.patch`). With span value recording plus the
widening pass — no node insertion, no strategy changes of any kind — all of the
following shrink to the wide-branch minimum: `integers() | sampled_from(...)` (open
and bounded), `text() | sampled_from(...)` (open and alphabet-restricted),
`text() | builds(...)` compound, and `lists(text() | sampled_from(...))`. As
predicted, `text() | just(...)` does not slide. The full `tests/conjecture` suite
(782 tests) and `tests/quality/test_shrink_quality.py` (90 tests) pass unmodified
against the prototype.

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
surface (§4.5). Accepting the limitation deletes the mechanism, and with it every
generation-side behavior change. The loss is small: a `just` value is a constant the
user wrote explicitly, so "it didn't shrink further" is far less surprising there
than for a grammar-generated blob — and §6 sketches two additive ways to recover
`just`-sliding later. Note that single-element `sampled_from` collapses to `just()`
at construction time and so inherits the limitation; two or more elements slide fine
(prototype-verified).

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
   so the "or any other generated value" comment would be false). #4713 needed it
   because piece 2 makes `just(5)` as a top-level argument an all-forced slice, but
   it is *also* a latent fix on master (e.g. `sampled_from`'s exhaustive-fallback
   path emits a forced index node), so we take it in PR 1 regardless.

We take pieces 1 and 3 (in PRs 2), piece 5 (in PR 1), and drop 2 and 4 (§4.4).

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
| 0 nodes (`just`, incl. 1-element `sampled_from`) | one node longer | **rejected** |

#4713's node insertion existed to move `just` (and, uniformly, `sampled_from`) out of
the bottom rows by pre-paying the node cost at generation time. Accepting that `just`
doesn't slide means we never touch generation at all — and the table's predictions,
including that `sampled_from` and every compound branch slide anyway, are now
prototype-verified (see Status above).

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

### 4.1 PR 1 — span substrate: explain/pprint bookkeeping onto spans

Behavior-preserving refactor plus one latent bug fix. Three parts:

**Span counting.** `SpanRecord` learns how many spans have started (a counter — the
full open-span *stack* waits for PR 2, where its consumer lands), exposed via
`ConjectureData`. This is the one-line mechanism that lets `BuildContext` know which
span a draw is about to create.

**Explain/pprint migration.** Key the explain-phase data by span index rather than by
hand-computed node slices: `track_arg_label` records "the span created by this draw
is reportable argument *k*"; `arg_slices: set[tuple[int, int]]` becomes
`arg_spans: set[int]`; `slice_comments` becomes span-keyed (with a `None` key for the
whole-test "varied together" comment, replacing the `(0, 0)` sentinel); the shrinker's
explain phase resolves spans to node ranges via the already-materialized `Spans`; the
pretty-printer looks comments up by span index. This deletes the manual
`len(data.nodes)` arithmetic in `BuildContext`, gives the explain phase span metadata
it previously couldn't see, and establishes spans as the single "which region
produced what" substrate that PR 2 reads from. No user-visible change.

**All-forced-slice fix (from #4713, pulled forward).** The explain phase skips spans
whose node range is empty or entirely forced — the value provably cannot vary, so the
"or any other generated value" comment would be false. On master this is reachable
(rarely) via forced draws like `sampled_from`'s exhaustive-fallback index; after
PR 2's widening it matters more, so it lands here with the semantics fix framing.

*Deliberately not in PR 1:* span value recording (the `dict` + the write in
`ConjectureData.draw`) — it lands in PR 2 next to its consumer, keeping each PR
conceptually self-contained. Likewise nothing changes about `record_call` /
`known_object_printers` (the id-keyed object printers): span-fed call reprs were
considered and deferred indefinitely — the printer is object-driven, so id-keying
survives anyway, and the win was marginal.

### 4.2 PR 2 — the widening pass, with `_invert` on primitive strategies

The feature PR, now small because the substrate exists (total prototype delta over
PR 1: ~150 lines of src):

**Span value recording.** `SpanRecord` gains the open-span stack and a sparse
`dict[span_index, Any]`; `ConjectureData.draw` records the value `do_draw` returned
against the just-closed span iff `type(value)` is one of the five primitive types
(exact type check — this also conveniently never records symbolic values from
alternative backends, whose types differ from the builtins, so we never pin or
realize them). Exposed as `Span.recorded_value`, `None` when absent. Recording at
the `ConjectureData.draw` level — not inside individual strategies — is load-bearing:
it's what lets `text() | st.builds(make_str, ...)` widen, because the *compound*
branch's span records the final `str` it produced (prototype-verified).

**`SearchStrategy._invert(value) -> tuple[ChoiceT, ...]`** lands with #4743's
contract (best-effort, caller verifies by replay) and exception hierarchy
(`CannotInvert`, `CannotInvertYet` as the base-class default, `DefinitelyCannotInvert`
for provably-out-of-image), implemented **only** on the five primitive strategies:
`IntegersStrategy`, `FloatStrategy`, `BooleansStrategy`, `BytesStrategy`, and
`TextStrategy`/`OneCharStringStrategy` (the one-char-alphabet fast path; other
element strategies raise `CannotInvertYet`). Each checks its constraints (NaN-aware
where relevant) and returns `(value,)` or raises. These are #4743's implementations,
roundtrip tests included, minus everything compound.

**The widening pass** ports #4713's piece 3 (mechanical — the prototype is exactly
this), with its encoding step expressed as inversion under the universal strategies:

- *Wiring, initial version:* the pass lazy-imports and caches canonical wide-open
  instances (unwrapped `st.integers()`, `st.floats()`, `st.booleans()`, `st.text()`,
  `st.binary()`) and calls `_invert(recorded_value)` on the one matching the value's
  type. Lazy import is the sanctioned pattern for this layering cycle (`data.py`
  already does it for `unwrap_strategies`), and this call site is trivially
  deletable.
- *Wiring, intended destination:* strategies↔shrinker communication should
  eventually go through the choice-sequence data structure itself (or its
  with-holes form, à la `ChoiceTemplate`) — e.g. the shrinker proposes a sequence
  containing an annotated hole ("this branch, this value") and the generation side
  fills it by inverting where strategies naturally live. That is the PR-4-era
  mechanism (§6); the lazy import is an explicitly interim bridge until it exists.
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
converted to `sampled_from`/compound equivalents (≥ 2 elements — one collapses to
`just`), plus a grammar-ish composite case (the headline motivation); #4743's
roundtrip + out-of-image tests for the five primitive `_invert`s; a regression test
pinning that `wide | just(v)` does not slide and that generation behavior is
byte-for-byte unchanged (keep `test_just_strategy_does_not_draw`, which #4713
deleted). RELEASE.rst: patch; reword #4713's note, which promised `just`-sliding.

*Honesty note:* in PR 2, `_invert` is only ever *called* on unconstrained instances,
where it degenerates to a type-and-permittedness check plus `return (value,)`. The
constrained code paths (e.g. `integers(0, 10)._invert(-5)` raising) are exercised by
tests but not by the feature until PR 3 consumers arrive. We think that's fine — the
implementations are small, the contract is the point — but it's the main "code not
yet earning its keep" objection someone could raise, and routing the pass through
`_invert` (rather than a private helper) is exactly what makes the interface real
rather than speculative.

### 4.3 Sequencing trade-offs (vs. shipping the feature first)

What this ordering buys: the churny refactor is reviewed on its own,
behavior-preserving merits instead of riding inside a feature diff; PR 2 becomes a
small, legible "one shrink pass + one method on five classes + one recording write";
and `_invert` debuts at minimum scope with a real consumer on day one. What it costs:
the user-visible feature waits behind prep work, and PR 1 is the largest review. We
accept that trade so long as PR 1 stays disciplined — no scope creep.

### 4.4 What this sequence deliberately does not contain

| Piece | From | Why dropped |
| --- | --- | --- |
| Forced-node insertion in `just`/`sampled_from` | #4713 | Only needed for `just`-sliding, which we've accepted losing; sole source of all generation-side churn (§4.5) |
| `one_of` rewrite + empty-branch retry logic | #4713 | Only needed to dodge insertion's forced-`False` in `sampled_from(strategies)` |
| `test_stateful.py` / `reproduce_failure` blob churn | #4713 | Consequence of insertion; vanishes with it |
| `_invert` on compound strategies (~15 of #4743's 20) | #4743 | No consumer until PR 3; includes `invert_many`, `deep_equal`, and the wrapper delegations (`Lazy`/`Deferred`/…), none of which PR 2's universal instances need |
| Span-fed call reprs (reduce id-keyed printer reliance) | (new idea) | Marginal win; printer is object-driven so id-keying survives regardless; revisit only if PR 3+ needs span→object anyway |

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

1. `arg_slices` / `slice_comments` — become `arg_spans` / span-keyed comments (PR 1).
2. `known_object_printers` — stays id-keyed (see §4.4 last row).
3. Span recorded values — added in PR 2; read by the widening pass and every future
   consumer in §6.

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
change; `sampled_from` never needs it (prototype-verified), so `one_of` internals
stay untouched and the compat surface is limited to `just(<primitive>)` users.
*(b)* a post-shrink slide experiment outside the monotone ordering — the explain
phase already demonstrates the pattern of non-shrinking experiments after shrinking
stabilizes; a slide experiment ("re-encode span under earlier branch, then
re-shrink") terminates because the branch selector strictly decreases. (b) never
touches generation and is also the natural home for *non-primitive* cross-branch
movement, so we likely want it eventually regardless, and (a) only as a stopgap.

**Cross-branch inversion in the shrinker (the hard one).** Widening non-primitive
values into non-universal wide branches requires strategy access at shrink time,
which the shrinker architecturally lacks. The agreed direction is to route this
through the choice-sequence data structure (or its with-holes form): the shrinker
proposes a sequence containing an annotated hole — "at this position, branch *j*
should try to `_invert` this value" — and generation fills the hole where strategies
naturally live, generalizing how `ChoiceTemplate` prefixes work today. This replaces
PR 2's interim lazy-import wiring, composes with option (b) above, and avoids
recording strategy references on spans (with the lifetime problems that would bring).

**Smarter encoders.** `.map` inversion via a registry of known inverses (`"".join`,
dataclass constructors, …), `.filter` via check-and-delegate (already in #4743),
search/solver-assisted inversion for opaque predicates. All internal upgrades behind
the same `value → choices, raising CannotInvert` contract, invisible to callers.

## 7. Risks

- ~~The `sampled_from`-slides-without-insertion prediction could be wrong~~ —
  **resolved**: prototype-verified across open/bounded integers, open/restricted
  text, compound builds, and nested-in-lists cases, with the full conjecture and
  shrink-quality suites passing.
- **PR 1 scope creep.** The explain/pprint migration touches `control.py`,
  `data.py`, `shrinker.py`, `vendor/pretty.py`, and `core.py`; it must stay
  behavior-preserving and mechanical, or it will absorb the whole sequence's review
  budget.
- **Layering.** PR 2's pass calls `_invert` across the conjecture→strategies
  boundary via a cached lazy import — precedented (`data.py`'s `unwrap_strategies`),
  explicitly interim (§4.2), and trivially deletable once the choice-sequence-hole
  mechanism exists.
- **Shrinker time**: the pass is chooser-gated and precondition-heavy, near-free when
  irrelevant — #4713's claim, which its narrow trigger justifies.
- **Memory**: primitive recorded values are references; the sparse dict is
  per-result. Negligible.
- **Compatibility**: none. No choice sequence changes shape; databases and
  `@reproduce_failure` blobs are untouched. (This line is the point of the design.)

## 8. Resolved questions

1. *Does widening work without insertion?* **Yes** — prototype-verified, see Status.
2. *Is losing `wide | just(v)` sliding acceptable?* **Yes** (with §6 recovery paths;
   single-element `sampled_from` collapses to `just` and shares the limitation).
3. *Span-fed call reprs (old "1c") in PR 1?* **Out**; primitive-value recording also
   moves to PR 2, keeping PR 1 purely substrate + fix.
4. *PR 2 wiring?* Lazy-imported universal instances as an explicitly interim bridge;
   the destination is communication via the choice-sequence data structure (§6).
5. *Naming?* `Span.recorded_value`. The node-wrapping helper's home is undecided
   (`shrinker.py` initially; move if a second caller appears).
