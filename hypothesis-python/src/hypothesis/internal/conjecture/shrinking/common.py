def find_integer(f):
    """Finds a (hopefully large) integer such that f(n) is True and f(n + 1) is
    False. f(0) is assumed to be True and will not be checked."""

    if not f(2):
        if f(1):
            return 1
        else:
            return 0

    # Take a bet on needing even numbers.
    if not f(3):
        def adjust(k):
            return 2 + 2 * k
        return adjust(find_integer(lambda k: f(adjust(k))))

    if not f(4):
        return 3

    hi = 5
    while f(hi):
        hi *= 2

    lo = 4
    while lo + 1 < hi:
        mid = (lo + hi) // 2
        if f(mid):
            lo = mid
        else:
            hi = mid
    return lo


def sort_key(buffer):
    return (len(buffer), buffer)
