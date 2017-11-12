import re

from ..mypython import startup
from .test_mypython import _test_output, _test_globals

def test_displayhook():
    # TODO: Add tests for other things.

    out, err = _test_output('(1j).conjugate\n')
    assert re.match(r'<built-in method conjugate of complex object at 0x[a-f0-9]+>', out), (out, err)
    assert err == ''

    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    _test_output('%sympy\n', _globals=_globals, mybuiltins=mybuiltins)
    out, err = _test_output('[1, 2, 3]\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert out == '[1, 2, 3]\n\n'
    assert err == ''
    out, err = _test_output('linear_eq_to_matrix([2*x + y, y + 1], [x, y])\n',
        _globals=_globals, mybuiltins=mybuiltins)
    assert out == '\n⎛⎡2  1⎤  ⎡0 ⎤⎞\n⎜⎢    ⎥, ⎢  ⎥⎟\n⎝⎣0  1⎦  ⎣-1⎦⎠\n\n'
    assert err == ''
    out, err = _test_output('linear_eq_to_matrix([2*x + y, y + 1], [x, y])\n',
        doctest_mode=True, _globals=_globals, mybuiltins=mybuiltins)
    assert out == '(Matrix([\n[2, 1],\n[0, 1]]), Matrix([\n[ 0],\n[-1]]))\n'
    assert err == ''

    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    _test_output('class Test:\ndef __repr__(self):\nreturn "a\\nb"\n\n',
        _globals=_globals, mybuiltins=mybuiltins)
    out, err = _test_output('Test()\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert out == '\na\nb\n\n'
    assert err == ''
    out, err = _test_output('Test()\n', _globals=_globals,
        mybuiltins=mybuiltins, doctest_mode=True)
    assert out == 'a\nb\n'
    assert err == ''

    out, err = _test_output('"a\\nb"\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert out == "'a\\nb'\n\n"
    assert err == ''

    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    _test_output('a = []\n', _globals=_globals, mybuiltins=mybuiltins)
    _test_output('a.append(a)\n', _globals=_globals, mybuiltins=mybuiltins)
    out, err = _test_output('a\n', _globals=_globals, mybuiltins=mybuiltins)
    assert out == '[[...]]\n\n'
    assert err == ''
