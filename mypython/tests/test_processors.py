from pyflakes.messages import UndefinedName, UnusedVariable, DuplicateArgument

from ..processors import get_pyflakes_warnings, SyntaxErrorMessage

def test_get_pyflakes_warnings():
    warnings = get_pyflakes_warnings("""\
a + b
""")
    assert len(warnings) == 2
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 4)

    assert warnings[0][2] == "undefined name 'a'"
    assert warnings[1][2] == "undefined name 'b'"

    assert isinstance(warnings[0][3], UndefinedName)
    assert isinstance(warnings[1][3], UndefinedName)

def test_get_pyflakes_warnings_long_undefined_name():
    warnings = get_pyflakes_warnings("""\
abc + cba
""")
    assert len(warnings) == 6
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 1)
    assert warnings[2][:2] == (0, 2)
    assert warnings[3][:2] == (0, 6)
    assert warnings[4][:2] == (0, 7)
    assert warnings[5][:2] == (0, 8)

    for i in range(3):
        assert warnings[i][2] == "undefined name 'abc'"
    for i in range(3, 6):
        assert warnings[i][2] == "undefined name 'cba'"

    for w in warnings:
        assert isinstance(w[3], UndefinedName)

def test_get_pyflakes_warnings_defined_names():
    warnings = get_pyflakes_warnings("""\
abc + cba
""", frozenset(['cba']))
    assert len(warnings) == 3
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 1)
    assert warnings[2][:2] == (0, 2)

    for i in range(3):
        assert warnings[i][2] == "undefined name 'abc'"

    for w in warnings:
        assert isinstance(w[3], UndefinedName)

def test_get_pyflakes_warnings_long_unused_name():
    warnings = get_pyflakes_warnings("""\
def test():
    abc = 1
""")
    assert len(warnings) == 3
    assert warnings[0][:2] == (1, 4)
    assert warnings[1][:2] == (1, 5)
    assert warnings[2][:2] == (1, 6)

    for i in range(3):
        assert warnings[i][2] == "local variable 'abc' is assigned to but never used"

    for w in warnings:
        assert isinstance(w[3], UnusedVariable)

def test_get_pyflakes_warnings_multiple():
    warnings = get_pyflakes_warnings("""\
def test():
    abc = 1
terst()
""")
    assert len(warnings) == 8
    # Don't depend on the warnings order from pyflakes
    assert {w[:2] for w in warnings} == {(1, 4), (1, 5), (1, 6), (2, 0), (2, 1), (2, 2), (2, 3), (2, 4)}

    for w in warnings:
        if w[0] == 1:
            assert w[2] == "local variable 'abc' is assigned to but never used"
            assert isinstance(w[3], UnusedVariable)
        else:
            assert w[2] == "undefined name 'terst'"
            assert isinstance(w[3], UndefinedName)

def test_get_pyflakes_warnings_syntaxerror_bug():
    # A bug in Python causes the SyntaxError offset to be larger than the
    # length of the string (reproduced in Python 3.6.7).
    code = '''Checker(ast.parse("""
)).messages[0].col'''
    warnings = get_pyflakes_warnings(code)
    # Don't test details because they are incorrect, just make sure the above doesn't crash
    assert warnings
    for w in warnings:
        assert isinstance(w[3], SyntaxErrorMessage)

