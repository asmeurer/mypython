"""Mypython: a Python REPL the way I like it"""

# Define globals first so that names from this module don't get included
_default_globals = globals().copy()
import builtins
_default_globals['__name__'] = '__main__'
del _default_globals['__file__']
_default_globals['__spec__'] = None
_default_globals['__package__'] = None
_default_globals['__cached__'] = None
_default_globals['__builtins__'] = builtins
_default_locals = _default_globals

import os
import sys
import inspect
import linecache
import random
import ast
import traceback
import textwrap
from io import StringIO
from textwrap import dedent
from pydoc import pager, Helper
from collections import deque

from pygments.lexers import Python3Lexer, Python3TracebackLexer
from pygments.formatters import TerminalTrueColorFormatter
from pygments.token import Token
from pygments import highlight

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.input.vt100 import PipeInput
from prompt_toolkit.shortcuts import print_formatted_text, Prompt, CompleteStyle
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.layout.processors import ConditionalProcessor
from prompt_toolkit.styles import (style_from_pygments_cls,
    style_from_pygments_dict, merge_styles)
from prompt_toolkit.history import FileHistory
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.filters import Condition, IsDone
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.enums import DEFAULT_BUFFER

import iterm2_tools

from .multiline import document_is_multiline_python
from .completion import PythonCompleter
from .theme import OneAMStyle, MyPython3Lexer, emoji
from .keys import get_key_bindings, LEADING_WHITESPACE
from .processors import MyHighlightMatchingBracketProcessor
from .magic import magic, MAGICS
from .printing import mypython_displayhook

