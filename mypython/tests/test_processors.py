from pyflakes.messages import UndefinedName, UnusedVariable

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

def test_get_pyflakes_warnings_help():
    warnings = get_pyflakes_warnings("f?")
    assert len(warnings) == 0

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
