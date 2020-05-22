
from lark import Lark
from hypothesis.extra.lark import from_lark
import hypothesis

grammar_source = r"""

prog: stmt+
stmt: typ id "=" num ";"
typ: "int"
   | "float"
id: /[a-z]+/
num: /[0-9]+/

%ignore /[ ]+/

"""

grammar = Lark(grammar_source, start='prog')

@hypothesis.given(from_lark(grammar, start='prog'))
def test_lark_token_concatenation(prog):
    print('===========')
    print(prog)
    print('----')
    p = grammar.parse(prog)
    print(p)
    print('===========')


if __name__ == "__main__":
    test_lark_token_concatenation()
