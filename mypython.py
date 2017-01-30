#!/usr/bin/env python

from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import TerminalFormatter
from pygments.styles.monokai import MonokaiStyle
from pygments import highlight

from prompt_toolkit.buffer import Buffer
from prompt_toolkit.interface import Application
from prompt_toolkit.shortcuts import run_application, create_prompt_layout
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.styles import style_from_pygments
from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.keys import Keys
from prompt_toolkit.validation import Validator, ValidationError
from prompt_toolkit.filters import Condition

from multiline import document_is_multiline_python

from traceback import format_exc

def define_custom_keys(manager):
    @manager.registry.add_binding(Keys.Escape, 'p')
    def previous_history_search(event):
        try:
            prev_enable_history_search = event.current_buffer.enable_history_search
            event.current_buffer.enable_history_search = lambda: True
            event.current_buffer.history_backward(count=event.arg)
        finally:
            event.current_buffer.enable_history_search = prev_enable_history_search

    @manager.registry.add_binding(Keys.Escape, 'P')
    def forward_history_search(event):
        try:
            prev_enable_history_search = event.current_buffer.enable_history_search
            event.current_buffer.enable_history_search = lambda: True
            event.current_buffer.history_forward(count=event.arg)
        finally:
            event.current_buffer.enable_history_search = prev_enable_history_search

class PythonSyntaxValidator(Validator):
    def validate(self, document):
        text = document.text
        if document_is_multiline_python(document):
            return
        try:
            compile(text, "<None>", 'exec')
        except SyntaxError as e:
            raise ValidationError(message="SyntaxError: %s" % e.args[0], cursor_position=e.offset)

if __name__ == '__main__':
    prompt_number = 1
    _globals = globals().copy()
    _locals = {}
    history = InMemoryHistory()

    manager = KeyBindingManager.for_prompt()
    define_custom_keys(manager)

    while True:
        try:
            def is_buffer_multiline():
                return True
                return document_is_multiline_python(buffer.document)

            multiline = Condition(is_buffer_multiline)
            buffer = Buffer(
                enable_history_search=False,
                is_multiline=multiline,
                validator=PythonSyntaxValidator(),
                history=history,
                )
            application = Application(
                create_prompt_layout(
                    message='In [%s]: ' % prompt_number,
                    lexer=PygmentsLexer(PythonLexer),
                    multiline=Condition(lambda cli: multiline())
                    ),
                buffer=buffer,
                style=style_from_pygments(MonokaiStyle),
                key_bindings_registry=manager.registry,
                mouse_support=True,
            )
            command = run_application(application, true_color=True)
        except EOFError:
            break
        except KeyboardInterrupt:
            print("KeyboardInterrupt")
            continue

        try:
            res = eval(command, _globals, _locals)
        except SyntaxError:
            try:
                res = exec(command, _globals, _locals)
            except BaseException as e:
                print(highlight(format_exc(), PythonTracebackLexer(), TerminalFormatter(bg='dark')))
            else:
                prompt_number += 1
        except BaseException as e:
            print(highlight(format_exc(), PythonTracebackLexer(), TerminalFormatter(bg='dark')))
        else:
            print(res)
            prompt_number += 1
