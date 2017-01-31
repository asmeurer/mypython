#!/usr/bin/env python

from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import TerminalFormatter
from pygments import highlight

from prompt_toolkit.buffer import Buffer, AcceptAction
from prompt_toolkit.interface import Application
from prompt_toolkit.shortcuts import run_application, create_prompt_layout
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.styles import style_from_pygments
from prompt_toolkit.history import FileHistory
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.key_binding.bindings.named_commands import accept_line
from prompt_toolkit.keys import Keys
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.filters import Condition
from prompt_toolkit.token import Token

from .multiline import document_is_multiline_python, auto_newline
from .completion import PythonCompleter
from .theme import OneAM

import os
import sys
import inspect
from traceback import format_exc
from textwrap import dedent

def define_custom_keys(manager):
    # XXX: These are a total hack. We should reimplement this manually, or
    # upstream something better.

    @manager.registry.add_binding(Keys.Escape, 'p')
    def previous_history_search(event):
        buffer = event.current_buffer
        prev_enable_history_search = buffer.enable_history_search
        cursor_position = buffer.cursor_position
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
        try:
            buffer.enable_history_search = lambda: True
            buffer.history_forward(count=event.arg)
            # Keep it from moving the cursor to the end of the line
            buffer.cursor_position = cursor_position
        finally:
            buffer.enable_history_search = prev_enable_history_search

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

        multiline = '\n' in text or document_is_multiline_python(event.current_buffer.document)
        if text.replace(' ', '').endswith('\n') or not multiline:
            # XXX: Should we be more careful if the cursor is not at the end?
            accept_line(event)
        else:
            auto_newline(event.current_buffer)

    @manager.registry.add_binding(Keys.Escape, Keys.Enter)
    def insert_newline(event):
        event.current_buffer.newline()


class PythonSyntaxValidator(Validator):
    def validate(self, document):
        text = dedent(document.text)
        if document_is_multiline_python(document):
            return
        if text.endswith('?') and not text.endswith('???'):
            return
        try:
            compile(text, "<None>", 'exec')
        except SyntaxError as e:
            raise ValidationError(message="SyntaxError: %s" % e.args[0], cursor_position=e.offset)

def get_continuation_tokens(cli, width):
    return [(Token, '.' * (width - 1) + ' ')]

prompt_style = {
    Token.In: '#ansigreen bold',
    Token.Space: '#ansigreen bold',
    Token.Bracket: '#ansigreen bold',
    Token.InNumber: '#ansiblue bold',
    Token.Colon: '#ansigreen bold',
    }

def get_prompt_tokens(cli):
    return [
        (Token.In, 'In'),
        (Token.Space, ' '),
        (Token.Bracket, '['),
        (Token.InNumber, str(len(cli.current_buffer.history)+1)),
        (Token.Bracket, ']'),
        (Token.Colon, ':'),
        (Token.Space, ' '),
    ]

def normalize(command, _globals, _locals):
    command = dedent(command)
    if command.endswith('???'):
        # Too many
        return command
    elif command.endswith('??'):
        try:
            source = eval('inspect.getsource(%s)' % command[:-2], _globals,
                {'inspect': inspect, **_locals})
        except Exception as e:
            print("Error: could not get source for '%s': %s" % (command[:-2], e))
        else:
            print(highlight(source, PythonLexer(),
                TerminalFormatter(style=OneAM)))
        return ''
    else:
        return command

def startup(_globals, _locals):
    exec("""
import sys
sys.path.insert(0, '.')
del sys
""", _globals, _locals)

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
            buffer = Buffer(
                enable_history_search=False,
                is_multiline=multiline,
                validator=PythonSyntaxValidator(),
                history=history,
                accept_action=AcceptAction.RETURN_DOCUMENT,
                completer=PythonCompleter(lambda: _globals, lambda: _locals),
                )
            application = Application(
                create_prompt_layout(
                    get_prompt_tokens=get_prompt_tokens,
                    lexer=PygmentsLexer(PythonLexer),
                    multiline=True,
                    get_continuation_tokens=get_continuation_tokens,
                    ),
                buffer=buffer,
                style=style_from_pygments(OneAM, {**prompt_style}),
                key_bindings_registry=manager.registry,
            )
            command = run_application(application, true_color=True)
        except EOFError:
            break
        except KeyboardInterrupt:
            # TODO: Keep it in the history
            print("KeyboardInterrupt")
            continue

        command = normalize(command, _globals, _locals)
        try:
            res = eval(command, _globals, _locals)
        except SyntaxError:
            try:
                res = exec(command, _globals, _locals)
            except BaseException as e:
                # TODO: Don't show syntax error traceback
                # Also, the syntax error is in the frames (run 'a = sys.exc_info()')
                print(highlight(format_exc(), PythonTracebackLexer(), TerminalFormatter(bg='dark')))
        except BaseException as e:
            print(highlight(format_exc(), PythonTracebackLexer(), TerminalFormatter(bg='dark')))
        else:
            print(res)

if __name__ == '__main__':
    main()
