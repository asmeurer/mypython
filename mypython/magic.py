"""
To define a magic %mymagic, define mymagic_magic(rest), where rest will be the
text after the magic, e.g.,

%mymagic 1

rest will be '1'.

The magic should return the source that gets run, and not execute any code
itself.
"""

import textwrap
import ast
import copy

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

    rest = rest.lstrip()
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

def noprompt_magic(rest):
    """
    Enable/disable no-prompt mode
    """
    if rest:
        return error("%noprompt takes no arguments")

    return """\
from mypython import mypython as _mypython
_mypython.NO_PROMPT_MODE ^= True

if _mypython.NO_PROMPT_MODE:
    print("prompts disabled")
else:
    print("prompts enabled")
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

    res = """\
from mypython.mypython import smart_eval as _smart_eval
from mypython.magic import ast_expr_for_pudb as _ast_expr_for_pudb
import pudb as _pudb
import bdb as _bdb
import linecache as _linecache

_filename = '<mypython-pudb-%s>' % PROMPT_NUMBER

_pudb._get_debugger().breaks.setdefault(_filename, [1])
# Instantiating the Breakpoint class enables the breakpoint. We can't use
# debugger.set_break() because it fails if the file isn't in the linecache.
_bdb.Breakpoint(_filename, 1, temporary=True)
_pudb.set_interrupt_handler()
_pudb._get_debugger().set_trace(paused=False)
_pudb._get_debugger().mainpyfile = _filename
_pudb._get_debugger()._wait_for_mainpyfile = True

# smart_eval puts the source in linecache, but pudb via linecache.getlines
# can't tell the difference between an empty source and source that isn't
# there. So this makes just "%pudb" with no arguments show empty source.
_MODULE_SOURCE_CODE = {rest!r}

try:
    _smart_eval({rest!r}, globals(), locals(), filename=_filename, ast_transformer=_ast_expr_for_pudb)
finally:
    # Exit PuDB cleanly, without entering mypython code
    _pudb._get_debugger().set_quit()
    del _linecache.cache[_filename]
    _pudb._get_debugger().mainpyfile = ''
    _pudb._get_debugger()._wait_for_mainpyfile = False
    del _pudb, _smart_eval, _bdb, _linecache, _filename, _MODULE_SOURCE_CODE
""".format(rest=rest)

    if has_expr:
        res += """\
locals().pop('_val')
"""

    return res

def ast_expr_for_pudb(p, name='_val'):
    """
    Transforms ast p into a suitable ast for PuDB.

    Converts any ending expr into an assignment, so that smart_eval()
    evaluates the whole thing with a single exec().

    The final expression, if any, will be assigned to `name`.
    """
    p = copy.deepcopy(p)
    if p.body and isinstance(p.body[-1], ast.Expr):
        expr = p.body.pop()

        a = ast.copy_location(ast.Assign(targets=[ast.Name(id=name, ctx=ast.Store())],
            value=expr.value), expr)
        p.body.append(a)

        ast.fix_missing_locations(p)
    return p

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
