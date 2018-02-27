import re
import textwrap
import time
import ast

from ..mypython import startup

from .test_mypython import _test_output, _test_globals
from ..magic import sympy_start, ast_expr_for_pudb

def test_echo():
    # Test basic magic and magic syntax checking
    out, err = _test_output('%echo\n')
    assert out == '\nNone\n\n'
    assert not err

    out, err = _test_output('%echo 1\n')
    assert out == '1\nNone\n\n'
    assert not err

    out, err = _test_output('%echo  1\n')
    assert out == '1\nNone\n\n'
    assert not err

    # \x1b\n == M-Enter
    out, err = _test_output('%echo\x1b\n1\n\n')
    assert out == '1\nNone\n\n'
    assert not err

    out, err = _test_output('%echo \x1b\n1\n\n')
    assert out == '1\nNone\n\n'
    assert not err

def test_time():
    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    assert _test_output('import time\n', _globals=_globals,
        mybuiltins=mybuiltins) == ('\n', '')
    out, err = _test_output('%time time.sleep(.1)\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert re.match(r'Total time: [\d\.]+ ms\nNone\n\n', out)
    assert not err

    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    out, err = _test_output('%time 1 + 1\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert re.match(r'Total time: [\d\.]+ [µu]s\n2\n\n', out), repr(out)
    assert not err

def test_timeit():
    # Each timeit takes ~10 seconds, so only one test here :)
    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    assert _test_output('import time\n', _globals=_globals, mybuiltins=mybuiltins) == ('\n', '')
    # 15 loops is the smallest 2**n - 1 >= 10
    out, err = _test_output('%timeit time.sleep(1)\n', _globals=_globals,
        mybuiltins=mybuiltins, remove_terminal_sequences=True)
    assert re.match(r"""15 loops, [\.\d]+ s average
Minimum time: [\.\d]+ s
Maximum time: [\.\d]+ s


""", out)
    assert not err

def test_timeit_max():
    # Make sure the max number of runs isn't too slow. This should take ~10 seconds.
    t = time.perf_counter()
    out, err = _test_output('%timeit pass\n', remove_terminal_sequences=True)
    assert time.perf_counter() - t < 20
    assert re.match(r"""4194303 loops, [\.\d]+ ns average
Minimum time: [\.\d]+ ns
Maximum time: [\.\d]+ [nmµu]s


""", out), out
    assert not err

def test_doctest():
    from .. import mypython
    assert mypython.DOCTEST_MODE == False

    try:
        _globals = _test_globals.copy()
        mybuiltins = startup(_globals, _globals, quiet=True)
        assert _test_output('%doctest\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('doctest mode enabled\n', '')
        assert mypython.DOCTEST_MODE
        assert _test_output('%doctest\n', _globals=_globals,
            mybuiltins=mybuiltins, doctest_mode=True) == ('doctest mode disabled\n\n', '')
        assert not mypython.DOCTEST_MODE
        assert _test_output('%doctest 1\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('\n', '%doctest takes no arguments\n')
    finally:
        mypython.DOCTEST_MODE = False


def test_debug():
    from .. import mypython
    assert mypython.DEBUG == False

    try:
        _globals = _test_globals.copy()
        mybuiltins = startup(_globals, _globals, quiet=True)
        assert _test_output('%debug\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('mypython debugging mode enabled\n\n', '')
        assert mypython.DEBUG
        assert _test_output('%debug\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('mypython debugging mode disabled\n\n', '')
        assert not mypython.DEBUG
        assert _test_output('%debug 1\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('\n', '%debug takes no arguments\n')
    finally:
        mypython.DEBUG = False

def test_noprompt():
    from .. import mypython
    assert mypython.NO_PROMPT_MODE == False

    try:
        _globals = _test_globals.copy()
        mybuiltins = startup(_globals, _globals, quiet=True)
        assert _test_output('%noprompt\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('prompts disabled\n\n', '')
        assert mypython.NO_PROMPT_MODE
        assert _test_output('%noprompt\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('prompts enabled\n\n', '')
        assert not mypython.DEBUG
        assert _test_output('%noprompt 1\n', _globals=_globals,
            mybuiltins=mybuiltins) == ('\n', '%noprompt takes no arguments\n')
    finally:
        mypython.NO_PROMPT_MODE = False

def test_sympy():
    _globals = _test_globals.copy()
    mybuiltins = startup(_globals, _globals, quiet=True)
    out, err = _test_output('%sympy\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert out == textwrap.indent(sympy_start, '    ') + '\n\n'
    assert err == ''

    out, err = _test_output('x + x\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert out == '2⋅x\n\n'
    assert err == ''

    assert _test_output('%sympy 1\n') == ('\n', '%sympy takes no arguments\n')

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
