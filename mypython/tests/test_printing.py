import re

def test_displayhook(check_output):
    # TODO: Add tests for other things.

    out, err = check_output('(1j).conjugate\n')
    assert re.match(r'<built-in method conjugate of complex object at 0x[a-f0-9]+>', out), (out, err)
    assert err == ''

    check_output('%sympy\n')
    out, err = check_output('[1, 2, 3]\n')
    assert out == '[1, 2, 3]\n\n'
    assert err == ''
    out, err = check_output('linear_eq_to_matrix([2*x + y, y + 1], [x, y])\n')
    assert out == '\n⎛⎡2  1⎤  ⎡0 ⎤⎞\n⎜⎢    ⎥, ⎢  ⎥⎟\n⎝⎣0  1⎦  ⎣-1⎦⎠\n\n'
    assert err == ''
    out, err = check_output('linear_eq_to_matrix([2*x + y, y + 1], [x, y])\n', doctest_mode=True)
    assert out == '(Matrix([\n[2, 1],\n[0, 1]]), Matrix([\n[ 0],\n[-1]]))\n'
    assert err == ''

    check_output('class Test:\ndef __repr__(self):\nreturn "a\\nb"\n\n')
    out, err = check_output('Test()\n')
    assert out == '\na\nb\n\n'
    assert err == ''
    out, err = check_output('Test()\n', doctest_mode=True)
    assert out == 'a\nb\n'
    assert err == ''

    out, err = check_output('"a\\nb"\n')
    assert out == "'a\\nb'\n\n"
    assert err == ''

    check_output('a = []\n')
    check_output('a.append(a)\n')
    out, err = check_output('a\n')
    assert out == '[[...]]\n\n'
    assert err == ''
