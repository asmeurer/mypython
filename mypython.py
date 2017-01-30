#!/usr/bin/env python

from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import TerminalFormatter
from pygments.styles.monokai import MonokaiStyle
from pygments import highlight

from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.layout.lexers import PygmentsLexer
from prompt_toolkit.styles import style_from_pygments
from prompt_toolkit.history import InMemoryHistory

from traceback import format_exc

if __name__ == '__main__':
    prompt_number = 1
    _globals = globals().copy()
    _locals = {}
    history = InMemoryHistory()
    while True:
        try:
            command = prompt('In [%s]: ' % prompt_number,
                lexer=PygmentsLexer(PythonLexer),
                style=style_from_pygments(MonokaiStyle), true_color=True,
                history=history, enable_history_search=False)
        except EOFError:
            break

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
