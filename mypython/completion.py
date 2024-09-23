"""
Taken from ptpython.completer and ptpython.util

Copyright (c) 2015, Jonathan Slenders
All rights reserved.

Redistribution and use in source and binary forms, with or without modification,
are permitted provided that the following conditions are met:

* Redistributions of source code must retain the above copyright notice, this
  list of conditions and the following disclaimer.

* Redistributions in binary form must reproduce the above copyright notice, this
  list of conditions and the following disclaimer in the documentation and/or
  other materials provided with the distribution.

* Neither the name of the {organization} nor the names of its
  contributors may be used to endorse or promote products derived from
  this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""
from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.patch_stdout import patch_stdout

import traceback

from .dircompletion import DirCompleter
from .magic import MAGICS, MAGIC_COMPLETIONS

def get_jedi_script_from_document(document, _locals, _globals, session):
    import jedi  # We keep this import in-line, to improve start-up time.
                 # Importing Jedi is 'slow'.

    full_document = '\n'.join(i for _, i in sorted(session.builtins['In'].items()))
    if not full_document.endswith('\n'):
        full_document += '\n'

    text = document.text
    for magic in MAGICS:
        if text.startswith(magic):
            text = ' '*len(magic) + text[len(magic):]
            break

    line = document.cursor_position_row + 2 + len(full_document.splitlines())
    column = document.cursor_position_col

    try:
        return (jedi.Interpreter(
            full_document + '\n' + text,
            path='<mypython>',
            namespaces=[_locals, _globals]), line, column)
    except Exception:
        # Workaround for many issues (see original code)
        return None

class PythonCompleter(Completer):
    """
    Completer for Python code.
    """
    def __init__(self, get_globals, get_locals, session):
        super(PythonCompleter, self).__init__()

        self.get_globals = get_globals
        self.get_locals = get_locals
        self.session = session

    def _complete_python_while_typing(self, document):
        char_before_cursor = document.char_before_cursor
        return document.text and (
            char_before_cursor.isalnum() or char_before_cursor in '_.')

    def get_completions(self, document, complete_event):
        """
        Get Python completions.
        """
        if ' ' not in document.text_before_cursor:
            for magic in MAGICS:
                for m in [magic, magic[1:]]:
                    if m.startswith(document.text_before_cursor):
                        yield Completion(magic + ' ',
                            -len(document.text_before_cursor),
                            display_meta='magic')

            if document.text.startswith('%'):
                return

        text_before_cursor = document.text_before_cursor

        for magic in MAGICS:
            if text_before_cursor.startswith(magic + ' '):
                text_before_cursor = text_before_cursor[len(magic) + 1:]
                if magic in MAGIC_COMPLETIONS:
                    for completion in MAGIC_COMPLETIONS[magic]():
                        if completion.startswith(text_before_cursor):
                            yield Completion(completion,
                                             -len(text_before_cursor), display_meta=magic)
                    return
                break

        if complete_event.completion_requested or self._complete_python_while_typing(document):

            # First do the dir completions (should be faster, and more
            # accurate)
            completer = DirCompleter(namespace=self.get_locals())
            state = 0
            dir_completions = set()
            while True:
                completion = completer.complete(text_before_cursor, state)
                if completion:
                    name = completer.NAME.match(text_before_cursor[::-1]).group(0)[::-1]
                    dir_completions.add(completion)
                    if len(completion) < len(text_before_cursor):
                        state += 1
                        continue
                    yield Completion(completion,
                        -len(name),
                        display_meta='from dir()')
                    state += 1
                else:
                    break

            script, line, column = get_jedi_script_from_document(document,
                self.get_locals(), self.get_globals(), self.session)

            if script:
                try:
                    completions = script.complete(line=line, column=column)
                except Exception:
                    with patch_stdout():
                        print("Error with Jedi completion:\n")
                        traceback.print_exc()
                except TypeError:
                    # Issue #9: bad syntax causes completions() to fail in jedi.
                    # https://github.com/jonathanslenders/python-prompt-toolkit/issues/9
                    pass
                except UnicodeDecodeError:
                    # Issue #43: UnicodeDecodeError on OpenBSD
                    # https://github.com/jonathanslenders/python-prompt-toolkit/issues/43
                    pass
                except AttributeError:
                    # Jedi issue #513: https://github.com/davidhalter/jedi/issues/513
                    pass
                except ValueError:
                    # Jedi issue: "ValueError: invalid \x escape"
                    pass
                except KeyError:
                    # Jedi issue: "KeyError: u'a_lambda'."
                    # https://github.com/jonathanslenders/ptpython/issues/89
                    pass
                except IOError:
                    # Jedi issue: "IOError: No such file or directory."
                    # https://github.com/jonathanslenders/ptpython/issues/71
                    pass
                except NotImplementedError:
                    pass
                else:
                    for c in completions:
                        if c.name_with_symbols in dir_completions:
                            continue
                        yield Completion(c.name_with_symbols,
                            len(c.complete) - len(c.name_with_symbols),
                            display=c.name_with_symbols,
                            display_meta=c.description)
