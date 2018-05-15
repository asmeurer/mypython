"""
Various helpers that are based on Python tokenization

Note that the tokenize module starts the rows at 1 and prompt_toolkit starts
them at 0.
"""

import io
from itertools import tee
from tokenize import tokenize, TokenError
from token import (LPAR, RPAR, LSQB, RSQB, LBRACE, RBRACE, ERRORTOKEN, STRING,
    COLON, AT, ENDMARKER, DEDENT)

braces = {
    LPAR: RPAR,
    LSQB: RSQB,
    LBRACE: RBRACE,
    }

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
    input_code = io.BytesIO(s.encode('utf-8'))
    stack = []
    matching = []
    mismatching = []
    try:
        for token in tokenize(input_code.readline):
            toknum, tokval, (srow, scol), (erow, ecol), line = token
            exact_type = token.exact_type
            if exact_type == ERRORTOKEN:
                # There is an unclosed string. If we do not break here,
                # tokenize will tokenize the stuff after the string delimiter.
                break
            elif exact_type in braces:
                stack.append(token)
            elif exact_type in braces.values():
                if not stack:
                    mismatching.append(token)
                    continue
                prevtoken = stack.pop()
                if braces[prevtoken.exact_type] == exact_type:
                    matching.append((prevtoken, token))
                else:
                    if allow_intermediary_mismatches:
                        stack.append(prevtoken)
                    else:
                        mismatching.insert(0, prevtoken)
                    mismatching.append(token)
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

def inside_string(s, row, col):
    """
    Returns True if row, col is inside a string in s, False otherwise.

    row starts at 1 and col starts at 0.
    """
    input_code = io.BytesIO(s.encode('utf-8'))
    try:
        for token in tokenize(input_code.readline):
            toknum, tokval, start, end, line = token
            if toknum == ERRORTOKEN:
                # There is an unclosed string. We haven't gotten to the
                # position yet, so it must be inside this string
                return True
            if start <= (row, col) <= end:
                if (row, col) == end:
                    # Position after the end of the string
                    return False
                return toknum == STRING
    except TokenError as e:
        # Uncompleted docstring or braces.
        return 'string' in e.args[0]
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
    # Dedent the text, otherwise, the last token will be DEDENT
    text = text.lstrip()

    input_code = io.BytesIO(text.encode('utf-8'))
    try:
        first = True
        error = False
        for (prev, token) in pairwise(tokenize(input_code.readline)):
            toknum, tokval, start, end, line = token
            if first:
                # The first token is encoding, which will be prev
                if token.exact_type == AT:
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

    except TokenError as e:
        # Uncompleted docstring or braces
        # Multiline unless there is an uncompleted non-docstring
        if not first and toknum == ERRORTOKEN and token.string == '\\':
            return True
        return not error
    except IndentationError:
        return False
    if error:
        return False

    if '\n' in text:
        return True

    return prev.exact_type == COLON
