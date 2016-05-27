---
layout: post
tags: python technical
date: 2016-05-26 11:00
title: Exploring Voting Systems with Hypothesis
published: true
author: drmaciver
---

Hypothesis is, of course, a library for writing tests.

But from an *implementation* point of view this is hardly noticeable.
Really it's a library for constructing and exploring data and using it
to prove or disprove hypotheses about it. It then has a small testing
library built on top of it.

It's far more widely used as a testing library, and that's really where
the focus of its development lies, but with the *find* function you can
use it just as well to explore your data interactively.

In this article we'll go through an example of doing this, by using it
to take a brief look at one of my other favourite subjects: Voting
systems.

<!--more-->

We're going to focus entirely on single winner preferential voting
systems: You have a set of candidates, and every voter gives a complete
ordering of the candidates from their favourite to their least
favourite. The voting system then tries to select a single candidate and
declare them the winner.

The general Python interface for a voting system we'll use is things
that look like the following:

```python
def plurality_winner(election):
    counts = Counter(vote[0] for vote in election)
    alternatives = candidates_for_election(election)
    winning_score = max(counts.values())
    winners = [c for c, v in counts.items() if v == winning_score]
    if len(winners) > 1:
        return None
    else:
        return winners[0]
```

That is, they take a list of individual votes, each expressed
as a list putting the candidates in order, and return a candidate that
is an unambiguous winner or None in the event of a tie.

The above implements plurality voting, what most people might think of
as "normal voting": The candidate with the most first preference votes
wins.

The other main voting system we'll consider is Instant Runoff Voting (
which you might know under the name "Alternative Vote" if you follow
British politics):
 
```python
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
```

In IRV, we run the vote in multiple rounds until we've eliminated all
but one candidate. In each round, we give each candidate a score which
is the number of voters who have ranked that candidate highest amongst
all the ones remaining. The candidates with the joint lowest score
drop out.

At the end, we'll either have either zero or one candidates remaining (
we can have zero if all candidates are tied for joint lowest score at
some point). If we have zero, that's a draw. If we have one, that's a
victory.

It seems pretty plausible that these would not produce the same answer
all the time (it would be surpising if they did!), but it's maybe not
obvious how you would go about constructing an example that shows it.

Fortunately, we don't have to because Hypothesis can do it for us!

We first create a strategy which generates elections, using Hypothesis's
composite decorator:

```python
import hypothesis.strategies as st

@st.composite
def election(draw):
    candidates = list(range(draw(st.integers(2, 10))))
    return draw(
        st.lists(st.permutations(candidates), min_size=1)
    )
```

This first draws the set of candidates as a list of integers of size
between 2 and 10 (it doesn't really matter what our candidates are as
long as they're distinct, so we use integers for simplicity). It then
draws an election as lists of permutations of those candidates, as we
defined it above.

We now write a condition to look for:

```python
def differing_without_ties(election):
    irv = irv_winner(election)
    if irv is None:
        return False
    plurality = plurality_winner(election)
    if plurality is None:
        return False
    return irv != plurality
```

That is, we're interested in elections where neither plurality nor IRV
resulted in a tie, but they resulted in distinct candidates winning.

We can now run this in the console:

```
>>> import voting as v
>>> distinct = find(v.election(), v.differing_without_ties)
>>> distinct
[[0, 1, 2],
 [0, 1, 2],
 [1, 0, 2],
 [2, 1, 0],
 [0, 1, 2],
 [0, 1, 2],
 [1, 0, 2],
 [1, 0, 2],
 [2, 1, 0]]
```

The example is a bit large, mostly because we insisted on there being
no ties: If we'd broken ties arbitrarily (e.g. preferring the lower
numbered candidates) we could have found a smaller one. Also, in some
runs Hypothesis ends up finding a slightly smaller election but with
four candidates instead of three.

We can check to make sure that these really do give different results:

```
>>> v.irv_winner(distinct)
1

>>> v.plurality_winner(distinct)
0
```

There are a lot of other interesting properties of voting systems to
explore, but this is an article about Hypothesis rather than one about
voting, so I'll stop here. However the intersted reader might want to
try to build on this to:

1. Find an election which has a [Condorcet Cycle](https://en.wikipedia.org/wiki/Voting_paradox)
2. Find elections in which the majority prefers the plurality winner to
   the IRV winner and vice versa.
3. Use @given rather than find and write some tests verifying some of
   [the classic properties of election systems](https://en.wikipedia.org/wiki/Voting_system#Evaluating_voting_systems_using_criteria).

And the reader who isn't that interested in voting systems might still
want to think about how this could be useful in other areas: Development
is often a constant series of small experiments and, while testing is
often a good way to perform them, sometimes you just have a more
exploratory "I wonder if...?" question to answer, and it can be
extremely helpful to be able to bring Hypothesis to bear there too.
