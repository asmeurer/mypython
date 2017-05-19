"""
To define a magic %mymagic, define mymagic_magic(rest), where rest will be the
text after the magic, e.g.,

%mymagic 1

rest will be '1'.

The magic should return the source that gets run, and not execute any code
itself.
"""

import textwrap

def magic(command):
    """
    You can do magic, you can have anything that you desire
    """
    if not ' ' in command:
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
    if not rest:
        return error('nothing to time')

    return """\
from timeit import Timer as _Timer
from mypython.timeit import time_format as _time_format, autorange as _autorange
_times = _autorange(_Timer({rest!r}, globals=globals()))
print(_time_format(_times))
del _autorange, _time_format, _Timer, _times
""".format(rest=rest)

def time_magic(rest):
    if not rest:
        return error('nothing to time')

    return """\
from time import perf_counter as _perf_counter
from IPython.core.magics.execution import _format_time
from mypython import smart_eval as _smart_eval
import sys as _sys
_time = _perf_counter()
res = _smart_eval({rest!r}, globals(), locals())
_time = _perf_counter() - _time
print("Total time:", _format_time(_time))
_sys.displayhook(res)
del _time, _format_time, _perf_counter, _smart_eval, _sys
""".format(rest=rest)

def doctest_magic(rest):
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
    if rest:
        return error('%sympy takes no arguments')

    return """
print(%r)
%s
""" % (textwrap.indent(sympy_start, '    '), sympy_start)

isympy_magic = sympy_magic

MAGICS = {}

for name in dir():
    if name.endswith('_magic'):
        MAGICS['%' + name[:-len('_magic')]] = globals()[name]
