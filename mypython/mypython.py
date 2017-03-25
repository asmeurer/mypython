#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK
"""
mypython

A Python REPL the way I like it.
"""

# Define globals first so that names from this module don't get included
_default_globals = globals().copy()
_default_globals['__name__'] = '__main__'
_default_locals = _default_globals

import os
import sys
import inspect
import linecache
import random
import ast
import argparse
import traceback
from textwrap import dedent
from pydoc import pager

from pygments.lexers import Python3Lexer, Python3TracebackLexer
from pygments.formatters import TerminalTrueColorFormatter
from pygments import highlight

from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.input import PipeInput
from prompt_toolkit.interface import Application, CommandLineInterface
from prompt_toolkit.shortcuts import (create_prompt_layout, print_tokens,
    create_eventloop, create_output)
from prompt_toolkit.document import Document
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.layout.processors import ConditionalProcessor
from prompt_toolkit.styles import style_from_pygments, style_from_dict
from prompt_toolkit.history import FileHistory
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.filters import Condition, IsDone
from prompt_toolkit.token import Token

import iterm2_tools
import catimg

# This is needed to make matplotlib plots work
from .inputhook import inputhook
from .multiline import (ends_in_multiline_string,
    document_is_multiline_python)
from .completion import PythonCompleter
from .theme import OneAMStyle
from .keys import get_registry
from .processors import MyHighlightMatchingBracketProcessor
from .magic import magic, MAGICS

class MyBuffer(Buffer):
    """
    Subclass of buffer that fixes some broken behavior of Buffer
    """
    def history_backward(self, count=1):
        """
        Move backwards through history.

        Same as Buffer.history_backward except it moves the cursor to the
        end of the first line.
        """
        self._set_history_search()

        # Go back in history.
        found_something = False

        for i in range(self.working_index - 1, -1, -1):
            if self._history_matches(i):
                self.working_index = i
                count -= 1
                found_something = True
            if count == 0:
                break

        # If we move to another entry, move the cursor to the beginning of the
        # first line.
        if found_something:
            self.cursor_position = 0
            self.cursor_position += self.document.get_end_of_line_position()

    def history_forward(self, count=1):
        """
        Move forwards through the history.
        :param count: Amount of items to move forward.

        Same as Buffer.history_forward except it moves the cursor to the end.
        """
        self._set_history_search()

        # Go forward in history.
        found_something = False

        for i in range(self.working_index + 1, len(self._working_lines)):
            if self._history_matches(i):
                self.working_index = i
                count -= 1
                found_something = True
            if count == 0:
                break

        # If we found an entry, move the cursor to the end.
        if found_something:
            self.cursor_position = len(self.text)

def dedent_return_document_handler(cli, buffer):
    dedented_text = dedent(buffer.text).strip()
    buffer.cursor_position -= len(buffer.text) - len(dedented_text)
    buffer.text = dedented_text

    return AcceptAction.RETURN_DOCUMENT.handler(cli, buffer)

class PythonSyntaxValidator(Validator):
    def validate(self, document):
        text = dedent(document.text)
        if ends_in_multiline_string(document):
            return
        if (document_is_multiline_python(document) and
            not text.replace(' ', '').endswith('\n')):
            return
        if text.endswith('?') and not text.endswith('???'):
            return
        if any(text.startswith(i) for i in MAGICS):
            return
        try:
            compile(text, "<None>", 'exec')
        except SyntaxError as e:
            index = document.translate_row_col_to_index(e.lineno - 1,  (e.offset or 1) - 1)
            raise ValidationError(message="SyntaxError: %s" % e.args[0], cursor_position=index)

prompt_style = {
    Token.DoctestIn: "#ansiwhite",
    Token.In: '#ansiwhite',
    Token.InBracket: '#ansiwhite',
    Token.InNumber: '#ansiblue',
    Token.InColon: '#ansiwhite',
    Token.Out: '#ansired',
    Token.OutBracket: '#ansired',
    Token.OutNumber: '#ansiblue',
    Token.OutColon: '#ansired',
    Token.VerticalLine: '#757575', # grey50
    }

style_extra = {
    Token.MatchingBracket.Other:   "bg:#0000ff", # blue
}

# The emoji mess up emacs, so use the escaped forms
emoji = [
    ('\N{SNAKE}', '\N{PERSONAL COMPUTER}'),
    ('\N{INBOX TRAY}', '\N{OUTBOX TRAY}'),
    # iTerm2 doesn't make DARK SUNGLASSES double width
    ('\N{DARK SUNGLASSES} ', '\N{SMILING FACE WITH SUNGLASSES}'),
    ('\N{SUN WITH FACE}', '\N{LAST QUARTER MOON WITH FACE}'),
    ('\N{FULL MOON WITH FACE}', '\N{NEW MOON WITH FACE}'),
]

