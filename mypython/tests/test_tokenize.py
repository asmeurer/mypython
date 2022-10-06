from ..tokenize import matching_parens, inside_string, is_multiline_python, nwise

import pytest

@pytest.mark.parametrize('tokenizer', [None, 'tokenize', 'parso'])
def test_matching_parens(tokenizer):
    def _tokenvals(matching, mismatching):
        _matching = [tuple(j.start for j in i) for i in matching]
        _mismatching = [i.start for i in mismatching]
        return _matching, _mismatching

    open_close = ['()', '[]', '{}']

    S = "(())"
    for o, c in open_close:
        s = S.replace('(', o).replace(')', c)
        assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
            [
                ((1, 0), (1, 3)),
                ((1, 1), (1, 2))
            ],
            []
        )

    S = "(()))"
    for o, c in open_close:
        s = S.replace('(', o).replace(')', c)
        assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
            [
                ((1, 0), (1, 3)),
                ((1, 1), (1, 2))
            ],
            [(1, 4)]
        )

    S = "((())"
    for o, c in open_close:
        s = S.replace('(', o).replace(')', c)
        assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
            [
                ((1, 1), (1, 4)),
                ((1, 2), (1, 3))
            ],
            [(1, 0)]
        )

    s = "(')"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
        [],
        [(1, 0)]
    )

    s = '(")'
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
        [],
        [(1, 0)]
    )

    s = "('()')"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
        [
            ((1, 0), (1, 5))
        ],
        []
    )

    s = "'('"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == ([], [])

    s = "')'"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == ([], [])

    s = "({})"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
        [
            ((1, 0), (1, 3)),
            ((1, 1), (1, 2)),
        ],
        []
    )

    s = "({)}"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer, allow_intermediary_mismatches=False)) == (
        [],
        [
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
        ]
    )

    s = "({)}"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer, allow_intermediary_mismatches=True)) == (
        [
            ((1, 1), (1, 3))
        ],
        [
            (1, 0),
            (1, 2),
        ]
    )

    s = "({)})"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer, allow_intermediary_mismatches=False)) == (
        [],
        [
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
            (1, 4),
        ]
    )

    s = "({)})"
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer, allow_intermediary_mismatches=True)) == (
        [
            ((1, 0), (1, 4)),
            ((1, 1), (1, 3)),
        ],
        [
            (1, 2),
        ]
    )

    # Test IndentationError
    s = 'def test():\n    if 1:\n  if 1:'
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == (
        [
            ((1, 8), (1, 9)),
        ],
        []
    )

    s = 'f"("'
    assert _tokenvals(*matching_parens(s, tokenizer=tokenizer)) == ([], [])

