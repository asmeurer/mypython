"""
Various helpers that are based on Python tokenization

Note that the tokenize module starts the rows at 0 and prompt_toolkit starts
them at 1.
"""

import io
from tokenize import tokenize, TokenError
from token import LPAR, RPAR, LSQB, RSQB, LBRACE, RBRACE, ERRORTOKEN

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
    except TokenError as e:
        pass

    # Anything remaining on the stack is mismatching. Keep the mismatching
    # list in order.
    stack.reverse()
    mismatching = stack + mismatching
    return matching, mismatching
