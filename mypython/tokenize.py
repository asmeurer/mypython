"""
Various helpers that are based on Python tokenization

Note that the tokenize module starts the rows at 1 and prompt_toolkit starts
them at 0.
"""

import io
from itertools import tee, chain
from tokenize import tokenize, TokenError
from tokenize import (STRING, COLON, AT, ENDMARKER, DEDENT, NAME, NEWLINE,
                      ENCODING)
import ast
import re

braces = {
    '(': ')',
    '[': ']',
    '{': '}',
    }

def tokenize_string(s, tokenizer=None):
    """
    Generator of tokens from the string s

    tokenizer should be 'tokenize', 'parso', or None (the default, which is
    the same as 'tokenize').
    """
    if tokenizer is None:
        tokenizer = 'tokenize'
    if tokenizer == 'tokenize':
        yield from tokenize(io.BytesIO(s.encode('utf-8')).readline)
    elif tokenizer == 'parso':
        from parso.utils import parse_version_string
        from parso.python.tokenize import tokenize as parso_tokenize

        for tok in parso_tokenize(s, version_info=parse_version_string()):
            # Make the parso tokens compatible with tokenize
            tok.start = tok.start_pos
            tok.end = tok.end_pos

            yield tok
    else:
        raise ValueError("The tokenizer keyword argument should be 'tokenize' or 'parso'")

def matching_parens(s, allow_intermediary_mismatches=True, tokenizer=None):
    """
    Find matching and mismatching parentheses and braces

    s should be a string of (partial) Python code.

    Returns a tuple (matching, mismatching).

    matching is a list of tuples of matching TokenInfo objects for matching
    parentheses/braces.

    mismatching is a list of TokenInfo objects for mismatching
    parentheses/braces.

    allow_intermediary_mismatches can be True (the default), or False. If it
    is True, an opening brace can still be considered matching if it is closed
    with the wrong brace but later closed with the correct brace. If it is
    False, once an opening brace is closed with the wrong brace it---and any
    unclosed braces before it---cannot be matched.

    tokenizer should be 'tokenize' or 'parso'. By default it is 'parso'. The
    parso tokenizer is able to handle braces inside of f-string expressions,
    whereas the 'tokenize' tokenizer is not.

        >>> matching_parens('f"{()}"', tokenizer='parso')
        ([(TokenInfo(type=OP, string='{', start_pos=(1, 2), prefix=''),
           TokenInfo(type=OP, string='}', start_pos=(1, 5), prefix='')),
          (TokenInfo(type=OP, string='(', start_pos=(1, 3), prefix=''),
           TokenInfo(type=OP, string=')', start_pos=(1, 4), prefix=''))],
        [])
        >>> matching_parens('f"{()}"', tokenizer='tokenize')
        ([], [])

    For example, consider '[ { ] }'. If allow_intermediary_mismatches is
    False, all the braces are considered mismatched.

        >>> matching, mismatching = matching_parens('[ { ] }',
        ... allow_intermediary_mismatches=False)
        >>> matching
        []
        >>> mismatching
        [TokenInfo(..., string='[', ...),
         TokenInfo(..., string='{', ...),
         TokenInfo(..., string=']', ...),
         TokenInfo(..., string='}', ...)]

    However, if it is True, the { and } are considered matching.

        >>> matching, mismatching = matching_parens('[ { ] }',
        ... allow_intermediary_mismatches=True)
        >>> matching
        [(TokenInfo(..., string='{', ...), TokenInfo(..., string='}', ...))]
        >>> mismatching
        [TokenInfo(..., string='[', ...),
         TokenInfo(..., string=']', ...)]

    Furthermore, with '[ { ] } ]' only the middle ] will be considered
    mismatched (with False, all would be mismatched).

        >>> matching, mismatching = matching_parens('[ { ] } ]',
        ... allow_intermediary_mismatches=True)
        >>> matching
        [(TokenInfo(..., string='[', ...), TokenInfo(..., string=']', start_pos=(1, 8), ...)),
         (TokenInfo(..., string='{', ...), TokenInfo(..., string='}', ...))]
        >>> mismatching
        [TokenInfo(..., string=']', start_pos=(1, 4), ...)]

        >>> matching, mismatching = matching_parens('[ { ] } ]',
        ... allow_intermediary_mismatches=False)
        >>> matching
        []
        >>> mismatching
        [TokenInfo(..., string='[', ...),
         TokenInfo(..., string='{', ...),
         TokenInfo(..., string=']', ...),
         TokenInfo(..., string='}', ...),
         TokenInfo(..., string=']', ...)]

    allow_intermediary_mismatches=False is a more technically correct version,
    but allow_intermediary_mismatches=True may provide more useful feedback if
    mismatching braces are highlighted, as it is more likely to only highlight
    the "mistake" braces.

    Example:

        >>> matching, mismatching = matching_parens("('a', {(1, 2)}, ]")
        >>> matching
        [(TokenInfo(..., string='{', ...), TokenInfo(..., string='}', ...)),
         (TokenInfo(..., string='(', ...), TokenInfo(..., string=')', ...))]
        >>> mismatching
        [TokenInfo(..., string='(', ...), TokenInfo(..., string=']', ...)]

    """
    if tokenizer is None:
        tokenizer = 'parso'
    if tokenizer == 'parso':
        from parso.python.tokenize import ERRORTOKEN
    else:
        from tokenize import ERRORTOKEN
    stack = []
    matching = []
    mismatching = []
    try:
        for tok in tokenize_string(s, tokenizer=tokenizer):
            typ = tok.type
            string = tok.string
            if typ == ERRORTOKEN:
                # There is an unclosed string. If we do not break here,
                # tokenize will tokenize the stuff after the string delimiter.
                break
            elif string in braces:
                stack.append(tok)
            elif string in braces.values():
                if not stack:
                    mismatching.append(tok)
                    continue
                prevtok = stack.pop()
                if braces[prevtok.string] == string:
                    matching.append((prevtok, tok))
                else:
                    if allow_intermediary_mismatches:
                        stack.append(prevtok)
                    else:
                        mismatching.insert(0, prevtok)
                    mismatching.append(tok)
            else:
                continue
    except TokenError:
        pass
    except IndentationError:
        pass

    matching.reverse()

    # Anything remaining on the stack is mismatching. Keep the mismatching
    # list in order.
    stack.reverse()
    mismatching = stack + mismatching
    return matching, mismatching

