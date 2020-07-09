from hypothesis.internal.conjecture.dfa import DFA, Indexer, INF
from hypothesis import strategies as st, given, settings, assume, example
from hypothesis.internal.conjecture.shrinker import sort_key


def test_indexes_infinite_set():
    x = DFA([(True, [(1, 1, 0)])])
    indexer = Indexer(x)

    assert indexer.length == INF
    for i in range(100):
        assert indexer[i] == b'\x01' * i


@st.composite
def dfas(draw):
    n = draw(st.integers(1, 5))

    states = draw(
        st.lists(st.tuples(
            st.booleans(),
            st.lists(st.builds(lambda c, i: (c, c, i), st.integers(0, 255), st.integers(0, n - 1)), unique_by=lambda x: x[0]),
        ),
        min_size=n, max_size=n)
    )
    assume(any(s[0] for s in states))
    return DFA(states)

@st.composite
def dfa_index(draw):
    dfa = draw(dfas())
    indexer = Indexer(dfa)

    assume(indexer.length > 0)

    if indexer.length == INF:
        i = draw(st.integers(min_value=0))
    else: 
        i = draw(st.integers(min_value=0, max_value=indexer.length - 1))

    # Avoid case where the index would produce really
    # long strings. This can happen when the DFA is
    # not one that grows exponentially.
    assume(i < sum(indexer._Indexer__count_strings(
        0, k
    ) for k in range(20)))

    return (dfa, i)


def test_zero_length_dfa():
    dfa = DFA(((False, ((0, 0, 0),)), (True, ((1, 1, 0),))))
    indexer = Indexer(dfa)
    assert len(indexer) == 0


@example((DFA(((True, ((28, 28, 4),)), (True, ()), (False, ()), (True, ((77, 77, 2), (19, 19, 4), (26, 26, 3), (248, 248, 4))), (False, ((152, 152, 4), (59, 59, 2), (230, 230, 4))))),
     0))
@example((DFA(((True, ((0, 0, 0),)),)), 1))
@example((DFA(((False, ((0, 0, 0), (1, 1, 1))), (True, ()))), 0),)
@settings(report_multiple_bugs=False)
@given(dfa_index())
def test_can_index_arbitrary_dfa(dfai):
    dfa, i = dfai

    indexer = Indexer(dfa)

    s = indexer[i]
    assert dfa.matches(s)

    if i > 0:
        s2 = indexer[i - 1]
        assert sort_key(s2) < sort_key(s)
    if i + 1 < indexer.length:
        s3 = indexer[i + 1]
        assert sort_key(s3) > sort_key(s)


@example(DFA(((True, ((1, 1, 0), (0, 0, 0))),)))
@given(dfas())
def test_agrees_with_iteration(dfa):
    x = Indexer(dfa)
    for i, s in enumerate(x):
        if i >= 20:
            break
        assert x[i] == s


@example((DFA(((False, ((0, 0, 1),)), (True, ((1, 1, 1),)))), 1))
@given(dfa_index())
def test_can_look_up_string(dfai):
    dfa, i = dfai
    x = Indexer(dfa)

    assert x.index(x[i]) == i
    assert Indexer(dfa).index(x[i]) == i


@example(b'\x00\x01', DFA(((True, ()),)))
@given(st.binary(), dfas())
def test_all_matches_match(s, dfa):
    matches = set(dfa.all_matches(s))
    for i, j in matches:
        assert dfa.matches(s[i:j])


@given(
    st.binary(),
    st.binary(),
    dfa_index()
)
def test_all_matches_contained_in_all_matches(s1, s2, dfai):
    dfa, i = dfai

    t = Indexer(dfa)[i]

    assume(t)

    s = s1 + t + s2

    assert (len(s1), len(s1) + len(t)) in dfa.all_matches(s)


@example(b'\x00\x00', DFA(((True, ((0, 0, 0),)),)))
@settings(max_examples=10**6)
@given(st.binary(), dfas())
def test_all_matches_are_unique(s, dfa):
    matches = dfa.all_matches(s)
    assert len(set(matches)) == len(matches)



@example(DFA([(True, [])]))
@given(dfas())
def test_can_serialize_a_dfa(dfa):
    assert DFA.from_compact(dfa.to_compact()) == dfa
