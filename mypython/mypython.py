#!/usr/bin/env python

from pygments.lexers import Python3Lexer, Python3TracebackLexer
from pygments.formatters import TerminalTrueColorFormatter
from pygments import highlight

from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.interface import Application, CommandLineInterface
from prompt_toolkit.shortcuts import (create_prompt_layout, print_tokens,
    create_eventloop, create_output)
from prompt_toolkit.document import Document
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.layout.processors import (ConditionalProcessor,
    HighlightMatchingBracketProcessor)
from prompt_toolkit.styles import style_from_pygments
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.key_binding.bindings.named_commands import accept_line
from prompt_toolkit.keys import Keys
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.filters import Condition, IsDone
from prompt_toolkit.token import Token

import iterm2_tools
import catimg

# This is needed to make matplotlib plots work
from IPython.terminal.pt_inputhooks.osx import inputhook

from .multiline import (ends_in_multiline_string,
    document_is_multiline_python, auto_newline,
    TabShouldInsertWhitespaceFilter)
from .completion import PythonCompleter
from .theme import OneAMStyle

import os
import sys
import inspect
import re
import linecache
import random
from traceback import format_exc
from textwrap import dedent
from pydoc import pager

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

def define_custom_keys(manager):

    # XXX: These are a total hack. We should reimplement this manually, or
    # upstream something better.
    @manager.registry.add_binding(Keys.Escape, 'p')
    def previous_history_search(event):
        buffer = event.current_buffer
        prev_enable_history_search = buffer.enable_history_search
        cursor_position = buffer.cursor_position
        buffer.history_search_text = buffer.text[:cursor_position]
        try:
            buffer.enable_history_search = lambda: True
            buffer.history_backward(count=event.arg)
            # Keep it from moving the cursor to the end of the line
            buffer.cursor_position = cursor_position
        finally:
            buffer.enable_history_search = prev_enable_history_search

    @manager.registry.add_binding(Keys.Escape, 'P')
    def forward_history_search(event):
        buffer = event.current_buffer
        prev_enable_history_search = buffer.enable_history_search
        cursor_position = buffer.cursor_position
        buffer.history_search_text = buffer.text[:cursor_position]
        try:
            buffer.enable_history_search = lambda: True
            buffer.history_forward(count=event.arg)
            # Keep it from moving the cursor to the end of the line
            buffer.cursor_position = cursor_position
        finally:
            buffer.enable_history_search = prev_enable_history_search

    @manager.registry.add_binding(Keys.ControlP)
    def history_backward(event):
        """
        Always backwards in history, even in multiline.
        """
        event.current_buffer.history_backward(event.arg)

    @manager.registry.add_binding(Keys.ControlN)
    def history_forward(event):
        """
        Always forwards in history, even in multiline.
        """
        event.current_buffer.history_forward(event.arg)

    @manager.registry.add_binding(Keys.Escape, '<')
    def beginning(event):
        """
        Move to the beginning
        """
        event.current_buffer.cursor_position = 0

    @manager.registry.add_binding(Keys.Escape, '>')
    def end(event):
        """
        Move to the beginning
        """
        event.current_buffer.cursor_position = len(event.current_buffer.text)

    # Document.start_of_paragraph/end_of_paragraph don't treat multiple blank
    # lines correctly.
    BLANK_LINES = re.compile(r'\S *(\n *\n)')
    @manager.registry.add_binding(Keys.Escape, '}')
    def forward_paragraph(event):
        """
        Move forward one paragraph of text
        """
        text = event.current_buffer.text
        cursor_position = event.current_buffer.cursor_position
        for m in BLANK_LINES.finditer(text):
            if m.start(0) > cursor_position:
                event.current_buffer.cursor_position = m.start(1)+1
                return
        event.current_buffer.cursor_position = len(text)


    @manager.registry.add_binding(Keys.Escape, '{')
    def back_paragraph(event):
        """
        Move back one paragraph of text
        """
        text = event.current_buffer.text
        cursor_position = event.current_buffer.cursor_position

        for m in BLANK_LINES.finditer(text[::-1]):
            if m.start(0) > len(text) - cursor_position:
                event.current_buffer.cursor_position = len(text) - m.end(1) + 1
                return
        event.current_buffer.cursor_position = 0

    @manager.registry.add_binding(Keys.Left)
    def left_multiline(event):
        """
        Left that wraps around in multiline.
        """
        if event.current_buffer.cursor_position - event.arg >= 0:
            event.current_buffer.cursor_position -= event.arg

    @manager.registry.add_binding(Keys.Right)
    def right_multiline(event):
        """
        Right that wraps around in multiline.
        """
        if event.current_buffer.cursor_position + event.arg <= len(event.current_buffer.text):
            event.current_buffer.cursor_position += event.arg

    @manager.registry.add_binding(Keys.ControlD)
    def exit(event):
        raise EOFError("Control-D")


    is_returnable = Condition(
        lambda cli: cli.current_buffer.accept_action.is_returnable)

    @manager.registry.add_binding(Keys.Enter, filter=is_returnable)
    def multiline_enter(event):
        """
        When not in multiline, execute. When in multiline, add a newline,
        unless there is already blank line.
        """
        text = event.current_buffer.text
        document = event.current_buffer.document
        multiline = '\n' in text or document_is_multiline_python(document)
        if ends_in_multiline_string(document):
            auto_newline(event.current_buffer)
        elif not multiline:
            accept_line(event)
        elif event.current_buffer.cursor_position == len(text) and text.replace(' ', '').endswith('\n'):
            accept_line(event)
        else:
            auto_newline(event.current_buffer)

    @manager.registry.add_binding(Keys.Escape, Keys.Enter)
    def insert_newline(event):
        event.current_buffer.newline()

    @manager.registry.add_binding(Keys.Tab, filter=TabShouldInsertWhitespaceFilter())
    def indent(event):
        """
        When tab should insert whitespace, do that instead of completion.
        """
        # Text before cursor on the line must be whitespace because of the
        # TabShouldInsertWhitespaceFilter.
        before_cursor = event.cli.current_buffer.document.current_line_before_cursor
        event.cli.current_buffer.insert_text(' '*(4 - len(before_cursor)%4))

    LEADING_WHITESPACE = re.compile(r'( *)[^ ]?')
    @manager.registry.add_binding(Keys.Escape, 'm')
    def back_to_indentation(event):
        """
        Move back to the beginning of the line, ignoring whitespace.
        """
        current_line = event.cli.current_buffer.document.current_line
        before_cursor = event.cli.current_buffer.document.current_line_before_cursor
        indent = LEADING_WHITESPACE.search(current_line)
        if indent:
            event.cli.current_buffer.cursor_position -= len(before_cursor) - indent.end(1)