def inside_string(s, row, col, include_quotes=False):
    """
    Returns True if row, col is inside a string in s, False otherwise.

    row starts at 1 and col starts at 0.

    If include_quotes=True, the quote characters and any prefix characters
    (like r, b, f, or u) are counted as part of the string. The default is
    False.

    """
    from tokenize import ERRORTOKEN
    def _offsets(string):
        # The offsets for the quote characters. The inside part of the
        # string will be tokval[start_margin: -end_margin]
        start_offset = end_offset = 0
        if not include_quotes:
            # Handle things like r'...' and rb'...'. There can be at most
            # two prefix characters. Since we are "deleting" characters,
            # shift the column that we check to the left. A negative
            # column would mean we are on a line below the opening of the
            # string, in which case start[0] will be less than row anyway.
            if string[:2].isalpha():
                start_offset += 2
            elif string[:1].isalpha():
                start_offset += 1

            # Figure out if the string is single- or triple-quoted.
            # Since tokenize only tokenizes complete valid string literals
            # as STRING, ""... must be a triple quoted string, unless it
            # is the empty string
            assert string[start_offset] in '"\'', tokval
            if tokval[start_offset] == tokval[start_offset+1] and len(string[start_offset:]) > 2:
                start_offset += 3
                end_offset += 3
            else:
                start_offset += 1
                end_offset += 1

        return (start_offset, end_offset)

    try:
        name_mark = False
        for toknum, tokval, start, end, line in tokenize_string(s):
            if toknum == NAME and include_quotes and start <= (row, col) < end:
                # Something like r'... that is unclosed will tokenize as NAME,
                # ERRORTOKEN. Mark here to check if the next token is
                # ERRORTOKEN.
                name_mark = tokval
                continue
            if toknum == ERRORTOKEN and tokval[0] in '"\'':
                if name_mark:
                    # (row, col) is on the name before the unclosed error
                    # string.
                    # Check if the previous token + string is a valid string
                    # prefix.

                    # name_mark not False implies include_quotes == True
                    try:
                        ast.literal_eval(name_mark + '""')
                    except SyntaxError:
                        return False
                    else:
                        return True
                # There is an unclosed string. We haven't gotten to the
                # position yet, so it must be inside this string
                start_offset = 0 if include_quotes else 1
                return (start[0], start[1] + start_offset) <= (row, col)
            elif name_mark:
                return False
            if start <= (row, col) < end:
                if not toknum == STRING:
                    return False

                start_offset, end_offset = _offsets(tokval)
                return (start[0], start[1] + start_offset) <= (row, col) < (end[0], end[1] - end_offset)

    except TokenError as e:
        # Uncompleted docstring or braces. If it's the former, then (row, col)
        # must be after the start of the unclosed string, or else we would
        # have seen a prior token with start <= (row, col) <= end.
        if 'string' in e.args[0] and (row, col) >= e.args[1]:
            start = e.args[1]
            tokval = s.splitlines()[start[0]-1][start[1]:]
            start_offset, _ = _offsets(tokval)
            return (start[0], start[1] + start_offset) <= (row, col)
        return False
    except IndentationError:
        return False

    return False