def test_inside_string():
    def isiq(s, row, col):
        return inside_string(s, row, col, include_quotes=True)

    s = "1 + 2 + 'abc'"
    assert not inside_string(s, 1, 6)
    assert not isiq(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert not isiq(s, 1, 7)
    assert not inside_string(s, 1, 8)
    assert isiq(s, 1, 8)
    assert inside_string(s, 1, 9)
    assert isiq(s, 1, 9)
    assert inside_string(s, 1, 10)
    assert isiq(s, 1, 10)
    assert inside_string(s, 1, 11)
    assert isiq(s, 1, 11)
    assert not inside_string(s, 1, 12)
    assert isiq(s, 1, 12)

    s = '1 + 2 + "abc"'
    assert not inside_string(s, 1, 6)
    assert not isiq(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert not isiq(s, 1, 7)
    assert not inside_string(s, 1, 8)
    assert isiq(s, 1, 8)
    assert inside_string(s, 1, 9)
    assert isiq(s, 1, 9)
    assert inside_string(s, 1, 10)
    assert isiq(s, 1, 10)
    assert inside_string(s, 1, 11)
    assert isiq(s, 1, 11)
    assert not inside_string(s, 1, 12)
    assert isiq(s, 1, 12)

    s = """\
1 + 1
'a'
"""
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert not inside_string(s, 2, 2)
    assert isiq(s, 2, 2)

    s = "1 + 'a"
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)

    s = '1 + "a'
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)

    s = "1 + '''a"
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert not inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert not inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 1, 7)
    assert isiq(s, 1, 7)

    s = '1 + """a'
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert not inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert not inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 1, 7)
    assert isiq(s, 1, 7)

    s = "1 + '''a\nbcd"
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert not inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert not inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 1, 7)
    assert isiq(s, 1, 7)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)

    s = '1 + """a\nbcd'
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert not inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert not inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 1, 7)
    assert isiq(s, 1, 7)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)

    s = "1 + 'a' + '''abc\ndef'''"
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert not inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert not isiq(s, 1, 7)
    assert not inside_string(s, 1, 8)
    assert not isiq(s, 1, 8)
    assert not inside_string(s, 1, 9)
    assert not isiq(s, 1, 9)
    assert not inside_string(s, 1, 10)
    assert isiq(s, 1, 10)
    assert not inside_string(s, 1, 11)
    assert isiq(s, 1, 11)
    assert not inside_string(s, 1, 12)
    assert isiq(s, 1, 12)
    assert inside_string(s, 1, 13)
    assert isiq(s, 1, 13)
    assert inside_string(s, 1, 14)
    assert isiq(s, 1, 14)
    assert inside_string(s, 1, 15)
    assert isiq(s, 1, 15)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert not inside_string(s, 2, 3)
    assert isiq(s, 2, 3)
    assert not inside_string(s, 2, 4)
    assert isiq(s, 2, 4)
    assert not inside_string(s, 2, 5)
    assert isiq(s, 2, 5)
    assert not inside_string(s, 2, 6)
    assert not isiq(s, 2, 6)
    assert not inside_string(s, 2, 7)
    assert not isiq(s, 2, 7)


    s = '1 + "a" + """abc\ndef"""'
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert not inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert not isiq(s, 1, 7)
    assert not inside_string(s, 1, 8)
    assert not isiq(s, 1, 8)
    assert not inside_string(s, 1, 9)
    assert not isiq(s, 1, 9)
    assert not inside_string(s, 1, 10)
    assert isiq(s, 1, 10)
    assert not inside_string(s, 1, 11)
    assert isiq(s, 1, 11)
    assert not inside_string(s, 1, 12)
    assert isiq(s, 1, 12)
    assert inside_string(s, 1, 13)
    assert isiq(s, 1, 13)
    assert inside_string(s, 1, 14)
    assert isiq(s, 1, 14)
    assert inside_string(s, 1, 15)
    assert isiq(s, 1, 15)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert not inside_string(s, 2, 3)
    assert isiq(s, 2, 3)
    assert not inside_string(s, 2, 4)
    assert isiq(s, 2, 4)
    assert not inside_string(s, 2, 5)
    assert isiq(s, 2, 5)
    assert not inside_string(s, 2, 6)
    assert not isiq(s, 2, 6)
    assert not inside_string(s, 2, 7)
    assert not isiq(s, 2, 7)

    s = """\
1, 2
'''
abcd
d
f'''
3
"""
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert not isiq(s, 1, 4)
    assert not inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert not inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert not inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert isiq(s, 2, 3)
    assert inside_string(s, 3, 0)
    assert isiq(s, 3, 0)
    assert inside_string(s, 3, 1)
    assert isiq(s, 3, 1)
    assert inside_string(s, 3, 2)
    assert isiq(s, 3, 2)
    assert inside_string(s, 3, 3)
    assert isiq(s, 3, 3)
    assert inside_string(s, 3, 4)
    assert isiq(s, 3, 4)
    assert inside_string(s, 4, 0)
    assert isiq(s, 4, 0)
    assert inside_string(s, 4, 1)
    assert isiq(s, 4, 1)
    assert inside_string(s, 5, 0)
    assert isiq(s, 5, 0)
    assert not inside_string(s, 5, 1)
    assert isiq(s, 5, 1)
    assert not inside_string(s, 5, 2)
    assert isiq(s, 5, 2)
    assert not inside_string(s, 5, 3)
    assert isiq(s, 5, 3)
    assert not inside_string(s, 5, 4)
    assert not isiq(s, 5, 4)
    assert not inside_string(s, 6, 0)
    assert not isiq(s, 6, 0)
    assert not inside_string(s, 6, 1)
    assert not isiq(s, 6, 1)

    s = '''\
1, 2
"""
abcd
d
f"""
3
'''
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert not isiq(s, 1, 4)
    assert not inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert not inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert not inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert isiq(s, 2, 3)
    assert inside_string(s, 3, 0)
    assert isiq(s, 3, 0)
    assert inside_string(s, 3, 1)
    assert isiq(s, 3, 1)
    assert inside_string(s, 3, 2)
    assert isiq(s, 3, 2)
    assert inside_string(s, 3, 3)
    assert isiq(s, 3, 3)
    assert inside_string(s, 3, 4)
    assert isiq(s, 3, 4)
    assert inside_string(s, 4, 0)
    assert isiq(s, 4, 0)
    assert inside_string(s, 4, 1)
    assert isiq(s, 4, 1)
    assert inside_string(s, 5, 0)
    assert isiq(s, 5, 0)
    assert not inside_string(s, 5, 1)
    assert isiq(s, 5, 1)
    assert not inside_string(s, 5, 2)
    assert isiq(s, 5, 2)
    assert not inside_string(s, 5, 3)
    assert isiq(s, 5, 3)
    assert not inside_string(s, 5, 4)
    assert not isiq(s, 5, 4)
    assert not inside_string(s, 6, 0)
    assert not isiq(s, 6, 0)
    assert not inside_string(s, 6, 1)
    assert not isiq(s, 6, 1)

    s = "[1, 2, 3"
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert not isiq(s, 1, 4)
    assert not inside_string(s, 1, 5)
    assert not isiq(s, 1, 5)

    s = "1 + '\\"
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert isiq(s, 1, 6)

    s = '1 + "\\'
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert isiq(s, 1, 6)

    s = "1 + '\\\nabc"
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert isiq(s, 2, 3)

    s = '1 + "\\\nabc'
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert isiq(s, 2, 3)


    s = "1 + '\\\nabc'"
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert not inside_string(s, 2, 3)
    assert isiq(s, 2, 3)
    assert not inside_string(s, 2, 4)
    assert not isiq(s, 2, 4)

    s = '1 + "\\\nabc"'
    assert not inside_string(s, 1, 0)
    assert not isiq(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not isiq(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not isiq(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not isiq(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert isiq(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert isiq(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert isiq(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert isiq(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert isiq(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert isiq(s, 2, 2)
    assert not inside_string(s, 2, 3)
    assert isiq(s, 2, 3)
    assert not inside_string(s, 2, 4)
    assert not isiq(s, 2, 4)

    s = """def test():
    """
    assert not inside_string(s, 2, 4)
    assert not isiq(s, 2, 4)

    s = """\
a = 1
     b = 2
"""
    assert not inside_string(s, 0, 1)
    assert not isiq(s, 0, 1)

    strings = [
        "1 + r'a'",
        '1 + r"a"',
        '1 + rb"a"',
        "1 + rb'a'",

        '1 + r"""a"""',
        "1 + r'''a'''",
        '1 + rb"""a"""',
        "1 + rb'''a'''",

        '1 + r"a',
        "1 + r'a",
        '1 + rb"a',
        "1 + rb'a",

        '1 + r"""a',
        "1 + r'''a",
        '1 + rb"""a',
        "1 + rb'''a",

        '""',
        "''",
        'r""',
        "r''",
        'rb""',
        "rb''",

        "x + y"
    ]
    for s in strings:
        for i, c in enumerate(s):
            if c in '1 +xy':
                assert not inside_string(s, 1, i)
                assert not isiq(s, 1, i)
            elif c in 'rb"\'':
                assert not inside_string(s, 1, i)
                assert isiq(s, 1, i)
            elif c in 'a':
                assert inside_string(s, 1, i)
                assert isiq(s, 1, i)
            else:
                raise ValueError("Unexpected character in string %s" % c)

def test_is_multiline_python():
    multiline = [
        "def test():",
        "    def test():",
        "@property",
        "  @property"
        "1 + \\",
        "1 + 'a\\",
        '1 + "a\\',
        '"""',
        '"""abc',
        "'''",
        "'''abc",
        "(1 + ",
        "(1 + \\",
        "('1 + \\",
        "{1: 2,",
        "[1, ",
        '("a',
        '["',
        # Anything with a newline is multiline, unless it has an unfinished
        # single quoted string
        "def test():\n    pass",
        '"""\nabc\n"""',
        '"""\n\n',
        'def test():\n    """',
        'def test():\n    "\\',
        'def test():\n    "\\\n1"',

        # Newline take precedence over unclosed single quoted string
        '["\n',
        '["\n]',
        'def test():\n    "',
        'def test():\n    "\\\n1',
        'def test():\n    "\n',
        'def test():\n    "\n1',
    ]

    notmultiline = [
        "'",
        '"',
        "'ab",
        '"ab',
        '1 + "a\\n',
        "1 + 'a\\n",
        '1 + "a\\n"',
        "1 + 'a\\n'",
        '1 + 1',
        '  1 + 1',
        '1 + ',
        '  1 + ',
        '\'"""',
        "\"'''",
        'def test():\n    if 1:\n  if 1:',
    ]

    for s in multiline:
        assert is_multiline_python(s)

    for s in notmultiline:
        assert not is_multiline_python(s)

def test_nwise():
    l = list(range(5))

    assert list(nwise(l, 2)) == [(0, 1), (1, 2), (2, 3), (3, 4)]
    assert list(nwise(l, 3)) == [(0, 1, 2), (1, 2, 3), (2, 3, 4)]
    assert list(nwise(l, 2, fill=True)) == [(None, 0), (0, 1), (1, 2), (2, 3), (3, 4)]
    assert list(nwise(l, 3, fill=True)) == [(None, None, 0), (None, 0, 1), (0, 1, 2), (1, 2, 3), (2, 3, 4)]
