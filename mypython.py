#!/usr/bin/env python

from pygments.lexers import PythonLexer, PythonTracebackLexer
from pygments.formatters import TerminalFormatter
from pygments import highlight

from prompt_toolkit.shortcuts import prompt
from prompt_toolkit.layout.lexers import PygmentsLexer

from traceback import format_exc

if __name__ == '__main__':
    prompt_number = 1
    _globals = globals().copy()
    _locals = {}
    while True:
        try:
            command = prompt('In [%s]: ' % prompt_number, lexer=PygmentsLexer(PythonLexer))
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