def parso_inside_string(s, row, col):
    from parso.utils import parse_version_string
    from parso.python.tokenize import tokenize, INDENT, STRING, ERRORTOKEN

    start = end = (0, 0)
    toknum = prev_tok = -1
    for token in tokenize(s, parse_version_string()):
        start = end
        prev_tok = toknum
        toknum, tokval, end, prefix = token
        if start <= (row, col) < end:
            if prev_tok == INDENT:
                continue
            break

    return prev_tok in [STRING, ERRORTOKEN]

# try:
#     import parso
#     inside_string = parso_inside_string
#     del parso
# except ImportError:
#     pass

# From https://docs.python.org/3/library/itertools.html
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def nwise(iterable, n, fill=False):
    """
    n-way rolling window over iterable.

    Generalization of pairwise().

    If fill=True then the window will start like (None, ..., None, s0), (None,
    ..., None, s0, s1), .... Otherwise it will start with (s0, s1, ..., sn).
    """
    iters = tee(iterable, n)
    if fill:
        iters = [chain([None]*i, iter) for i, iter in enumerate(reversed(iters))]
        iters.reverse()
    else:
        for i, iter in enumerate(iters):
            for j in range(i):
                next(iter, None)
    return zip(*iters)

def is_multiline_python(text):
    """
    Returns True of text should be considered multiline.

    text is considered multiline if typing Enter at the end of text should add
    a newline. Returns False if the text is a single line that can be
    executed. Also returns False in some situations when text has a syntax
    error that cannot be resolved after an additional line, such as EOL in a
    non-docstring literal or an indentation error.

    """
    from tokenize import ERRORTOKEN

    # Dedent the text, otherwise, the last token will be DEDENT
    text = text.lstrip()

    try:
        error = False
        for (prevprev, prev, tok) in nwise(tokenize_string(text), 3, fill=True):
            toknum, tokval, start, end, line = tok
            # The first token is encoding
            if prev and prev.type == ENCODING and tok.exact_type == AT:
                # Decorator
                return True
            if toknum == ERRORTOKEN:
                # Error means unclosed (non doc-) string or backslash
                # continuation. We want a backslash continuation to be
                # multiline, which is caught below. Every other case shouldn't
                # be multiline.
                error = True
            if toknum in {ENDMARKER, DEDENT}:
                # In 3.6.7 and 3.7.1 the last token before ENDMARKER is always
                # NEWLINE. We want to handle both cases here.
                if prev.type == NEWLINE:
                    if prevprev.type == ERRORTOKEN and prevprev.string == '\\':
                        return True
                else:
                    if prev.type == ERRORTOKEN and prev.string == '\\':
                        return True

    except TokenError:
        # Uncompleted docstring or braces
        # Multiline unless there is an uncompleted non-docstring
        if tok.type != ENCODING and toknum == ERRORTOKEN and tokval == '\\':
            return True
        return not error
    except IndentationError:
        return False
    if error:
        return False

    if '\n' in text:
        return True

    return prev.exact_type == COLON or (prev.exact_type == NEWLINE and prevprev.exact_type == COLON)

# Taken from standard library textwrap module

# Changes:

# - Renamed dedent() to indentation() and made it return the indentation level
#   of the text instead of dedenting it.

# - Made dedent() function that applies dedentation to text and a margin

# Copyright (C) 1999-2001 Gregory P. Ward.
# Copyright (C) 2002, 2003 Python Software Foundation.
# Written by Greg Ward <gward@python.net>

