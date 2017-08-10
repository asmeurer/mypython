from ..tokenize import matching_parens, inside_string, is_multiline_python

def test_matching_parens():
    def _tokenvals(matching, mismatching):
        _matching = [tuple(j.start for j in i) for i in matching]
        _mismatching = [i.start for i in mismatching]
        return _matching, _mismatching

    open_close = ['()', '[]', '{}']

    S = "(())"
    for o, c in open_close:
        s = S.replace('(', o).replace(')', c)
        assert _tokenvals(*matching_parens(s)) == (
            [
                ((1, 0), (1, 3)),
                ((1, 1), (1, 2))
            ],
            []
        )

    S = "(()))"
    for o, c in open_close:
        s = S.replace('(', o).replace(')', c)
        assert _tokenvals(*matching_parens(s)) == (
            [
                ((1, 0), (1, 3)),
                ((1, 1), (1, 2))
            ],
            [(1, 4)]
        )

    S = "((())"
    for o, c in open_close:
        s = S.replace('(', o).replace(')', c)
        assert _tokenvals(*matching_parens(s)) == (
            [
                ((1, 1), (1, 4)),
                ((1, 2), (1, 3))
            ],
            [(1, 0)]
        )

    s = "(')"
    assert _tokenvals(*matching_parens(s)) == (
        [],
        [(1, 0)]
    )

    s = '(")'
    assert _tokenvals(*matching_parens(s)) == (
        [],
        [(1, 0)]
    )

    s = "('()')"
    assert _tokenvals(*matching_parens(s)) == (
        [
            ((1, 0), (1, 5))
        ],
        []
    )

    s = "({})"
    assert _tokenvals(*matching_parens(s)) == (
        [
            ((1, 0), (1, 3)),
            ((1, 1), (1, 2)),
        ],
        []
    )

    s = "({)}"
    assert _tokenvals(*matching_parens(s, allow_intermediary_mismatches=False)) == (
        [],
        [
            (1, 0),
            (1, 1),
            (1, 2),
            (1, 3),
        ]
    )

    s = "({)}"
    assert _tokenvals(*matching_parens(s, allow_intermediary_mismatches=True)) == (
        [
            ((1, 1), (1, 3))
        ],
        [
            (1, 0),
            (1, 2),
        ]
    )

    s = "({)})"
    assert _tokenvals(*matching_parens(s, allow_intermediary_mismatches=False)) == (
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
    assert _tokenvals(*matching_parens(s, allow_intermediary_mismatches=True)) == (
        [
            ((1, 0), (1, 4)),
            ((1, 1), (1, 3)),
        ],
        [
            (1, 2),
        ]
    )

def test_inside_string():
    s = "1 + 2 + 'abc'"
    assert not inside_string(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert inside_string(s, 1, 8)
    assert inside_string(s, 1, 9)
    assert inside_string(s, 1, 10)
    assert inside_string(s, 1, 11)
    assert inside_string(s, 1, 12)

    s = '1 + 2 + "abc"'
    assert not inside_string(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert inside_string(s, 1, 8)
    assert inside_string(s, 1, 9)
    assert inside_string(s, 1, 10)
    assert inside_string(s, 1, 11)
    assert inside_string(s, 1, 12)

    s = """\
1 + 1
'a'
"""
    assert not inside_string(s, 1, 1)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)

    s = "1 + 'a"
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)

    s = '1 + "a'
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)

    s = "1 + '''a"
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 1, 7)

    s = '1 + """a'
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 1, 7)

    s = "1 + '''a\nbcd"
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 1, 7)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)

    s = '1 + """a\nbcd'
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 1, 7)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)

    s = "1 + 'a' + '''abc\ndef'''"
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert not inside_string(s, 1, 8)
    assert not inside_string(s, 1, 9)
    assert inside_string(s, 1, 10)
    assert inside_string(s, 1, 11)
    assert inside_string(s, 1, 12)
    assert inside_string(s, 1, 13)
    assert inside_string(s, 1, 14)
    assert inside_string(s, 1, 15)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert inside_string(s, 2, 4)
    assert inside_string(s, 2, 5)
    assert not inside_string(s, 2, 6)
    assert not inside_string(s, 2, 7)


    s = '1 + "a" + """abc\ndef"""'
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert not inside_string(s, 1, 7)
    assert not inside_string(s, 1, 8)
    assert not inside_string(s, 1, 9)
    assert inside_string(s, 1, 10)
    assert inside_string(s, 1, 11)
    assert inside_string(s, 1, 12)
    assert inside_string(s, 1, 13)
    assert inside_string(s, 1, 14)
    assert inside_string(s, 1, 15)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert inside_string(s, 2, 4)
    assert inside_string(s, 2, 5)
    assert not inside_string(s, 2, 6)
    assert not inside_string(s, 2, 7)

    s = """\
1, 2
'''
abcd
d
f'''
3
"""
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert inside_string(s, 3, 0)
    assert inside_string(s, 3, 1)
    assert inside_string(s, 3, 2)
    assert inside_string(s, 3, 3)
    assert inside_string(s, 3, 4)
    assert inside_string(s, 4, 0)
    assert inside_string(s, 4, 1)
    assert inside_string(s, 5, 0)
    assert inside_string(s, 5, 1)
    assert inside_string(s, 5, 2)
    assert inside_string(s, 5, 3)
    assert not inside_string(s, 5, 4)
    assert not inside_string(s, 6, 0)
    assert not inside_string(s, 6, 1)

    s = '''\
1, 2
"""
abcd
d
f"""
3
'''
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert inside_string(s, 3, 0)
    assert inside_string(s, 3, 1)
    assert inside_string(s, 3, 2)
    assert inside_string(s, 3, 3)
    assert inside_string(s, 3, 4)
    assert inside_string(s, 4, 0)
    assert inside_string(s, 4, 1)
    assert inside_string(s, 5, 0)
    assert inside_string(s, 5, 1)
    assert inside_string(s, 5, 2)
    assert inside_string(s, 5, 3)
    assert not inside_string(s, 5, 4)
    assert not inside_string(s, 6, 0)
    assert not inside_string(s, 6, 1)

    s = "[1, 2, 3"
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert not inside_string(s, 1, 3)
    assert not inside_string(s, 1, 4)
    assert not inside_string(s, 1, 5)

    s = "1 + '\\"
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)

    s = '1 + "\\'
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)

    s = "1 + '\\\nabc"
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)

    s = '1 + "\\\nabc'
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)


    s = "1 + '\\\nabc'"
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert not inside_string(s, 2, 4)

    s = '1 + "\\\nabc"'
    assert not inside_string(s, 1, 0)
    assert not inside_string(s, 1, 1)
    assert not inside_string(s, 1, 2)
    assert not inside_string(s, 1, 3)
    assert inside_string(s, 1, 4)
    assert inside_string(s, 1, 5)
    assert inside_string(s, 1, 6)
    assert inside_string(s, 2, 0)
    assert inside_string(s, 2, 1)
    assert inside_string(s, 2, 2)
    assert inside_string(s, 2, 3)
    assert not inside_string(s, 2, 4)

    s = """def test():
    """
    assert not inside_string(s, 2, 4)

    s = """\
a = 1
     b = 2
"""
    assert not inside_string(s, 0, 1)

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
        "{1: 2,",
        "[1, ",
        # Anything with a newline is multiline, unless it has an unfinished
        # single quoted string
        "def test():\n    pass",
        '"""\nabc\n"""',
        '"""\n\n',
        'def test():\n    """',
        'def test():\n    "\\',
        'def test():\n    "\\\n1"',
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
        '("a',
        '\'"""',
        "\"'''",
        'def test():\n    "',
        'def test():\n    "\\\n1',
        'def test():\n    "\n',
        'def test():\n    "\n1',
        'def test():\n    if 1:\n  if 1:',
    ]

    for s in multiline:
        assert is_multiline_python(s)

    for s in notmultiline:
        assert not is_multiline_python(s)
