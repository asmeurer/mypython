"""
Various helpers that are based on Python tokenization

Note that the tokenize module starts the rows at 1 and prompt_toolkit starts
them at 0.
"""

import io
from itertools import tee
from tokenize import tokenize, TokenError
from token import (LPAR, RPAR, LSQB, RSQB, LBRACE, RBRACE, ERRORTOKEN, STRING,
    COLON, AT, ENDMARKER)

braces = {
    LPAR: RPAR,
    LSQB: RSQB,
    LBRACE: RBRACE,
    }

def matching_parens(s):
    """
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
                    mismatching.append(token)
                    stack.append(prevtoken)
            else:
                continue
    except TokenError:
        pass
    except IndentationError:
        pass

    # Anything remaining on the stack is mismatching. Keep the mismatching
    # list in order.
    stack.reverse()
    mismatching = stack + mismatching
    return matching, mismatching

def inside_string(s, row, col):
    """
    Returns True if row, col is inside a string in s, False otherwise.
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

# From https://docs.python.org/3/library/itertools.html
def pairwise(iterable):
    "s -> (s0,s1), (s1,s2), (s2, s3), ..."
    a, b = tee(iterable)
    next(b, None)
    return zip(a, b)

def is_multiline_python(text):
    if '\n' in text:
        return True

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
            if toknum == ENDMARKER and prev.type == ERRORTOKEN and prev.string == '\\':
                # Unclosed (non doc-) string or backslash continuation.
                # If it is backslash, we want to be multiline, otherwise no.
                return True

    except TokenError:
        # Uncompleted docstring or braces
        return True
    except IndentationError:
        # Shouldn't ever happen, since we have no newlines in text
        return False
    if error:
        return False
    return prev.exact_type == COLON