class MyBuffer(Buffer):
    """
    Subclass of buffer that fixes some broken behavior of Buffer
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._multiline_history_search_index = None

    def delete_before_cursor(self, count=1):
        self.multiline_history_search_index = None
        return super().delete_before_cursor(count)

    @property
    def multiline_history_search_index(self):
        if self._multiline_history_search_index is None:
            self._multiline_history_search_index = len(self._working_lines) - 1
        return self._multiline_history_search_index

    @multiline_history_search_index.setter
    def multiline_history_search_index(self, value):
        self._multiline_history_search_index = value

    def _history(self, direction, count=1, history_search=False):
        assert direction in ['forward', 'backward'], direction

        # self._set_history_search()
        if history_search:
            if self.history_search_text is None:
                self.history_search_text = self.document.current_line_before_cursor.lstrip()
        else:
            self.history_search_text = None
        indent = LEADING_WHITESPACE.match(self.document.current_line_before_cursor)
        current_line_indent = indent.group(1) if indent else ''

        found_something = False

        index = self.multiline_history_search_index if history_search else self.working_index

        r = range(index - 1, -1, -1) if direction == 'backward' else range(index + 1, len(self._working_lines))
        for i in r:
            if self._history_matches(i):
                if history_search:
                    # XXX: Put this in the multiline_history_search_index
                    # setter?
                    match_text = textwrap.indent(self._working_lines[i], current_line_indent)
                    if '\n' in self.document.text_before_cursor:
                        lines_before_cursor, line_before_cursor = self.document.text_before_cursor.rsplit('\n', 1)
                        if match_text == line_before_cursor + self.document.text[self.cursor_position:]:
                            continue
                        self.text = lines_before_cursor + '\n' + match_text
                    else:
                        if match_text == self.text:
                            continue
                        self.text = match_text
                    self.multiline_history_search_index = i
                else:
                    self.working_index = i
                count -= 1
                found_something = True
            if count == 0:
                break
        else:
            # Can't access cli.output.bell()
            print("\a", end='')
            sys.stdout.flush()

        # If we move to another entry, move the cursor to the end of the
        # first line.
        if found_something and not history_search:
            if direction == 'backward':
                self.cursor_position = 0
                self.cursor_position += self.document.get_end_of_line_position()
            else:
                self.cursor_position = len(self.text)


    def history_backward(self, count=1, history_search=False):
        """
        Move backwards through history.

        Based on Buffer.history_backward, but it moves the cursor to the
        beginning of the first line, and supports multiline history search.
        """
        return self._history('backward', count=count, history_search=history_search)

    def history_forward(self, count=1, history_search=False):
        """
        Move forwards through the history.
        :param count: Amount of items to move forward.

        Same as Buffer.history_forward except it moves the cursor to the end,
        and supports multiline history search.

        """
        return self._history('forward', count=count, history_search=history_search)

def on_text_insert(buf):
    buf.multiline_history_search_index = None

def dedent_return_document_handler(cli, buffer):
    dedented_text = dedent(buffer.text).strip()
    buffer.cursor_position -= len(buffer.text) - len(dedented_text)
    buffer.text = dedented_text

    return AcceptAction.RETURN_DOCUMENT.handler(cli, buffer)

def validate_text(text):
    """
    Return None if text is valid, or raise SyntaxError.
    """
    if any(text == i + '?' for i in MAGICS):
        return
    if text.endswith('?') and not text.endswith('???'):
        text = text.rstrip('?')
    elif any(text.startswith(i) for i in MAGICS):
        if ' ' not in text.splitlines()[0]:
            text = ''
        else:
            magic, text = text.split(' ', 1)
            text = text.lstrip()

    compile(text, "<None>", 'exec')

class PythonSyntaxValidator(Validator):
    def validate(self, document):
        text = dedent(document.text)
        try:
            validate_text(text)
        except SyntaxError as e:
            offset = len(text.split('\n')[0]) - len(text.split('\n')[0])
            index = document.translate_row_col_to_index(e.lineno - 1, (e.offset or 1) - 1 + offset)
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
    Token.MatchingBracket.Cursor:    "bg:#0000ff", # blue
    Token.MatchingBracket.Other:     "bg:#0000ff", # blue
    Token.MismatchingBracket.Cursor: "bg:#ff0000", # red
    Token.MismatchingBracket.Other:  "bg:#ff0000", # red
}

NO_PROMPT_MODE = False
DOCTEST_MODE = False
DEBUG = False

def mypython_file(prompt_number=None):
    if DOCTEST_MODE:
        return "<stdin>"
    if prompt_number is not None:
        return "<mypython-{prompt_number}>".format(prompt_number=prompt_number)
    return "<mypython>"

def normalized_filename(filename):
    __main__file = sys.modules['__main__'].__file__
    if filename == __main__file:
        filename == 'Unknown'
    if filename.startswith("<mypython-"):
        filename = "mypython input #%s" % filename[10:-1]
    return filename

def red(text):
    return "\033[31m%s\033[0m" % text

def blue(text):
    return "\033[34m%s\033[0m" % text

def myhelp(item):
    help_io = StringIO()
    helper = Helper(output=help_io)

    def _name(obj):
        try:
            name = obj.__qualname__
        except AttributeError:
            try:
                name = obj.__name__
            except AttributeError:
                name = None
        return name

    try:
        s = inspect.signature(item)
    except (TypeError, ValueError):
        pass
    else:
        name = _name(item)
        if name:
            # highlight adds a newline to the end of the string
            # (https://bitbucket.org/birkenfeld/pygments-main/issues/1403/)
            help_io.write("{heading}: {name}{s}".format(heading=
                red("Signature"), name=name, s=highlight(str(s), Python3Lexer(), TerminalTrueColorFormatter(style=OneAMStyle))))

    try:
        filename = normalized_filename(inspect.getfile(item))
    except TypeError:
        pass
    else:
        help_io.write("{heading}: {filename}\n".format(heading=red("File"), filename=filename))

    item_type_name = _name(type(item))
    if item_type_name:
        heading = red("Metaclass") if inspect.isclass(item) else red("Type")
        help_io.write("{heading}: {type_name}\n".format(heading=heading, type_name=item_type_name))

    if inspect.isclass(item):
        try:
            mro = item.__mro__
        except AttributeError:
            pass
        else:
            help_io.write("{heading}: {mro}\n".format(heading=red("MRO"), mro=mro))

    if help_io.tell():
        help_io.write("\n")

    # Don't import numpy if it isn't imported already
    if 'numpy' in sys.modules:
        import numpy
        if isinstance(item, numpy.ufunc):
            help_io.write(blue("NumPy Ufunc help\n----------------\n\n"))
            numpy.info(item, output=help_io)
            help_io.write("\n")

    help_io.write(blue("Pydoc help\n----------\n\n"))

    helper.help(item)

    return pager(help_io.getvalue())


def getsource(command, _globals, _locals, ret=False, include_info=True):
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
            return '\n'.join([i for _, i in sorted(_locals['_PROMPT'].In.items())] + ['']).splitlines(keepends=True)
        else:
            return linecache._orig_getlines(filename, module_globals)

    try:
        linecache._orig_getlines = linecache.getlines
        linecache.getlines = _patched_linecache_getlines
        try:
            sourcelines, lineno = eval('inspect.getsourcelines(%s)' % command, _globals,
                {'inspect': inspect, **_locals})
            if include_info:
                filename = eval('inspect.getfile(%s)' % command, _globals,
                    {'inspect': inspect, **_locals})
        except TypeError:
            sourcelines, lineno = eval('inspect.getsourcelines(type(%s))' % command, _globals,
                {'inspect': inspect, **_locals})
            if include_info:
                filename = eval('inspect.getfile(type(%s))' % command, _globals,
                    {'inspect': inspect, **_locals})
    except Exception as e:
        if ret:
            raise
        print("Error: could not get source for '%s': %s" % (command, e), file=sys.stderr)
    else:
        source = ''.join(sourcelines)
        if include_info:
            filename = normalized_filename(filename)
            info = dedent("""
            # File: {filename}
            # Line: {lineno}

            """.format(filename=filename, lineno=lineno))
            source = info + source
        if ret:
            return source
        pager(highlight(source, Python3Lexer(),
            TerminalTrueColorFormatter(style=OneAMStyle)))
    finally:
        linecache.getlines = linecache._orig_getlines
        del linecache._orig_getlines

def normalize(command, _globals, _locals):
    command = dedent(command).strip()
    if command.endswith('???'):
        # Too many
        return command
    elif command.endswith('??'):
        return """\
