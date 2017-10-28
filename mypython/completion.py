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

from .dircompletion import DirCompleter
from .magic import MAGICS
from .mypython import In

def get_jedi_script_from_document(document, locals, globals):
    import jedi  # We keep this import in-line, to improve start-up time.
                 # Importing Jedi is 'slow'.

    full_document = '\n'.join(i for _, i in sorted(In.items()))
    if not full_document.endswith('\n'):
        full_document += '\n'

    try:
        return jedi.Interpreter(
            full_document + '\n' + document.text,
            column=document.cursor_position_col,
            line=document.cursor_position_row + 2 + len(full_document.splitlines()),
            path='<mypython>',
            namespaces=[locals, globals])
    except Exception as e:
        # Workaround for many issues (see original code)
        return None

class PythonCompleter(Completer):
    """
    Completer for Python code.
    """
    def __init__(self, get_globals, get_locals):
        super(PythonCompleter, self).__init__()

        self.get_globals = get_globals
        self.get_locals = get_locals

    def _complete_python_while_typing(self, document):
        char_before_cursor = document.char_before_cursor
        return document.text and (
            char_before_cursor.isalnum() or char_before_cursor in '_.')

    def get_completions(self, document, complete_event):
        """
        Get Python completions.
        """
        if document.text.startswith('%') and ' ' not in document.text_before_cursor:
            for magic in MAGICS:
                if magic.startswith(document.text):
                    yield Completion(magic + ' ',
                        -len(document.text_before_cursor),
                        display_meta='magic')

            return
        if complete_event.completion_requested or self._complete_python_while_typing(document):

            # First do the dir completions (should be faster, and more
            # accurate)
            completer = DirCompleter(namespace=self.get_locals())
            state = 0
            dir_completions = set()
            while True:
                completion = completer.complete(document.text_before_cursor, state)
                if completion:
                    name = completer.NAME.match(document.text_before_cursor[::-1]).group(0)[::-1]
                    dir_completions.add(completion)
                    if len(completion) < len(document.text_before_cursor):
                        state += 1
                        continue
                    yield Completion(completion,
                        -len(name),
                        display_meta='from dir()')
                    state += 1
                else:
                    break

            script = get_jedi_script_from_document(document, self.get_locals(), self.get_globals())

            if script:
                try:
                    completions = script.completions()
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
