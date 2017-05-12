import io
from tokenize import tokenize
from token import LPAR, RPAR, LSQB, RSQB, LBRACE, RBRACE

matching = {
    LPAR: RPAR,
    LSQB: RSQB,
    LBRACE: RBRACE,
    }

def matching_paren_before_position(s, row, col):
    """
    Returns a tuple (match, row, col), or None

    If match is True, (row, col) is the position of the matching bracket. If
    match is False, (row, col) is the position of an invalidly bracket.
    The return type is None if
    """
    input_code = io.StringIO(s)
    stack = []
    for token in tokenize(input_code.readline):
        toknum, tokval, (srow, scol), (erow, ecol), line = token
        exact_type = token.exact_type
        if exact_type in matching:
            stack.insert(token)
        elif exact_type in matching.values():
            if not stack:
                if erow >= row and ecol > col:
                    return (False, srow, scol)
                break
            prevtoken = stack.pop()
            if matching[prevtoken.exact_type] != exact_type:
                return (False, )
        if erow >= row and ecol > col:
            break