from mypython import getsource as _getsource
try:
    _getsource(%r, globals(), locals())
finally:
    del _getsource
""" % command[:-2]
    elif command.endswith('?'):
        if command.startswith('%'):
            return """\
from mypython import myhelp as _myhelp
from mypython.magic import MAGICS as _MAGICS
try:
    _myhelp(_MAGICS[%r])
finally:
    del _myhelp, _MAGICS
""" % command[:-1]
        return """\
from mypython import myhelp as _myhelp
try:
    _myhelp(%s)
finally:
    del _myhelp
""" % command[:-1]
    elif command.startswith('%'):
        return magic(command)
    else:
        return command


class NoResult:
    pass

mypython_dir = os.path.dirname(__file__)

def smart_eval(stmt, _globals, _locals, filename=None, *, ast_transformer=None):
    """
    Automatically exec/eval stmt.

    Returns the result if eval, or NoResult if it was an exec. Or raises if
    the stmt is a syntax error or raises an exception.

    filename should be the filename used for compiling the statement. If
    given, the statement will be saved to the Python linecache, so that it
    appears in tracebacks. Otherwise, a default filename is used and it isn't
    saved to the linecache. To work properly, "fake" filenames should start
    with < and end with >, and be unique for each stmt.

    Note that classes defined with this will have their module set to
    '__main__'.  To change this, set _globals['__name__'] to the desired
    module.

    To transform the ast before compiling it, pass in an ast_transformer
    function. It should take in an ast and return a new ast.
    """
    if filename:
        # Don't show context lines in doctest mode
        if filename != "<stdin>":
            # (size, mtime, lines, fullname)
            linecache.cache[filename] = (len(stmt), None, stmt.splitlines(keepends=True), filename)
    else:
        filename = mypython_file()

    p = ast.parse(stmt)
    if ast_transformer:
        p = ast_transformer(p)
    expr = None
    res = NoResult
    if p.body and isinstance(p.body[-1], ast.Expr):
        expr = p.body.pop()
    code = compile(p, filename, 'exec')
    exec(code, _globals, _locals)
    if expr:
        code = compile(ast.Expression(expr.value), filename, 'eval')
        res = eval(code, _globals, _locals)

    return res

def post_command(*, command, res, _globals, _locals, prompt):
    PROMPT_NUMBER = prompt.prompt_number
    prompt.In[PROMPT_NUMBER] = command
    builtins = prompt.builtins

    if res is not NoResult:
        print_formatted_text(prompt.get_out_prompt(),
            style=merge_styles([style_from_pygments_cls(OneAMStyle),
                style_from_pygments_dict({**prompt_style})]))

        prompt.Out[PROMPT_NUMBER] = res
        builtins['_%s' % PROMPT_NUMBER] = res
        builtins['_'], builtins['__'], builtins['___'] = res, builtins.get('_'), builtins.get('__')

        if not (DOCTEST_MODE and res is None):
            sys.displayhook(res)

    if command.strip():
        prompt.prompt_number += 1

    # Allow the mutable builtin names to be redefined without mypython resetting them. If
    # they are del-ed, they will be restored to the builtin versions.
    # Immutable names exempt from this because we cannot detect if they are
    # redefined.
    # TODO: Handle this better?
    for name in prompt.builtins:
        if name in ['_', '__', '___', 'PROMPT_NUMBER', '_PROMPT']:
            _locals[name] = prompt.builtins[name]
        else:
            _locals.setdefault(name, builtins[name])


class MyPrompt(Prompt):
    def __init__(self, *args, _globals, _locals, message=None,
        key_bindings=None, history_file=None, IN_OUT=None, builtins=None,
        quiet=False, cat=False, **kwargs):

        if not history_file:
            try:
                tty_name = os.path.basename(os.ttyname(sys.stdout.fileno()))
            except OSError:
                tty_name = 'unknown'
            history_file = '~/.mypython/history/%s_history' % tty_name

        history_file = os.path.expanduser(history_file)

        os.makedirs(os.path.dirname(history_file), exist_ok=True)

        kwargs.setdefault('history', FileHistory(history_file))
        kwargs.setdefault('key_bindings', key_bindings or get_key_bindings())
        kwargs.setdefault('message', message or self.get_in_prompt)
        kwargs.setdefault('lexer', PygmentsLexer(MyPython3Lexer))
        kwargs.setdefault('multiline', True)
        kwargs.setdefault('prompt_continuation', self.get_prompt_continuation)
        kwargs.setdefault('complete_style', CompleteStyle.MULTI_COLUMN)
        kwargs.setdefault('input_processors', [
            ConditionalProcessor(
                # 20000 is ~most characters that fit on screen even with
                # really small font
                processor=MyHighlightMatchingBracketProcessor(max_cursor_distance=20000),
                filter=~IsDone()
                )])
        kwargs.setdefault('search_ignore_case', True)
        kwargs.setdefault('style', merge_styles([style_from_pygments_cls(OneAMStyle),
                style_from_pygments_dict({**prompt_style, **style_extra})]))

        self._globals = _globals
        self._locals = _locals

        self.startup(builtins=builtins)
        if not IN_OUT:
            IN_OUT = random.choice(emoji)
        self.IN, self.OUT = IN_OUT
        self.builtins = builtins

        self.__init__(*args, **kwargs)

    def startup(self, builtins=None):
        exec("""
