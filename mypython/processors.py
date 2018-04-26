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
    HighlightMatchingBracketProcessor)
from prompt_toolkit.layout.utils import explode_text_fragements
from prompt_toolkit.token import Token
from prompt_toolkit.application import get_app

from .tokenize import matching_parens

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
                fragments = explode_text_fragements(fragments)
                token, text = fragments[col]

                if col == document.cursor_position_col:
                    token += (':', ) + Token.MatchingBracket.Cursor
                else:
                    token += (':', ) + Token.MatchingBracket.Other

                fragments[col] = (token, text)

        for row, col in bad:
            if row == lineno:
                col = source_to_display(col)
                fragments = explode_text_fragements(fragments)
                token, text = fragments[col]

                if col == document.cursor_position_col:
                    token += (':', ) + Token.MismatchingBracket.Cursor
                else:
                    token += (':', ) + Token.MismatchingBracket.Other

                fragments[col] = (token, text)

        return Transformation(fragments)