# 1. This LICENSE AGREEMENT is between the Python Software Foundation ("PSF"), and
#    the Individual or Organization ("Licensee") accessing and otherwise using Python
#    3.6.0 software in source or binary form and its associated documentation.
#
# 2. Subject to the terms and conditions of this License Agreement, PSF hereby
#    grants Licensee a nonexclusive, royalty-free, world-wide license to reproduce,
#    analyze, test, perform and/or display publicly, prepare derivative works,
#    distribute, and otherwise use Python 3.6.0 alone or in any derivative
#    version, provided, however, that PSF's License Agreement and PSF's notice of
#    copyright, i.e., "Copyright © 2001-2017 Python Software Foundation; All Rights
#    Reserved" are retained in Python 3.6.0 alone or in any derivative version
#    prepared by Licensee.
#
# 3. In the event Licensee prepares a derivative work that is based on or
#    incorporates Python 3.6.0 or any part thereof, and wants to make the
#    derivative work available to others as provided herein, then Licensee hereby
#    agrees to include in any such work a brief summary of the changes made to Python
#    3.6.0.
#
# 4. PSF is making Python 3.6.0 available to Licensee on an "AS IS" basis.
#    PSF MAKES NO REPRESENTATIONS OR WARRANTIES, EXPRESS OR IMPLIED.  BY WAY OF
#    EXAMPLE, BUT NOT LIMITATION, PSF MAKES NO AND DISCLAIMS ANY REPRESENTATION OR
#    WARRANTY OF MERCHANTABILITY OR FITNESS FOR ANY PARTICULAR PURPOSE OR THAT THE
#    USE OF PYTHON 3.6.0 WILL NOT INFRINGE ANY THIRD PARTY RIGHTS.
#
# 5. PSF SHALL NOT BE LIABLE TO LICENSEE OR ANY OTHER USERS OF PYTHON 3.6.0
#    FOR ANY INCIDENTAL, SPECIAL, OR CONSEQUENTIAL DAMAGES OR LOSS AS A RESULT OF
#    MODIFYING, DISTRIBUTING, OR OTHERWISE USING PYTHON 3.6.0, OR ANY DERIVATIVE
#    THEREOF, EVEN IF ADVISED OF THE POSSIBILITY THEREOF.
#
# 6. This License Agreement will automatically terminate upon a material breach of
#    its terms and conditions.
#
# 7. Nothing in this License Agreement shall be deemed to create any relationship
#    of agency, partnership, or joint venture between PSF and Licensee.  This License
#    Agreement does not grant permission to use PSF trademarks or trade name in a
#    trademark sense to endorse or promote products or services of Licensee, or any
#    third party.
#
# 8. By copying, installing or otherwise using Python 3.6.0, Licensee agrees
#    to be bound by the terms and conditions of this License Agreement.

_whitespace_only_re = re.compile('^[ \t]+$', re.MULTILINE)
_leading_whitespace_re = re.compile('(^[ \t]*)(?:[^ \t\n])', re.MULTILINE)

def indentation(text):
    """Remove any common leading whitespace from every line in `text`.

    This can be used to make triple-quoted strings line up with the left
    edge of the display, while still presenting them in the source code
    in indented form.

    Note that tabs and spaces are both treated as whitespace, but they
    are not equal: the lines "  hello" and "\\thello" are
    considered to have no common leading whitespace.  (This behaviour is
    new in Python 2.5; older versions of this module incorrectly
    expanded tabs before searching for common leading whitespace.)
    """
    # Look for the longest leading string of spaces and tabs common to
    # all lines.
    margin = None
    text = _whitespace_only_re.sub('', text)
    indents = _leading_whitespace_re.findall(text)
    for indent in indents:
        if margin is None:
            margin = indent

        # Current line more deeply indented than previous winner:
        # no change (previous winner is still on top).
        elif indent.startswith(margin):
            pass

        # Current line consistent with and no deeper than previous winner:
        # it's the new winner.
        elif margin.startswith(indent):
            margin = indent

        # Find the largest common whitespace between current line and previous
        # winner.
        else:
            for i, (x, y) in enumerate(zip(margin, indent)):
                if x != y:
                    margin = margin[:i]
                    break

    # sanity check (testing/debugging only)
    if 0 and margin:
        for line in text.split("\n"):
            assert not line or line.startswith(margin), \
                   "line = %r, margin = %r" % (line, margin)

    if margin is None:
        return ''
    return margin

def dedent(text, margin):
    if margin:
        text = re.sub(r'(?m)^' + margin, '', text)
    return text