def dedent_return_document_handler(cli, buffer):
    dedented_text = dedent(buffer.text)
    buffer.cursor_position -= len(buffer.text) - len(dedented_text)
    buffer.text = dedent(buffer.text)

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
        try:
            compile(text, "<None>", 'exec')
        except SyntaxError as e:
            raise ValidationError(message="SyntaxError: %s" % e.args[0], cursor_position=e.offset)

def get_continuation_tokens(cli, width):
    return [
        (Token.Clapping, '\N{CLAPPING HANDS SIGN}'*((width - 1)//2)),
        (Token.VerticalLine, '⎢'),
    ]

prompt_style = {
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

def get_in_prompt_tokens(cli):
    return [
        (Token.ZeroWidthEscape, iterm2_tools.BEFORE_PROMPT),

        (Token.Emoji, IN*3),
        (Token.InBracket, '['),
        (Token.InNumber, str(len(cli.current_buffer.history)+1)),
        (Token.InBracket, ']'),
        (Token.InColon, ':'),
        (Token.Space, ' '),
        (Token.ZeroWidthEscape, iterm2_tools.AFTER_PROMPT),
    ]

def get_out_prompt_tokens(cli):
    return [
        (Token.Emoji, OUT*3),
        (Token.OutBracket, '['),
        (Token.OutNumber, str(len(cli.current_buffer.history))),
        (Token.OutBracket, ']'),
        (Token.OutColon, ':'),
        (Token.Space, ' '),
    ]

def getsource(command, _globals, _locals):
    # Enable getting the source for code defined in the REPL. Uses a similar
    # pattern as the doctest module.
    def _patched_linecache_getlines(filename, module_globals=None):
        if filename == "<mypython>":
            return '\n'.join(i for _, i in sorted(_locals['In'].items())).splitlines(keepends=True)
        else:
            return linecache._orig_getlines(filename, module_globals)

    try:
        linecache._orig_getlines = linecache.getlines
        linecache.getlines = _patched_linecache_getlines
        try:
            source = eval('inspect.getsource(%s)' % command[:-2], _globals,
                {'inspect': inspect, **_locals})
        except TypeError:
            source = eval('inspect.getsource(type(%s))' % command[:-2], _globals,
                {'inspect': inspect, **_locals})
    except Exception as e:
        print("Error: could not get source for '%s': %s" % (command[:-2], e))
    else:
        pager(highlight(source, Python3Lexer(),
            TerminalTrueColorFormatter(style=OneAMStyle)))
    finally:
        linecache.getlines = linecache._orig_getlines
        del linecache._orig_getlines

    return ''

def normalize(command, _globals, _locals):
    command = dedent(command)
    if command.endswith('???'):
        # Too many
        return command
    elif command.endswith('??'):
        return getsource(command, _globals, _locals)
    elif command.endswith('?'):
        return 'help(%s)' % command[:-1]
    else:
        return command

def startup(_globals, _locals):
    exec("""
import sys
sys.path.insert(0, '.')
del sys
""", _globals, _locals)

    _locals['In'] = {}
    _locals['Out'] = {}

    print("Welcome to mypython.")
    image = catimg.get_random_image()
    if image:
        print("Here is a cat:")
        iterm2_tools.display_image_file(image)

    try:
        import matplotlib
    except ImportError:
        pass
    else:
        matplotlib.interactive(True)

class NoResult:
    pass

def post_command(*, command, res, _globals, _locals, prompt_number, cli):
    _locals['In'][prompt_number] = command
    if res is not NoResult:
        print_tokens(get_out_prompt_tokens(cli),
            style=style_from_pygments(OneAMStyle, {**prompt_style}))

        _locals['Out'][prompt_number] = res
        _locals['_%s' % prompt_number] = res
        _locals['_'], _locals['__'], _locals['___'] = res, _locals.get('_'), _locals.get('__')

        print(repr(res))

def main():
    _globals = globals().copy()
    _locals = _globals
    os.makedirs(os.path.expanduser('~/.mypython/history'), exist_ok=True)
    try:
        tty_name = os.path.basename(os.ttyname(sys.stdout.fileno()))
    except OSError:
        tty_name = 'unknown'

    history = FileHistory(os.path.expanduser('~/.mypython/history/%s_history'
        % tty_name))

    manager = KeyBindingManager.for_prompt()
    define_custom_keys(manager)

    startup(_globals, _locals)

    while True:
        try:
            def is_buffer_multiline():
                return document_is_multiline_python(buffer.document)

            multiline = Condition(is_buffer_multiline)

            # This is based on prompt_toolkit.shortcuts.prompt() and
            # prompt_toolkit.shortcuts.create_prompt_application().
            buffer = MyBuffer(
                enable_history_search=False,
                is_multiline=multiline,
                validator=PythonSyntaxValidator(),
                history=history,
                accept_action=AcceptAction(dedent_return_document_handler),
                completer=PythonCompleter(lambda: _globals, lambda: _locals),
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
                            processor=HighlightMatchingBracketProcessor(max_cursor_distance=20000),
                            filter=~IsDone()
                        )],
                    ),
                buffer=buffer,
                style=style_from_pygments(OneAMStyle, {**prompt_style}),
                key_bindings_registry=manager.registry,
            )
            eventloop = create_eventloop(inputhook)
            # This is based on run_application
            cli = CommandLineInterface(
                application=application,
                eventloop=eventloop,
                output=create_output(true_color=True))
            # Replace stdout.
            patch_context = cli.patch_stdout_context(raw=True)
            with patch_context:
                result = cli.run()
            if isinstance(result, Document):  # Backwards-compatibility.
                command = result.text
            else:
                command = result

        except EOFError:
            break
        except KeyboardInterrupt:
            # TODO: Keep it in the history
            print("KeyboardInterrupt")
            continue

        command = normalize(command, _globals, _locals)
        with iterm2_tools.Output() as o:
            prompt_number = len(buffer.history)
            try:
                code = compile(command, '<mypython>', 'eval')
                res = eval(code, _globals, _locals)
            except SyntaxError:
                try:
                    code = compile(command, '<mypython>', 'exec')
                    res = exec(code, _globals, _locals)
                except BaseException as e:
                    # TODO: Don't show syntax error traceback
                    # Also, the syntax error is in the frames (run 'a = sys.exc_info()')
                    print(highlight(format_exc(), Python3TracebackLexer(),
                        TerminalTrueColorFormatter(style=OneAMStyle)))
                    o.set_command_status(1)
                else:
                    post_command(command=command, res=NoResult, _globals=_globals,
                        _locals=_locals, prompt_number=prompt_number, cli=cli)
            except BaseException as e:
                print(highlight(format_exc(), Python3TracebackLexer(), TerminalTrueColorFormatter(style=OneAMStyle)))
                o.set_command_status(1)
            else:
                post_command(command=command, res=res, _globals=_globals,
                    _locals=_locals, prompt_number=prompt_number, cli=cli)
            print()

if __name__ == '__main__':
    main()
