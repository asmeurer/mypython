"""
Various helpers that are based on Python tokenization

Note that the tokenize module starts the rows at 1 and prompt_toolkit starts
them at 0.
"""

import io
from itertools import tee
from tokenize import tokenize, TokenError
from token import (LPAR, RPAR, LSQB, RSQB, LBRACE, RBRACE, ERRORTOKEN, STRING,
    COLON, AT, ENDMARKER, DEDENT, NAME)
import ast

braces = {
    LPAR: RPAR,
    LSQB: RSQB,
    LBRACE: RBRACE,
    }

def tokenize_string(s):
    """
    Generator of tokens from the string s
    """
    return tokenize(io.BytesIO(s.encode('utf-8')).readline)

def matching_parens(s, allow_intermediary_mismatches=True):
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
        [(TokenInfo(..., string='[', ...), TokenInfo(..., string=']', start=(1, 8), ...)),
         (TokenInfo(..., string='{', ...), TokenInfo(..., string='}', ...))]
        >>> mismatching
        [TokenInfo(..., string=']', start=(1, 4), ...)]

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
    stack = []
    matching = []
    mismatching = []
    try:
        for tok in tokenize_string(s):
            exact_type = tok.exact_type
            if exact_type == ERRORTOKEN:
                # There is an unclosed string. If we do not break here,
                # tokenize will tokenize the stuff after the string delimiter.
                break
            elif exact_type in braces:
                stack.append(tok)
            elif exact_type in braces.values():
                if not stack:
                    mismatching.append(tok)
                    continue
                prevtok = stack.pop()
                if braces[prevtok.exact_type] == exact_type:
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

def is_multiline_python(text):
    """
    Returns True of text should be considered multiline

    text is considered multiline if typing Enter at the end of text should add
    a newline. Returns False if the text is a single line that can be
    executed. Also returns False in some situations when text has a syntax
    error that cannot be resolved after an additional line, such as EOL in a
    non-docstring literal or an indentation error.

    """
    # Dedent the text, otherwise, the last token will be DEDENT
    text = text.lstrip()

    try:
        first = True
        error = False
        for (prev, tok) in pairwise(tokenize_string(text)):
            toknum, tokval, start, end, line = tok
            if first:
                # The first token is encoding, which will be prev
                if tok.exact_type == AT:
                    # Decorator
                    return True
                first = False
            if toknum == ERRORTOKEN:
                # Error means unclosed (non doc-) string or backslash
                # continuation. We want a backslash continuation to be
                # multiline, which is caught below. Every other case shouldn't
                # be multiline.
                error = True
            if toknum in {ENDMARKER, DEDENT} and prev.type == ERRORTOKEN and prev.string == '\\':
                return True

    except TokenError:
        # Uncompleted docstring or braces
        # Multiline unless there is an uncompleted non-docstring
        if not first and toknum == ERRORTOKEN and tokval == '\\':
            return True
        return not error
    except IndentationError:
        return False
    if error:
        return False

    if '\n' in text:
        return True

    return prev.exact_type == COLON
