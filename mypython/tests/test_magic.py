import re
import textwrap

from .test_mypython import _test_output, _test_globals
from ..magic import sympy_start

def test_time():
    _globals = _test_globals.copy()
    assert _test_output('import time\n', _globals=_globals) == ('\n', '')
    out, err = _test_output('%time time.sleep(1)\n', _globals=_globals)
    assert re.match(r'Total time: [\d\.]+ s\nNone\n\n', out)
    assert not err

    _globals = _test_globals.copy()
    out, err = _test_output('%time 1 + 1\n', _globals=_globals)
    assert re.match(r'Total time: [\d\.]+ [µu]s\n2\n\n', out), repr(out)
    assert not err


def test_timeit():
    # Each timeit takes ~10 seconds, so only one test here :)
    _globals = _test_globals.copy()
    assert _test_output('import time\n', _globals=_globals) == ('\n', '')
    # 15 loops is the smallest 2**n - 1 >= 10
    out, err = _test_output('%timeit time.sleep(1)\n', _globals=_globals,
        remove_terminal_sequences=True)
    assert re.match(r"""15 loops, [\.\d]+ s average
Minimum time: [\.\d]+ s
Maximum time: [\.\d]+ s


""", out)
    assert not err

def test_doctest():
    from .. import mypython
    assert mypython.DOCTEST_MODE == False

    try:
        _globals = _test_globals.copy()
        assert _test_output('%doctest\n', _globals=_globals) == ('doctest mode enabled\n', '')
        assert mypython.DOCTEST_MODE
        assert _test_output('%doctest\n', _globals=_globals,
            doctest_mode=True) == ('doctest mode disabled\n\n', '')
        assert not mypython.DOCTEST_MODE
        assert _test_output('%doctest 1\n', _globals=_globals) == ('\n', '%doctest takes no arguments\n')
    finally:
        mypython.DOCTEST_MODE = False


def test_debug():
    from .. import mypython
    assert mypython.DEBUG == False

    try:
        _globals = _test_globals.copy()
        assert _test_output('%debug\n', _globals=_globals) == ('mypython debugging mode enabled\n\n', '')
        assert mypython.DEBUG
        assert _test_output('%debug\n', _globals=_globals) == ('mypython debugging mode disabled\n\n', '')
        assert not mypython.DEBUG
        assert _test_output('%debug 1\n', _globals=_globals) == ('\n', '%debug takes no arguments\n')
    finally:
        mypython.DEBUG = False

def test_sympy():
    _globals = _test_globals.copy()
    assert _test_output('%sympy\n', _globals=_globals) == (textwrap.indent(sympy_start, '    ') + '\n\n', '')
    assert _test_output('%sympy 1\n', _globals=_globals) == ('\n', '%sympy takes no arguments\n')
