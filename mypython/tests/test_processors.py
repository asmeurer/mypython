from pyflakes.messages import UndefinedName

from ..processors import get_pyflakes_warnings

def test_get_pyflakes_warnings():
    warnings = get_pyflakes_warnings("""\
a + b
""")
    assert len(warnings) == 2
    assert warnings[0][:2] == (0, 0)
    assert warnings[1][:2] == (0, 4)

    assert warnings[0][2] == "undeined name 'a'"
    assert warnings[1][2] == "undeined name 'b'"

    assert isinstance(warnings[0][3], UndefinedName)
    assert isinstance(warnings[1][3], UndefinedName)