import sys
sys.path.insert(0, '.')
del sys
    """, self._globals, self._locals)

        builtins = builtins or {}

        self.In = builtins['In'] = {}
        self.Out = builtins['Out'] = {}
        self.prompt_number = builtins['PROMPT_NUMBER'] = 1

        self._locals.update(builtins)

        if not self.quiet:
            print_formatted_text(PygmentsTokens([(Token.Welcome, "Welcome to mypython.\n\n")]))
            if self.cat:
                try:
                    import catimg
                except ImportError:
                    image = None
                else:
                    image = catimg.get_random_image()
                if image:
                    print_formatted_text(PygmentsTokens([(Token.Welcome, "Here is a cat:\n")]))
                    iterm2_tools.display_image_file(image)
                    print()

        sys.displayhook = mypython_displayhook
        sys.excepthook = mypython_excepthook

        try:
            import matplotlib
        except ImportError:
            pass
        else:
            matplotlib.interactive(True)

        self.builtins = builtins

    def get_in_prompt(self):
        if NO_PROMPT_MODE:
            return PygmentsTokens([
                (Token.ZeroWidthEscape, iterm2_tools.BEFORE_PROMPT),
                (Token.ZeroWidthEscape, iterm2_tools.AFTER_PROMPT),
                ])
        if DOCTEST_MODE:
            return PygmentsTokens([
                (Token.ZeroWidthEscape, iterm2_tools.BEFORE_PROMPT),
                (Token.DoctestIn, '>>>'),
                (Token.Space, ' '),
                (Token.ZeroWidthEscape, iterm2_tools.AFTER_PROMPT),
                ])
        return PygmentsTokens([
            (Token.ZeroWidthEscape, iterm2_tools.BEFORE_PROMPT),

            (Token.Emoji, self.IN*3),
            (Token.InBracket, '['),
            (Token.InNumber, str(self.prompt_number)),
            (Token.InBracket, ']'),
            (Token.InColon, ':'),
            (Token.Space, ' '),
            (Token.ZeroWidthEscape, iterm2_tools.AFTER_PROMPT),
        ])

    def get_prompt_continuation(self, width):
        if DOCTEST_MODE:
            return PygmentsTokens([
                (Token.DoctestContinuation, '...'),
                (Token.Space, ' '),
                ])
        return PygmentsTokens([
            (Token.Clapping, '\N{CLAPPING HANDS SIGN}'*((width - 1)//2)),
            (Token.VerticalLine, '⎢'),
        ])

    def get_out_prompt(self):
        if DOCTEST_MODE or NO_PROMPT_MODE:
            return PygmentsTokens([])
        return PygmentsTokens([
            (Token.Emoji, self.OUT*3),
            (Token.OutBracket, '['),
            (Token.OutNumber, str(self.prompt_number)),
            (Token.OutBracket, ']'),
            (Token.OutColon, ':'),
            (Token.Space, ' '),
        ])

    def _create_default_buffer(self):

        def is_buffer_multiline():
            return document_is_multiline_python(buffer.document)

        multiline = Condition(is_buffer_multiline)
        buffer = MyBuffer(
            name=DEFAULT_BUFFER,
            enable_history_search=False,
            is_multiline=multiline,
            validator=PythonSyntaxValidator(),
            history=self.history,
            # accept_action=AcceptAction(dedent_return_document_handler),
            completer=PythonCompleter(lambda: self._globals, lambda: self._locals),
            # Needs to be False until
            # https://github.com/jonathanslenders/python-prompt-toolkit/issues/472
            # is fixed.
            complete_while_typing=False,
            on_text_insert=on_text_insert,
            tempfile_suffix='.py',
        )
        return buffer

class MyTracebackException(traceback.TracebackException):
    def __init__(self, exc_type, exc_value, exc_traceback, *,
        remove_mypython=True, **kwargs):

        super().__init__(exc_type, exc_value, exc_traceback, **kwargs)

        new_stack = traceback.StackSummary()
        mypython_error = None
        for frame in self.stack[:]:
            if frame.filename.startswith(mypython_dir):
                if mypython_error is False:
                    mypython_error = True
            elif frame.filename.startswith('<mypython'):
                new_stack.append(frame)
            else:
                new_stack.append(frame)
                if not mypython_error:
                    mypython_error = False

        if mypython_error is None and frame.filename.startswith(mypython_dir):
            mypython_error = True

        if remove_mypython and not mypython_error:
            self.stack = new_stack

        self.mypython_error = mypython_error


def mypython_excepthook(etype, value, tb):
    try:
        tbexception = MyTracebackException(type(value), value, tb, limit=None,
            remove_mypython=not DEBUG)

        tb_str = "".join(list(tbexception.format(chain=True)))
        print(highlight(tb_str, Python3TracebackLexer(),
            TerminalTrueColorFormatter(style=OneAMStyle)),
            file=sys.stderr, end='')
        if tbexception.mypython_error:
            print_formatted_text(PygmentsTokens([(Token.Newline, '\n'), (Token.InternalError,
                "!!!!!! ERROR from mypython !!!!!!"), (Token.Newline, '\n\n')]),
                style=style_from_pygments_dict({Token.InternalError: "#ansired"}),
                file=sys.stderr)

    except RecursionError:
        sys.__excepthook__(*sys.exc_info())
        print_formatted_text(PygmentsTokens([(Token.Newline, '\n'), (Token.InternalError,
            "Warning: RecursionError from mypython_excepthook")]),
            style=style_from_pygments_dict({Token.InternalError: "#ansired"}),
            file=sys.stderr)

def execute_command(command, prompt, *, _globals=None, _locals=None):
    _globals = _globals or _default_globals
    _locals = _locals or _default_locals

    with iterm2_tools.Output() as o:
        try:
            command = normalize(command, _globals, _locals)

            if not command:
                if not DOCTEST_MODE:
                    print()
                return

            res = smart_eval(command, _globals, _locals, filename=mypython_file(prompt.prompt_number))
            post_command(command=command, res=res, _globals=_globals,
                _locals=_locals, prompt=prompt)
        except SystemExit:
            raise
        except BaseException as e:
            sys.excepthook(*sys.exc_info())
            o.set_command_status(1)
        if not DOCTEST_MODE:
            print()


CMD_QUEUE = deque()

def run_shell(_globals=_default_globals, _locals=_default_locals, *,
    quiet=False, cmd=None, history_file=None, cat=False, _exit=False):

    if cmd:
        if isinstance(cmd, str):
            cmd = [cmd]
        else:
            for c in cmd:
                # \x1b\n = Meta-Enter
                # \x1b[ag = Shift-Enter (iTerm2 settings)
                CMD_QUEUE.append(c.replace('\n', '\x1b\n') + '\x1b[ag')

    prompt = MyPrompt(_globals=_globals, _locals=_locals, quiet=quiet,
        cat=cat, history_file=history_file)

    prompt.startup()

    while True:
        try:
            # _history = history

            if CMD_QUEUE:
                _input = PipeInput()
                _input.send_text(CMD_QUEUE.popleft())
                if cmd:
                    # TODO
                    # Don't store --cmd in the history
                    _history = cmd = None
            elif _exit:
                break
            else:
                _input = None

            # Replace stdout.
            # patch_context = cli.patch_stdout_context(raw=True)
            # with patch_context:
            command = prompt.prompt()
        except KeyboardInterrupt:
            # TODO: Keep it in the history
            print("KeyboardInterrupt", file=sys.stderr)
            continue
        except (EOFError, SystemExit):
            break
        except:
            sys.excepthook(*sys.exc_info())

        execute_command(command, prompt, _globals=_globals, _locals=_locals)
