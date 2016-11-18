from hypothesis.strategies import text,lists,fixed_dictionaries, just, characters, sampled_from, composite, integers
from hypothesis.searchstrategy.strings import StringStrategy
from hypothesis.searchstrategy import SearchStrategy
from itertools import chain
import string
import sys
import re

#TODO: handle using future
if sys.version_info[0] >= 3:
    unichr = chr
    xrange = range

#don't use very long examples
limit = 15

def categories(category):
    if category == "category_digit":
        return string.digits
    elif category == "category_not_digit":
        return string.ascii_letters + string.punctuation
    elif category == "category_space":
        return string.whitespace
    elif category == "category_not_space":
        return string.printable.strip()
    elif category == "category_word":
        return string.ascii_letters + string.digits + '_'
    elif category == "category_not_word":
        return ''.join(set(string.printable)
                        .difference(string.ascii_letters +
                                    string.digits + '_'))

def handle_negated_state(state):
    opcode, value = state
    if opcode == "range":
        return [unichr(val) for val in xrange(value[0],value[1])]
    elif opcode == "literal":
        return [unichr(value)]
    elif opcode == "category":
        return categories(value)
    else:
        print "Unknown opcode in handle_negated_state",opcode

@composite
def handle_state(draw,state):
    opcode, value = state
    if opcode == "literal":
        return draw(just(unichr(value)))
    elif opcode == "not_literal":
        return draw(characters(blacklist_characters=unichr(value)))
    elif opcode == "at":
        return draw(just(""))
    elif opcode == "in":
        if draw(handle_state(value[0]))[0] is False:
            candidates = list(chain(*(handle_negated_state(v) for v in value[1:])))
            return draw(characters(blacklist_characters=candidates))
        else:
            candidates = list(chain(*(draw(handle_state(v)) for v in value)))
            return draw(sampled_from(candidates))
    elif opcode == "any":
        return draw(characters())
    elif opcode == "range":
        return unichr(draw(integers(min_value=value[0],max_value=value[1])))
    elif opcode == "category":
        return draw(text(alphabet=categories(value),max_size=1,min_size=1))
    elif opcode == "branch":
        return u''.join(draw(handle_state(i)) for i in draw(sampled_from(value[1])))
    elif opcode == "subpattern":
        return u''.join(draw(handle_state(i)) for i in value[1])
    elif opcode == "assert":
        pass
    elif opcode == "assert_not":
        return just("")
    elif opcode == "groupref":
        pass
    elif opcode == "min_repeat":
        start_range, end_range, val = value
        end_range = min((end_range, limit))
        return u"".join(draw(lists(handle_state(v),min_size=start_range,max_size=end_range)) for v in val)
    elif opcode == "max_repeat":
        start_range, end_range, val = value
        end_range = min((end_range, limit))
        res = []
        for v in val:
            res.append(u"".join(draw(lists(handle_state(v),min_size=start_range,max_size=end_range))))
        return u"".join(res)
    elif opcode == "negate":
        return draw(just([False]))
    else:
        print "Unknown opcode",opcode, value


@composite
def regex(draw,pattern):
    """
    Strategy for generating strings conforming to a regular expression

    Not supported are backreferences,
    maybe there are problems with locales
    """
    parsed = re.sre_parse.parse(pattern)
    print parsed
    return u"".join(draw(handle_state(state)) for state in parsed)
