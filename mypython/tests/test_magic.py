import re
import textwrap
import time
import ast

from ..magic import sympy_start, ast_expr_for_pudb

def test_echo(check_output):
    # Test basic magic and magic syntax checking
    out, err = check_output('%echo\n')
    assert out == '\nNone\n\n'
    assert not err

    out, err = check_output('%echo 1\n')
    assert out == '1\nNone\n\n'
    assert not err

    out, err = check_output('%echo  1\n')
    assert out == '1\nNone\n\n'
    assert not err

    # \x1b\n == M-Enter
    out, err = check_output('%echo\x1b\n1\n\n')
    assert out == '1\nNone\n\n'
    assert not err

    out, err = check_output('%echo \x1b\n1\n\n')
    assert out == '1\nNone\n\n'
    assert not err

def test_time(check_output):
    assert check_output('import time\n') == ('\n', '')
    out, err = check_output('%time time.sleep(.1)\n')
    assert re.match(r'Total time: [\d\.]+ ms\nNone\n\n', out)
    assert not err

    out, err = check_output('%time 1 + 1\n')
    assert re.match(r'Total time: [\d\.]+ [µu]s\n2\n\n', out), repr(out)
    assert not err

def test_timeit(check_output):
    # Each timeit takes ~10 seconds, so only one test here :)
    assert check_output('import time\n') == ('\n', '')
    # 15 loops is the smallest 2**n - 1 >= 10
    out, err = check_output('%timeit time.sleep(1)\n')
    assert re.match(r"""15 loops, [\.\d]+ s average
Minimum time: [\.\d]+ s
Maximum time: [\.\d]+ s
""", out)
    assert not err

def test_timeit_max(check_output):
    # Make sure the max number of runs isn't too slow. This should take ~10 seconds.
    t = time.perf_counter()
    out, err = check_output('%timeit pass\n')
    assert time.perf_counter() - t < 20
    assert re.match(r"""4194303 loops, [\.\d]+ ns average
Minimum time: [\.\d]+ [nmµu]?s
Maximum time: [\.\d]+ [nmµu]?s
""", out), out
    assert not err

def test_doctest(check_output):
    from .. import mypython
    assert mypython.DOCTEST_MODE == False

    try:
        assert check_output('%doctest\n') == ('doctest mode enabled\n', '')
        assert mypython.DOCTEST_MODE
        assert check_output('%doctest\n', doctest_mode=True) == ('doctest mode disabled\n\n', '')
        assert not mypython.DOCTEST_MODE
        assert check_output('%doctest 1\n') == ('\n', '%doctest takes no arguments\n')
    finally:
        mypython.DOCTEST_MODE = False


def test_debug(check_output):
    from .. import mypython
    assert mypython.DEBUG == False

    try:
        assert check_output('%debug\n') == ('mypython debugging mode enabled\n\n', '')
        assert mypython.DEBUG
        assert check_output('%debug\n') == ('mypython debugging mode disabled\n\n', '')
        assert not mypython.DEBUG
        assert check_output('%debug 1\n') == ('\n', '%debug takes no arguments\n')
    finally:
        mypython.DEBUG = False

def test_noprompt(check_output):
    from .. import mypython
    assert mypython.NO_PROMPT_MODE == False

    try:
        assert check_output('%noprompt\n') == ('prompts disabled\n\n', '')
        assert mypython.NO_PROMPT_MODE
        assert check_output('%noprompt\n') == ('prompts enabled\n\n', '')
        assert not mypython.DEBUG
        assert check_output('%noprompt 1\n') == ('\n', '%noprompt takes no arguments\n')


        assert check_output('%prompt\n') == ('prompts disabled\n\n', '')
        assert mypython.NO_PROMPT_MODE
        assert check_output('%prompt\n') == ('prompts enabled\n\n', '')
        assert not mypython.DEBUG
        assert check_output('%prompt 1\n') == ('\n', '%noprompt takes no arguments\n')
    finally:
        mypython.NO_PROMPT_MODE = False

def test_sympy(check_output):
    out, err = check_output('%sympy\n')
    assert out == textwrap.indent(sympy_start, '    ') + '\n\n'
    assert err == ''

    out, err = check_output('x + x\n')
    assert out == '2⋅x\n\n'
    assert err == ''

    assert check_output('%sympy 1\n') == ('\n', '%sympy takes no arguments\n')

def test_ast_expr_for_pudb():
    d = {}
    p = ast.parse("""
p = 1
""")
    p1 = ast_expr_for_pudb(p, name='_val')
    assert p1 is not p
    exec(compile(p1, '<test>', 'exec'), d)
    assert d['p'] == 1
    assert '_val' not in d

    d = {}
    p = ast.parse("""
p = 1
p + 1
""")
    p1 = ast_expr_for_pudb(p, name='_val')
    assert p1 is not p
    exec(compile(p1, '<test>', 'exec'), d)
    assert d['p'] == 1
    assert d['_val'] == 2

def test_history(check_output):
    out, err = check_output('%history\n')
    assert out == '\n'
    assert err == ''

def test_pprint(check_output):
    out, err = check_output("%pprint {chr(i): i for i in range(ord('z'), ord('a')-1,-1)}\n")
    assert out == """\
{'z': 122,
 'y': 121,
 'x': 120,
 'w': 119,
 'v': 118,
 'u': 117,
 't': 116,
 's': 115,
 'r': 114,
 'q': 113,
 'p': 112,
 'o': 111,
 'n': 110,
 'm': 109,
 'l': 108,
 'k': 107,
 'j': 106,
 'i': 105,
 'h': 104,
 'g': 103,
 'f': 102,
 'e': 101,
 'd': 100,
 'c': 99,
 'b': 98,
 'a': 97}
None

"""
    assert err == ''
