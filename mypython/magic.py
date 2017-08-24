"""
To define a magic %mymagic, define mymagic_magic(rest), where rest will be the
text after the magic, e.g.,

%mymagic 1

rest will be '1'.

The magic should return the source that gets run, and not execute any code
itself.
"""

import ast
import textwrap

def magic(command):
    """
    You can do magic, you can have anything that you desire
    """
    if '\n' in command and ' ' not in command.splitlines()[0]:
        magic_command, rest = command.split('\n', 1)
    elif not ' ' in command:
        magic_command, rest = command, ''
    else:
        magic_command, rest = command.split(' ', 1)

    if magic_command not in MAGICS:
        return command

    result = MAGICS[magic_command](rest)
    if not result.strip():
        # Magic should return something, so that prompt numbers get
        # incremented
        return 'pass'
    return result

def error(message):
    return """\
import sys as _sys
print(%r, file=_sys.stderr)
del _sys
""" % message

def timeit_magic(rest):
    """
    Run the code many times and display timing statistics.

    The number of times is based on how fast the code runs. It should finish
    within 10-20 seconds.
    """
    if not rest:
        return error('nothing to time')

    return """\
from timeit import Timer as _Timer
from mypython.timeit import timeit_format as _timeit_format, autorange as _autorange
_times = _autorange(_Timer({rest!r}, globals=globals()))
print(_timeit_format(_times, {rest!r}))
del _autorange, _timeit_format, _Timer, _times
""".format(rest=rest)

def time_magic(rest):
    """
    Time the code, running it once.

    The output is also shown.
    """
    if not rest:
        return error('nothing to time')

    return """\
from time import perf_counter as _perf_counter
from mypython import smart_eval as _smart_eval, format_time as _format_time
import sys as _sys
_time = _perf_counter()
res = _smart_eval({rest!r}, globals(), locals())
_time = _perf_counter() - _time
print("Total time:", _format_time(_time))
del _time, _format_time, _perf_counter, _smart_eval, _sys
res
""".format(rest=rest)

def doctest_magic(rest):
    """
    Enable/disable doctest mode.

    Doctest mode tries to emulate the output of a regular Python prompt as
    much as possible, for copy-pasting purposes.

    A known issue is that soft-wrapped code shows a ... (this is an issue with
    upstream prompt-toolkit).
    """
    if rest:
        return error('%doctest takes no arguments')

    return """\
from mypython import mypython as _mypython

_mypython.DOCTEST_MODE ^= True

if _mypython.DOCTEST_MODE:
    print("doctest mode enabled")
else:
    print("doctest mode disabled")
del _mypython
"""

def debug_magic(rest):
    """
    Enable/disable debug mode

    In debug mode, tracebacks are not truncated to prevent showing code in
    mypython itself.
    """
    if rest:
        return error('%debug takes no arguments')

    return """\
from mypython import mypython as _mypython
_mypython.DEBUG ^= True

if _mypython.DEBUG:
    print("mypython debugging mode enabled")
else:
    print("mypython debugging mode disabled")
del _mypython
"""

sympy_start = """\
import sympy
from sympy import *
x, y, z, t = symbols('x y z t')
k, m, n = symbols('k m n', integer=True)
f, g, h = symbols('f g h', cls=Function)"""

def sympy_magic(rest):
    """
    Import SymPy names and common symbols.

    This the mypython version of sympy.init_session(). Note that SymPy pretty
    printing is always enabled in mypython.
    """
    if rest:
        return error('%sympy takes no arguments')

    return """\
print(%r)
%s
""" % (textwrap.indent(sympy_start, '    '), sympy_start)

isympy_magic = sympy_magic

def pudb_magic(rest):
    """
    Debug the code with PuDB.
    """
    p = ast.parse(rest)
    has_expr = bool(p.body and isinstance(p.body[-1], ast.Expr))

    return """\
from mypython.mypython import smart_eval as _smart_eval
import pudb as _pudb
import bdb as _bdb
import linecache as _linecache

# XXX: Add the prompt number as a mypython builtin
_filename = '<mypython-pudb-%s>' % (max(In, default=0) + 1)

_pudb._get_debugger().breaks.setdefault(_filename, [1])
# Instantiating the Breakpoint class enables the breakpoint. We can't use
# debugger.set_break() because it fails if the file isn't in the linecache.
_bdb.Breakpoint(_filename, 1, temporary=True)
_pudb._get_debugger().set_trace(paused=False)
# TODO: Figure out how to make this work when has_expr=True
if not {has_expr}:
    _pudb._get_debugger().mainpyfile = _filename
    _pudb._get_debugger()._wait_for_mainpyfile = True

try:
    _val = _smart_eval({rest!r}, globals(), locals(), filename=_filename)
finally:
    # Exit PuDB cleanly, without entering mypython code
    _pudb._get_debugger().set_quit()
    del _linecache.cache[_filename]
    del _pudb, _smart_eval, _bdb, _linecache, _filename

locals().pop('_val')
""".format(rest=rest, has_expr=has_expr)

def error_magic(rest):
    """
    Always raise an exception. For testing.
    """
    raise RuntimeError("Error magic")


def echo_magic(rest):
    """
    Echo the argument, for testing.
    """
    return "print(%r)" % rest

MAGICS = {}

for name in dir():
    if name.endswith('_magic'):
        MAGICS['%' + name[:-len('_magic')]] = globals()[name]
