"""
To define a magic %mymagic, define mymagic_magic(rest), where rest will be the
text after the magic, e.g.,

%mymagic 1

rest will be '1'.

The magic should return the source that gets run, and not execute any code
itself.
"""

import threading
import textwrap
import ast
import copy
import shlex
import subprocess
import platform
import os
import re
import sys
from functools import wraps

from prompt_toolkit.history import FileHistory

from . import ai

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
        return 'pass\n'
    if not result.endswith('\n'):
        result = result + '\n'
    return result

NON_PYTHON_MAGICS = []

def nonpython(f):
    @wraps(f)
    def inner(rest):
        return f(rest)
    NON_PYTHON_MAGICS.append('%' + f.__name__[:-len('_magic')])
    return inner

MAGIC_COMPLETIONS = {}

def completions(get_completions):
    """
    Use like

    @completions(lambda: ['a', 'b', 'c'])
    def x_magic(rest):
        ...
    """
    def wrapper(f):
        MAGIC_COMPLETIONS['%' + f.__name__[:-len('_magic')]] = get_completions
        return f
    return wrapper

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

_mypython.doctest_mode()

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

prompt_magic = noprompt_magic

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

def get_history(file=None, this_history=None):
    """
    Return the list of history strings corresponding to a given history
    file

    `this_history` should be _PROMPT.history for the current prompt session.
    If the history file corresponds to this session, the live history list
    will be returned. Otherwise, a static list is returned and this function
    will need to be called again to update the strings.

    Strings are ordered with the most recent history items first.

    """
    history = None
    history_base = "~/.mypython/history/"
    tty_name = os.path.basename(os.ttyname(sys.stdout.fileno()))
    if file is None:
        file = tty_name
    if isinstance(file, int):
        file = "%03i" % file
    if isinstance(file, str):
        for f in [file,
                  os.path.join(history_base, file),
                  os.path.join(history_base, "%s_history" % file),
                  os.path.join(history_base, "%s_history" % re.sub(r"\d+", file, tty_name))
                  ]:
            f = os.path.expanduser(f)
            if this_history and f == this_history.filename:
                return this_history._loaded_strings
            if os.path.exists(f):
                file = FileHistory(f)
                break
    if isinstance(file, FileHistory):
        history = file

    if history is None:
        raise RuntimeError("Could not find history from %s" % file)
    return list(history.load_history_strings())

def history_magic(rest):
    return """\
import pydoc as _pydoc
import pygments as _pygments
from mypython.theme import OneAMStyle as _OneAMStyle, MyPython3Lexer as _MyPython3Lexer
from mypython.mypython import blue as _blue, underline as _underline
_pydoc.pipepager('\\n'.join(_pygments.highlight(i, _MyPython3Lexer(), _pygments.formatters.TerminalTrueColorFormatter(style=_OneAMStyle))+_underline(_blue(' '*80)) for i in _PROMPT.history.get_strings()), 'less +G')
del _pydoc, _pygments, _OneAMStyle, _MyPython3Lexer, _blue, _underline
"""

def pprint_magic(rest):
    """
    Pretty print the result
    """
    if not rest.strip():
        return error("nothing to pretty print")

    return """\
from pprint import pprint as _pprint
_pprint({rest}, sort_dicts=False)
""".format(rest=rest)

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

def pyinstrument_magic(rest):
    """
    Profile the code with pyinstrument.
    """
    res = """\
from pyinstrument import Profiler as _Profiler

try:
    with _Profiler() as _profiler:
        pass
{rest}

    _profiler.open_in_browser()
finally:
    del _profiler, _Profiler
"""
    return res.format(rest=textwrap.indent(rest, ' '*8))

def line_profiler_magic(rest):
    """
    Profile the code with line_profiler
    """
    res = f"""
from mypython.line_profiler import run_line_profiler as _run_line_profiler
_line_profile_result = _run_line_profiler({rest!r}, globals(), locals())
print(_line_profile_result)
del _run_line_profiler, _line_profile_result
"""
    return res

@nonpython
def ls_magic(rest):
    """
    Run ls.
    """
    if "Linux" in platform.platform():
        ls=['ls', '--color', '-AFlha']
    else:
        ls = ['ls', '-AGFlha']

    subprocess.run(ls + shlex.split(rest.strip()))
    return ''

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

def timings_magic(rest):
    """
    Show timings for the code.

    Note that the prompt itself has an overhead of about 90 microseconds.

    """
    rest = rest.strip()
    if rest:
        try:
            rest = int(rest)
        except ValueError:
            return error("argument must be an integer")

    return f"""\
from mypython.timeit import format_time as _format_time
if {rest!r}:
    print(_format_time(TIMINGS[int({rest})]))
else:
    for _i in range(1, PROMPT_NUMBER):
        print(f'{{_i:2d}} {{_format_time(TIMINGS[_i])}}')
"""

def get_ai_models():
    yield from list(ai.MODELS)
    for model in ai.MODELS:
        yield from ai.MODELS[model]['model_aliases']

@completions(get_ai_models)
@nonpython
def model_magic(rest):
    """
    Set the current model for the completion engine.
    """
    rest = rest.strip()
    if not rest:
        return error("no model specified: available models are %s" % ', '.join(ai.MODELS))

    for model in ai.MODELS:
        if rest == model:
            break
        if rest in ai.MODELS[model]['model_aliases']:
            rest = model
            break
    else:
        return error("model not found")

    ai.CURRENT_MODEL = rest
    # Asynchronously Load the model into memory
    threading.Thread(target=ai.load_model, args=(rest,), daemon=True).start()
    return ""

MAGICS = {}

for name in dir():
    if name.endswith('_magic'):
        MAGICS['%' + name[:-len('_magic')]] = globals()[name]