def test_get_pyflakes_warnings_magic():
    warnings = get_pyflakes_warnings("%debug")
    assert len(warnings) == 0

    warnings = get_pyflakes_warnings("%pudb a + bc")
    assert len(warnings) == 3
    assert warnings[0][:2] == (0, 6)
    assert warnings[1][:2] == (0, 10)
    assert warnings[2][:2] == (0, 11)

    assert warnings[0][2] == "undefined name 'a'"
    assert warnings[1][2] == "undefined name 'bc'"
    assert warnings[2][2] == "undefined name 'bc'"

    for w in warnings:
        assert isinstance(w[3], UndefinedName)

    warnings = get_pyflakes_warnings("%pudb  a + bc")
    assert len(warnings) == 3
    assert warnings[0][:2] == (0, 7)
    assert warnings[1][:2] == (0, 11)
    assert warnings[2][:2] == (0, 12)

    assert warnings[0][2] == "undefined name 'a'"
    assert warnings[1][2] == "undefined name 'bc'"
    assert warnings[2][2] == "undefined name 'bc'"

    for w in warnings:
        assert isinstance(w[3], UndefinedName)

    warnings = get_pyflakes_warnings("%pudb  a +")
    assert len(warnings) == 4
    assert warnings[0][:2] == (0, 7)
    assert warnings[1][:2] == (0, 8)
    assert warnings[2][:2] == (0, 9)
    assert warnings[3][:2] == (0, 10)
    for w in warnings:
        assert w[2] == "SyntaxError: invalid syntax"
        assert isinstance(w[3], SyntaxErrorMessage)
        assert w[3].text == 'a +\n'

    warnings = get_pyflakes_warnings("%pudb \na + bc")
    assert len(warnings) == 3
    assert warnings[0][:2] == (1, 0)
    assert warnings[1][:2] == (1, 4)
    assert warnings[2][:2] == (1, 5)

    assert warnings[0][2] == "undefined name 'a'"
    assert warnings[1][2] == "undefined name 'bc'"
    assert warnings[2][2] == "undefined name 'bc'"

    for w in warnings:
        assert isinstance(w[3], UndefinedName)

    warnings = get_pyflakes_warnings("%pudb \na +")
    assert len(warnings) == 4
    assert warnings[0][:2] == (1, 0)
    assert warnings[1][:2] == (1, 1)
    assert warnings[2][:2] == (1, 2)
    assert warnings[3][:2] == (1, 3)
    for w in warnings:
        assert w[2] == "SyntaxError: invalid syntax"
        assert isinstance(w[3], SyntaxErrorMessage)
        assert w[3].text == 'a +\n'

    warnings = get_pyflakes_warnings("%time\n1_")
    assert len(warnings) == 3
    assert warnings[0][:2] == (1, 0)
    assert warnings[1][:2] == (1, 1)
    assert warnings[2][:2] == (1, 2)
    for w in warnings:
        assert w[2] in [
            "SyntaxError: invalid token",
            "SyntaxError: invalid syntax",
            "SyntaxError: invalid decimal literal",
        ]
        assert isinstance(w[3], SyntaxErrorMessage)
        assert w[3].text in ['1_', '1_\n']

    warnings = get_pyflakes_warnings("%time\nabc")
    assert len(warnings) == 3
    assert warnings[0][:2] == (1, 0)
    assert warnings[1][:2] == (1, 1)
    assert warnings[2][:2] == (1, 2)
    for w in warnings:
        assert w[2] == "undefined name 'abc'"
        assert isinstance(w[3], UndefinedName)

    warnings = get_pyflakes_warnings("%ls mypython/")
    assert warnings == []

def test_get_pyflakes_warnings_help():
    warnings = get_pyflakes_warnings("f?")
    assert len(warnings) == 1
    assert warnings[0][:2] == (0, 0)
    assert warnings[0][2] == "undefined name 'f'"
    assert isinstance(warnings[0][3], UndefinedName)

    warnings = get_pyflakes_warnings("f?", frozenset({"f"}))
    assert warnings == []

    warnings = get_pyflakes_warnings("f??")
    assert len(warnings) == 1
    assert warnings[0][:2] == (0, 0)
    assert warnings[0][2] == "undefined name 'f'"
    assert isinstance(warnings[0][3], UndefinedName)

    warnings = get_pyflakes_warnings("f??", frozenset({"f"}))
    assert warnings == []

    warnings = get_pyflakes_warnings("(a +\nb)?")
    assert len(warnings) == 2
    assert warnings[0][:2] == (0, 1)
    assert warnings[1][:2] == (1, 0)
    assert warnings[0][2] == "undefined name 'a'"
    assert warnings[1][2] == "undefined name 'b'"
    assert isinstance(warnings[0][3], UndefinedName)

    warnings = get_pyflakes_warnings("(a +\nb)?", frozenset({"a", "b"}))
    assert len(warnings) == 0

    warnings = get_pyflakes_warnings("(a +\nb)??")
    assert len(warnings) == 2
    assert warnings[0][:2] == (0, 1)
    assert warnings[1][:2] == (1, 0)
    assert warnings[0][2] == "undefined name 'a'"
    assert warnings[1][2] == "undefined name 'b'"
    assert isinstance(warnings[0][3], UndefinedName)

    warnings = get_pyflakes_warnings("(a +\nb)??", frozenset({"a", "b"}))
    assert len(warnings) == 0

    warnings = get_pyflakes_warnings("f???")
    assert len(warnings) == 5
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 1)
    assert warnings[2][:2] == (0, 2)
    assert warnings[3][:2] == (0, 3)
    assert warnings[4][:2] == (0, 4)
    for w in warnings:
        assert w[2] == "SyntaxError: invalid syntax"
        assert isinstance(w[3], SyntaxErrorMessage)
        assert w[3].text == 'f???\n'

    warnings = get_pyflakes_warnings("(a +\nb)???")
    assert len(warnings) == 6
    assert warnings[0][:2] == (1, 0)
    assert warnings[1][:2] == (1, 1)
    assert warnings[2][:2] == (1, 2)
    assert warnings[3][:2] == (1, 3)
    assert warnings[4][:2] == (1, 4)
    assert warnings[5][:2] == (1, 5)
    for w in warnings:
        assert w[2] == "SyntaxError: invalid syntax"
        assert isinstance(w[3], SyntaxErrorMessage)
        assert w[3].text == 'b)???\n'

