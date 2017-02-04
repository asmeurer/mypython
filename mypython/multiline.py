"""
Taken from ptpython.util and ptpython.key_bindings

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

import re

from prompt_toolkit.filters import Filter

def has_unclosed_brackets(text):
    """
    Starting at the end of the string. If we find an opening bracket
    for which we didn't had a closing one yet, return True.
    """
    stack = []

    # Ignore braces inside strings
    text = re.sub(r'''('[^']*'|"[^"]*")''', '', text)  # XXX: handle escaped quotes.!

    for c in reversed(text):
        if c in '])}':
            stack.append(c)

        elif c in '[({':
            if stack:
                if ((c == '[' and stack[-1] == ']') or
                        (c == '{' and stack[-1] == '}') or
                        (c == '(' and stack[-1] == ')')):
                    stack.pop()
            else:
                # Opening bracket for which we didn't had a closing one.
                return True

    return False

_multiline_string_delims = re.compile('''[']{3}|["]{3}''')

def document_is_multiline_python(document):
    """
    Determine whether this is a multiline Python document.
    """
    def ends_in_multiline_string():
        """
        ``True`` if we're inside a multiline string at the end of the text.
        """
        delims = _multiline_string_delims.findall(document.text)
        opening = None
        for delim in delims:
            if opening is None:
                opening = delim
            elif delim == opening:
                opening = None
        return bool(opening)

    if '\n' in document.text or ends_in_multiline_string():
        return True

    def line_ends_with_colon():
        return document.current_line.rstrip()[-1:] == ':'

    # If we just typed a colon, or still have open brackets, always insert a real newline.
    if line_ends_with_colon() or \
            (document.is_cursor_at_the_end and
             has_unclosed_brackets(document.text_before_cursor)) or \
            document.text.startswith('@'):
        return True

    # If the character before the cursor is a backslash (line continuation
    # char), insert a new line.
    elif document.text_before_cursor[-1:] == '\\':
        return True

    return False

def auto_newline(buffer):
    r"""
    Insert \n at the cursor position. Also add necessary padding.
    """
    insert_text = buffer.insert_text

    if buffer.document.current_line_after_cursor:
        # When we are in the middle of a line. Always insert a newline.
        insert_text('\n')
    else:
        # Go to new line, but also add indentation.
        current_line = buffer.document.current_line_before_cursor.rstrip()
        insert_text('\n')

        unindent_keywords = ['pass', 'continue', 'break', 'return', 'raise']
        # Unident if the last line ends with 'pass', remove four spaces.
        for keyword in unindent_keywords:
            begin = current_line.lstrip()
            if begin.startswith(keyword + ' ') or begin == keyword:
                unindent = True
                break
        else:
            unindent = False

        # Copy whitespace from current line
        current_line2 = current_line[4:] if unindent else current_line

        for c in current_line2:
            if c.isspace():
                insert_text(c)
            else:
                break

        # If the last line ends with a colon, add four extra spaces.
        if current_line[-1:] == ':':
            for x in range(4):
                insert_text(' ')

class TabShouldInsertWhitespaceFilter(Filter):
    """
    When the 'tab' key is pressed with only whitespace character before the
    cursor, do autocompletion. Otherwise, insert indentation.
    Except for the first character at the first line. Then always do a
    completion. It doesn't make sense to start the first line with
    indentation.
    """
    def __call__(self, cli):
        b = cli.current_buffer
        before_cursor = b.document.current_line_before_cursor

        return bool(not before_cursor or before_cursor.isspace())
