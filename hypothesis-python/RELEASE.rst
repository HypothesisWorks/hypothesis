RELEASE_TYPE: patch

If a test uses :func:`~hypothesis.strategies.sampled_from` on a sequence of
strategies, and raises a ``TypeError``, we now :pep:`add a note <678>` asking
whether you meant to use :func:`~hypothesis.strategies.one_of`.

Thanks to Vince Reuter for suggesting and implementing this hint!