def test_get_pyflakes_warnings_syntaxerror():
    warnings = get_pyflakes_warnings("a +")
    assert len(warnings) == 4
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 1)
    assert warnings[2][:2] == (0, 2)
    assert warnings[3][:2] == (0, 3)

    for w in warnings:
        assert w[2] == "SyntaxError: invalid syntax"
        assert isinstance(w[3], SyntaxErrorMessage)
        assert w[3].text == 'a +\n'


def test_get_pyflakes_warnings_syntaxerror_unicode():
    # The SyntaxError for '\U1d400' gives an offset of 0
    warnings = get_pyflakes_warnings(r"'\U1d400'")
    assert len(warnings) == 10
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 1)
    assert warnings[2][:2] == (0, 2)
    assert warnings[3][:2] == (0, 3)
    assert warnings[4][:2] == (0, 4)
    assert warnings[5][:2] == (0, 5)
    assert warnings[6][:2] == (0, 6)
    assert warnings[7][:2] == (0, 7)
    assert warnings[8][:2] == (0, 8)
    assert warnings[9][:2] == (0, 9)

    for w in warnings:
        assert w[2] == "SyntaxError: (unicode error) 'unicodeescape' codec can't decode bytes in position 0-6: truncated \\UXXXXXXXX escape"
        assert isinstance(w[3], SyntaxErrorMessage)
        # text is None prior to Python 3.9
        assert w[3].text in [None, "'\\U1d400'\n"]

def test_get_pyflakes_warnings_syntaxerror_multiline():
    warnings = get_pyflakes_warnings("""\
a
01
""")
    assert len(warnings) == 3
    assert warnings[0][:2] == (1, 0)
    assert warnings[1][:2] == (1, 1)
    assert warnings[2][:2] == (1, 2)

    for w in warnings:
        assert w[2] in [
            "SyntaxError: invalid token",
            "SyntaxError: leading zeros in decimal integer literals are not permitted; use an 0o prefix for octal integers",
            ]
        assert isinstance(w[3], SyntaxErrorMessage)
        # The text is None in Python 3.8. We
        # don't presently use it so it doesn't matter.
        assert w[3].text in ['01', '01\n', None]

def test_get_pyflakes_warnings_other():
    # Make sure the columns fill the whole line for errors that aren't names
    warnings = get_pyflakes_warnings("""\
a = 1
def test(a, a):
    pass
""")
    assert len(warnings) == 15
    for i in range(15):
        assert warnings[i][:2] == (1, i)

    for w in warnings:
        assert w[2] == "duplicate argument 'a' in function definition"
        assert isinstance(w[3], DuplicateArgument)

def test_get_pyflakes_warnings_skip():
    warnings = get_pyflakes_warnings("import stuff")
    assert warnings == []

    warnings = get_pyflakes_warnings("from stuff import *")
    assert warnings == []

    warnings = get_pyflakes_warnings("""\
from stuff import *
a + b
""")
    assert warnings == []