IN, OUT = random.choice(emoji)

DOCTEST_MODE = False
DEBUG = False

def get_in_prompt_tokens(cli):
    if DOCTEST_MODE:
        return [
            (Token.ZeroWidthEscape, iterm2_tools.BEFORE_PROMPT),
            (Token.DoctestIn, '>>>'),
            (Token.Space, ' '),
            (Token.ZeroWidthEscape, iterm2_tools.AFTER_PROMPT),
            ]
    return [
        (Token.ZeroWidthEscape, iterm2_tools.BEFORE_PROMPT),

        (Token.Emoji, IN*3),
        (Token.InBracket, '['),
        (Token.InNumber, str(cli.prompt_number)),
        (Token.InBracket, ']'),
        (Token.InColon, ':'),
        (Token.Space, ' '),
        (Token.ZeroWidthEscape, iterm2_tools.AFTER_PROMPT),
    ]

def get_continuation_tokens(cli, width):
    if DOCTEST_MODE:
        return [
            (Token.DoctestContinuation, '...'),
            (Token.Space, ' '),
            ]
    return [
        (Token.Clapping, '\N{CLAPPING HANDS SIGN}'*((width - 1)//2)),
        (Token.VerticalLine, '⎢'),
    ]

def get_out_prompt_tokens(cli):
    if DOCTEST_MODE:
        return []
    return [
        (Token.Emoji, OUT*3),
        (Token.OutBracket, '['),
        (Token.OutNumber, str(cli.prompt_number)),
        (Token.OutBracket, ']'),
        (Token.OutColon, ':'),
        (Token.Space, ' '),
    ]

def mypython_file(prompt_number=None):
    if DOCTEST_MODE:
        return "<stdin>"
    if prompt_number is not None:
        return "<mypython-{prompt_number}>".format(prompt_number=prompt_number)
    return "<mypython>"

def getsource(command, _globals, _locals, ret=False):
    """
    Get and show the source for the given code

    Works for code defined interactively.

    If ret=False (default), displays the source in a pager. Otherwise, returns
    the source, or raises an exception (from inspect.getsource()) if it cannot
    be found.

    """
    # Enable getting the source for code defined in the REPL.

    # Even though we add code defined interactively to linecache.cache in
    # smart_eval(), we have to monkey patch linecache.getlines() because it
    # skips files with mtime == None (and even if it weren't None, it would
    # try to os.stat() the file and skip it when that fails). This is a
    # similar pattern as the doctest module.
    def _patched_linecache_getlines(filename, module_globals=None):
        if '__main__' in sys.modules:
            # Classes defined interactively will have their module set to
            # __main__, so getfile looks at this. This will typically be
            # /path/to/bin/mypython.
            __main__file = sys.modules['__main__'].__file__
        else:
            __main__file = None
        if filename in ["<stdin>", __main__file] or filename.startswith("<mypython"):
            return '\n'.join([i for _, i in sorted(_locals['In'].items())] + ['']).splitlines(keepends=True)
        else:
            return linecache._orig_getlines(filename, module_globals)

    try:
        linecache._orig_getlines = linecache.getlines
        linecache.getlines = _patched_linecache_getlines
        try:
            source = eval('inspect.getsource(%s)' % command, _globals,
                {'inspect': inspect, **_locals})
        except TypeError:
            source = eval('inspect.getsource(type(%s))' % command, _globals,
                {'inspect': inspect, **_locals})
    except Exception as e:
        if ret:
            raise
        print("Error: could not get source for '%s': %s" % (command, e), file=sys.stderr)
    else:
        if ret:
            return source
        pager(highlight(source, Python3Lexer(),
            TerminalTrueColorFormatter(style=OneAMStyle)))
    finally:
        linecache.getlines = linecache._orig_getlines
        del linecache._orig_getlines

    return ''

def normalize(command, _globals, _locals):
    command = dedent(command).strip()
    if command.endswith('???'):
        # Too many
        return command
    elif command.endswith('??'):
        return getsource(command[:-2], _globals, _locals)
    elif command.endswith('?'):
        return 'help(%s)' % command[:-1]
    elif command.startswith('%'):
        return magic(command)
    else:
        return command

def mypython_displayhook(value):
    """
    Unlike the default displayhook:

    - doesn't set builtins._ (we do that separately),
    - always prints None,
    - prints a newline before a multiline output, so the out prompt doesn't
      mess up pretty printing,
    - uses sympy.pretty() for SymPy objects.

    """
    if value is NoResult:
        return

    try:
        import sympy
    except ImportError:
        sympy = None

    if sympy and (getattr(value, '__module__', '') or '').startswith('sympy.'):
        res = sympy.pretty(value)
    else:
        res = repr(value)

    if '\n' in res:
        # Print multiline stuff below the out prompt
        print()
    print(res)

def startup(_globals, _locals, quiet=False):
    exec("""
import sys
sys.path.insert(0, '.')
del sys
""", _globals, _locals)

    _locals['In'] = {}
    _locals['Out'] = {}

    if not quiet:
        print_tokens([(Token.Welcome, "Welcome to mypython.\n")])
        image = catimg.get_random_image()
        if image:
            print_tokens([(Token.Welcome, "Here is a cat:\n")])
            iterm2_tools.display_image_file(image)

    sys.displayhook = mypython_displayhook
    sys.excepthook = mypython_excepthook

    try:
        import matplotlib
    except ImportError:
        pass
    else:
        matplotlib.interactive(True)

class NoResult:
    pass

mypython_dir = os.path.dirname(__file__)

def smart_eval(stmt, _globals, _locals, filename=None):
    """
    Automatically exec/eval stmt.

    Returns the result if eval, or NoResult if it was an exec. Or raises if
    the stmt is a syntax error or raises an exception.

    filename should be the filename used for compiling the statement. If
    given, the statement will be saved to the Python linecache, so that it
    appears in tracebacks. Otherwise, a default filename is used and it isn't
    saved to the linecache.

    Note that classes defined with this will have their module set to
    '__main__'.  To change this, set _globals['__name__'] to the desired
    module.
    """
    if filename:
        # Don't show context lines in doctest mode
        if filename != "<stdin>":
            # (size, mtime, lines, fullname)
            linecache.cache[filename] = (len(stmt), None, stmt.splitlines(), filename)
    else:
        filename = mypython_file()

    try:
        code = compile(stmt, filename, 'eval')
        res = eval(code, _globals, _locals)
    except SyntaxError as s:
        p = ast.parse(stmt)
        expr = None
        res = NoResult
        if p.body and isinstance(p.body[-1], ast.Expr):
            expr = p.body.pop()
        code = compile(p, filename, 'exec')
        try:
            exec(code, _globals, _locals)
            if expr:
                code = compile(ast.Expression(expr.value), filename, 'eval')
                res = eval(code, _globals, _locals)
        except BaseException as e:
            # TODO: Should this use sys.excepthook instead?

            # Remove the SyntaxError from the tracebacks. Note, the
            # SyntaxError is still in the frames (run 'a =
            # sys.exc_info()'). I don't know if this will be an issue,
            # but until it does, I'll leave it in for debugging (and
            # also I don't know how to remove it).
            if DEBUG:
                raise e

            c = e
            while c.__context__ != s:
                c = c.__context__
            c.__suppress_context__ = True
            raise e

    return res

def post_command(*, command, res, _globals, _locals, cli):
    prompt_number = cli.prompt_number
    _locals['In'][prompt_number] = command
    if res is not NoResult:
        print_tokens(get_out_prompt_tokens(cli),
            style=style_from_pygments(OneAMStyle, {**prompt_style}))

        _locals['Out'][prompt_number] = res
        _locals['_%s' % prompt_number] = res
        _locals['_'], _locals['__'], _locals['___'] = res, _locals.get('_'), _locals.get('__')

        if not (DOCTEST_MODE and res is None):
            sys.displayhook(res)

    if command.strip():
        cli.prompt_number += 1

def get_eventloop():
    return create_eventloop(inputhook)

def get_cli(*, history, _globals, _locals, registry, _input=None, output=None, eventloop=None):
    def is_buffer_multiline():
        return document_is_multiline_python(buffer.document)

    multiline = Condition(is_buffer_multiline)

    output = output or create_output(true_color=True)

    # This is based on prompt_toolkit.shortcuts.prompt() and
    # prompt_toolkit.shortcuts.create_prompt_application().
    buffer = MyBuffer(
        enable_history_search=False,
        is_multiline=multiline,
        validator=PythonSyntaxValidator(),
        history=history,
        accept_action=AcceptAction(dedent_return_document_handler),
        completer=PythonCompleter(lambda: _globals, lambda: _locals),
        # Needs to be False until
        # https://github.com/jonathanslenders/python-prompt-toolkit/issues/472
        # is fixed.
        complete_while_typing=False,
        )
    application = Application(
        create_prompt_layout(
            get_prompt_tokens=get_in_prompt_tokens,
            lexer=PygmentsLexer(Python3Lexer),
            multiline=True,
            get_continuation_tokens=get_continuation_tokens,
            display_completions_in_columns=True,
            extra_input_processors=[
                ConditionalProcessor(
                    # 20000 is ~most characters that fit on screen even with
                    # really small font
                    processor=MyHighlightMatchingBracketProcessor(max_cursor_distance=20000),
                    filter=~IsDone()
                )],
            ),
        buffer=buffer,
        style=style_from_pygments(OneAMStyle, {**prompt_style, **style_extra}),
        key_bindings_registry=registry,
    )
    # This is based on run_application
    cli = CommandLineInterface(
        application=application,
        eventloop=eventloop or get_eventloop(),
        output=output,
        input=_input,
    )
    cli.prompt_number = 1
    return cli

def format_exception(etype, value, tb, limit=None, chain=True):
    """
    Like traceback.format_exception() except lines from mypython are not returned.
    """
    if DEBUG:
        return traceback.format_exception(etype, value, tb, limit=limit, chain=chain)

    l = []

    for i in traceback.format_exception(etype, value, tb, limit=limit, chain=chain):
        if i.startswith('  File "{}'.format(mypython_dir)):
            continue
        l.append(i)

    return l

def format_exc(limit=None, chain=True):
    """
    Like traceback.format_exc() except lines from mypython are not returned.
    """
    return "".join(format_exception(*sys.exc_info(), limit=limit, chain=chain))

def mypython_excepthook(etype, value, tb):
    try:
        tb_str = "".join(format_exception(etype, value, tb))
        print(highlight(tb_str, Python3TracebackLexer(),
            TerminalTrueColorFormatter(style=OneAMStyle)),
            file=sys.stderr, end='')
    except RecursionError:
        sys.__excepthook__(*sys.exc_info())
        print_tokens([(Token.Newline, '\n'), (Token.InternalError,
            "Warning: RecursionError from mypython_excepthook")],
            style=style_from_dict({Token.InternalError: "#ansired"}),
            file=sys.stderr)

def execute_command(command, cli, *, _globals=None, _locals=None):
    _globals = _globals or _default_globals
    _locals = _locals or _default_locals

    command = normalize(command, _globals, _locals)
    with iterm2_tools.Output() as o:
        if not command:
            if not DOCTEST_MODE:
                print()
            return
        try:
            res = smart_eval(command, _globals, _locals, filename=mypython_file(cli.prompt_number))
            post_command(command=command, res=res, _globals=_globals,
                _locals=_locals, cli=cli)
        except BaseException as e:
            sys.excepthook(*sys.exc_info())
            o.set_command_status(1)
        if not DOCTEST_MODE:
            print()

def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument("--cmd", "-c", metavar="CMD", action="store",
        help="""Execute the given command at startup.""")
    parser.add_argument("--quiet", "-q", action="store_true", help="""Don't
        print the startup messages.""")
    parser.add_argument("--doctest-mode", "-d", action="store_true",
        help="""Enable doctest mode. Mimics the default Python prompt.""")

    try:
        import argcomplete
        argcomplete.autocomplete(parser)
    except ImportError:
        pass
    args = parser.parse_args()

    if args.doctest_mode:
        global DOCTEST_MODE
        DOCTEST_MODE = True

    os.makedirs(os.path.expanduser('~/.mypython/history'), exist_ok=True)
    try:
        tty_name = os.path.basename(os.ttyname(sys.stdout.fileno()))
    except OSError:
        tty_name = 'unknown'

    history = FileHistory(os.path.expanduser('~/.mypython/history/%s_history'
        % tty_name))

    registry = get_registry()

    startup(_default_globals, _default_locals, quiet=args.quiet)
    prompt_number = 1
    while True:
        if prompt_number == 1 and args.cmd:
            _input = PipeInput()
            _input.send_text(args.cmd + '\n')
        else:
            _input = None

        cli = get_cli(history=history, _locals=_default_locals, _globals=_default_globals,
                registry=registry, _input=_input)
        cli.prompt_number = prompt_number
        try:
            # Replace stdout.
            patch_context = cli.patch_stdout_context(raw=True)
            with patch_context:
                result = cli.run()
            if isinstance(result, Document):  # Backwards-compatibility.
                command = result.text
            else:
                command = result
        except KeyboardInterrupt:
            # TODO: Keep it in the history
            print("KeyboardInterrupt", file=sys.stderr)
            continue
        except EOFError:
            break

        execute_command(command, cli)
        prompt_number = cli.prompt_number

if __name__ == '__main__':
    main()
