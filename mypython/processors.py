"""
Adapted from prompt_toolkit.layout.processors

Copyright (c) 2014, Jonathan Slenders
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

from prompt_toolkit.layout.processors import (Transformation,
    HighlightMatchingBracketProcessor, Processor)
from prompt_toolkit.layout.utils import explode_text_fragments
from prompt_toolkit.application import get_app
from prompt_toolkit.formatted_text import fragment_list_width, to_formatted_text

from pyflakes.checker import Checker
from pyflakes.messages import (UnusedImport, UnusedVariable, UndefinedName,
                               Message, ImportStarUsed, ImportStarUsage)

from .tokenize import matching_parens, indentation, dedent
from .magic import MAGICS, NON_PYTHON_MAGICS

import ast
from collections import namedtuple
from functools import lru_cache

###########################################
# Highlight matching/mismatching brackets #
###########################################

class MyHighlightMatchingBracketProcessor(HighlightMatchingBracketProcessor):
    def _get_positions_to_highlight(self, document):
        """
        Return a list of (row, col) tuples that need to be highlighted.

        Same as HighlightMatchingBracketProcessor._get_positions_to_highlight
        except only highlights the position before the cursor.
        """
        good = []
        matching, mismatching = matching_parens(document.text)

        row, col = document.translate_index_to_position(document.cursor_position)
        prow, pcol = document.translate_index_to_position(document.cursor_position - 1)
        for left, right in matching:
            if left.start == (row+1, col):
                good.extend([
                    (left.start[0]-1, left.start[1]),
                    (right.start[0]-1, right.start[1]),
                    ])
            # Highlight the character before the cursor for end braces.
            if right.start == (prow+1, pcol):
                good.extend([
                    (left.start[0]-1, left.start[1]),
                    (right.start[0]-1, right.start[1]),
                    ])

        bad = [(i.start[0]-1, i.start[1]) for i in mismatching]
        return good, bad

    def apply_transformation(self, transformation_input):
        buffer_control, document, lineno, source_to_display, fragments, _, _ = transformation_input.unpack()

        # When the application is in the 'done' state, don't highlight.
        if get_app().is_done:
            return Transformation(fragments)

        # Get the highlight positions.
        key = (get_app().render_counter, document.text, document.cursor_position)

        good, bad = self._positions_cache.get(
            key, lambda: self._get_positions_to_highlight(document))

        # Apply if positions were found at this line.
        for row, col in good:
            if row == lineno:
                col = source_to_display(col)
                fragments = explode_text_fragments(fragments)
                style, text = fragments[col]

                if col == document.cursor_position_col and row == document.cursor_position_row:
                    style += ' class:pygments.matchingbracket.cursor '
                else:
                    style += ' class:pygments.matchingbracket.other '

                fragments[col] = (style, text)

        for row, col in bad:
            if row == lineno:
                col = source_to_display(col)
                fragments = explode_text_fragments(fragments)
                style, text = fragments[col]

                if col == document.cursor_position_col and row == document.cursor_position_row:
                    style += ' class:pygments.mismatchingbracket.cursor '
                else:
                    style += ' class:pygments.mismatchingbracket.other '

                fragments[col] = (style, text)

        return Transformation(fragments)

#####################
# Pyflakes warnings #
#####################

# Note:
# pyflakes counts rows from 1 and columns from 0
# prompt-toolkit counts rows from 0 and columns from 0
# SyntaxErrors count rows (lineno) from 1 and columns (offset) from 1

loc = namedtuple("loc", ["lineno", "col_offset"])

class SyntaxErrorMessage(Message):
    message = "SyntaxError: %s"

    def __init__(self, filename, loc, msg, text):
        Message.__init__(self, filename, loc)
        self.message_args = (msg,)
        self.text = text

# TODO: Cache this as a generator
@lru_cache()
def get_pyflakes_warnings(code, defined_names=frozenset(),
                          skip=(UnusedImport, ImportStarUsed, ImportStarUsage)):
    """
    Get pyflakes warnings for code

    Return a list of (row, col, msg, m) tuples, where

    row is the line number (starting at 0),
    col is the column number (starting at 0),
    msg is the string message for the warning, and
    m is the pyflakes Message class for the message

    defined_names should be a frozenset of names which should be considered
    already defined in the global namespace for the code.

    skip should be a tuple of pyflakes message classes to skip.
    """
    code = code.rstrip()

    prefix = ''

    if code.lstrip().startswith('%'):
        code = code.lstrip()
        for i in NON_PYTHON_MAGICS:
            if code.startswith(i):
                return []

        for i in MAGICS:
            if code.startswith(i + ' '):
                prefix = i + ' '
            elif code.startswith(i + '?'):
                prefix = i
            elif code.startswith(i + '\n'):
                prefix = i + '\n'
            elif code == i:
                prefix = i
            else:
                continue
            code = code[len(prefix):]
            break

    suffix = ''
    if code.endswith('???'):
        pass
    elif code.endswith('??'):
        suffix = '??'
    elif code.endswith('?'):
        suffix = '?'
    code = code[:len(code)-len(suffix)]

    margin = indentation(code)
    code = dedent(code, margin)
    col_offset = len(margin)

    def _get_warnings(code, defined_names):
        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            msg = e.args[0]
            col = max(e.offset - 1, 0)
            row = e.lineno - 1
            m = SyntaxErrorMessage(e.filename, loc(e.lineno, col + col_offset), msg, e.text)

            endcol = col
            # Highlight the whole line
            line = code.splitlines()[row]
            while endcol < len(line) and line[endcol] != '\n':
                endcol += 1
            if endcol == len(line):
                endcol += 1
            if col >= len(line):
                # Handle col == len(line) and also a bug where the col is very large.
                line = line + ' '*(col - len(line) + 1)
            while col > 0 and line[col] != '\n':
                col -= 1

            if row == 0:
                m.col += len(prefix)

            if '\n' in prefix:
                row += 1
            for c in range(col + col_offset, endcol + col_offset):
                if row == 0: # '\n' not in prefix
                    c += len(prefix)
                yield (row, c, m.message % m.message_args, m)
            return

        try:
            checker = Checker(tree, builtins=defined_names)
        except RecursionError:
            return
        messages = checker.messages
        for m in messages:
            if isinstance(m, skip):
                continue
            row = m.lineno - 1
            col = m.col
            msg = m.message % m.message_args
            if row == 0:
                m.col += len(prefix)

            endcol = col
            if isinstance(m, (UndefinedName, UnusedVariable)):
                endcol = col + len(m.message_args[0])
            else:
                # Highlight the whole line
                line = code.splitlines()[row]
                endcol = len(line)

            if '\n' in prefix:
                row += 1
            for c in range(col + col_offset, endcol + col_offset):
                if row == 0: # '\n' not in prefix
                    c += len(prefix)
                yield (row, c, msg, m)

    return sorted(_get_warnings(code, defined_names), key=lambda x: x[:2])

class HighlightPyflakesErrorsProcessor(Processor):

    def apply_transformation(self, transformation_input):
        buffer_control, document, lineno, source_to_display, fragments, width, height = transformation_input.unpack()

        text = document.text

        for row, col, msg, m in get_pyflakes_warnings(text, frozenset(buffer_control.buffer.session._locals)):
            # col = source_to_display(col)
            if isinstance(m, UnusedImport):
                continue

            if row == lineno:
                # TODO: handle warnings without a column
                fragments = explode_text_fragments(fragments)
                if col > len(fragments):
                    print(f"Error with pyflakes checker: {col=}, {len(fragments)=}, {row=}")
                    continue

                if col == len(fragments):
                    fragments += [('', ' ')]

                style, char = fragments[col]
                if col == document.cursor_position_col and lineno == document.cursor_position_row:
                    style += ' class:pygments.pyflakeswarning.cursor '
                else:
                    style += ' class:pygments.pyflakeswarning.other '

                if isinstance(m, SyntaxErrorMessage):
                    # Only color the whole line if the cursor is not on it
                    if lineno == document.cursor_position_row:
                        style = style.replace('class:pygments.pyflakeswarning.other', '')
                    style = style.replace('pyflakeswarning', 'pyflakeserror')

                fragments[col] = (style, char)

                if isinstance(m, SyntaxErrorMessage) and m.col == col:
                    style, char = fragments[col]
                    style += ' class:pygments.pyflakeserror.column '
                    fragments[col] = (style, char)

        return Transformation(fragments)

class AppendAIAutoSuggestion(Processor):
    """
    Based on prompt_toolkit.layout.processors.Autosuggestion but is not
    limited to just inserting the suggestion at the end.
    """

    def __init__(self, style: str = "class:auto-suggestion") -> None:
        self.style = style

    def apply_transformation(self, transformation_input):
        buffer = transformation_input.buffer_control.buffer
        app = get_app()

        source_to_display = transformation_input.source_to_display
        column = source_to_display(buffer.document.cursor_position_col)
        current_line_before_cursor = buffer.document.current_line_before_cursor
        if buffer.ai_suggestions:
            suggestion = buffer.ai_suggestions[buffer.ai_suggestion_index]

            terminal_size = app.output.get_size().columns
            wrap_width = terminal_size - prompt_width(buffer)
            suggestion = replace_newlines_with_spaces(current_line_before_cursor + suggestion, wrap_width)[column:]
        else:
            suggestion = ""

        fragments = list(transformation_input.fragments)
        if transformation_input.lineno == buffer.document.cursor_position_row:
            fragments.insert(column, (self.style, suggestion))

        return Transformation(fragments=fragments)

def prompt_width(buffer):
    return fragment_list_width(to_formatted_text(buffer.session.message))

def replace_newlines_with_spaces(text, column_width):
    lines = text.split('\n')
    result = ''
    for i, line in enumerate(lines):
        line_length = len(line)
        # Calculate padding to reach the next multiple of column_width
        if not line:
            padding = column_width
        else:
            padding = (column_width - (line_length % column_width)) % column_width
        result += line
        if i != len(lines) - 1:  # Avoid adding padding after the last line
            result += ' ' * padding
    return result
