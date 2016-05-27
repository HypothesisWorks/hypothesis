from hypothesis import strategies as st
from hypothesis import assume, find
from collections import Counter


@st.composite
def election(draw, max_candidates=10):
    candidates = list(range(draw(st.integers(2, max_candidates))))
    return draw(
        st.lists(st.permutations(candidates), min_size=1)
    )


def candidates_for_election(election):
    return sorted({c for cs in election for c in cs})
    
    
def plurality_winner(election):
    counts = Counter(vote[0] for vote in election)
    alternatives = candidates_for_election(election)
    winning_score = max(counts.values())
    winners = [c for c, v in counts.items() if v == winning_score]
    if len(winners) > 1:
        return None
    else:
        return winners[0]


def irv_winner(election):
    candidates = candidates_for_election(election)
    while len(candidates) > 1:
        scores = Counter()
        for vote in election:
            for c in vote:
                if c in candidates:
                    scores[c] += 1
                    break
        losing_score = min(scores[c] for c in candidates)
        candidates = [c for c in candidates if scores[c] > losing_score]
    if not candidates:
        return None
    else:
        return candidates[0]

def differing_without_ties(election):
    irv = irv_winner(election)
    if irv is None:
        return False
    plurality = plurality_winner(election)
    if plurality is None:
        return False
    return irv != plurality


def is_majority_dominated(election, c):
    scores = Counter()
    for vote in election:
        for d in vote:
            if d == c:
                break
            scores[d] += 1
    return any(score > len(election) / 2 for score in scores.values())


def find_majority_dominated_winner(method):
    def test(election):
        winner = method(election)
        return winner is not None and is_majority_dominated(election, winner)
    return find(election(), test)
