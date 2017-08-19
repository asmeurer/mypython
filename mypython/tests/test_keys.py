from ..keys import BLANK_LINES, LEADING_WHITESPACE, WORD, split_prompts

def test_blank_lines_re():
    test_text = """\
test1
test2


test3

test4
test5  \n\

test6
   \n\

test7

"""
    matches = list(BLANK_LINES.finditer(test_text))

    # Last three characters of the paragraph (not including the newline)
    assert [test_text[m.start(1)-3:m.start(1)] for m in matches] == [
        'st2',
        'st3',
        '5  ',
        'st6',
        'st7',
        ]


def test_leading_indentation_re():
    t = '    1'
    assert LEADING_WHITESPACE.search(t).end(1) == 4

    t = '1'
    # Could change to not match
    assert LEADING_WHITESPACE.search(t) is None or LEADING_WHITESPACE.search(t).end(1) == 0

def test_word_re():
    test_text = 'abc defGhiJKL_mno012_345'
    assert WORD.findall(test_text) == ['abc', 'def', 'Ghi', 'JKL', 'mno012',
    '345']
    assert WORD.findall("list(WORD.finditer('abc def'))[0].end(0)") == \
        ['list', 'WORD', 'finditer', 'abc', 'def', '0', 'end', '0']

def test_split_prompts():
    mypython_prompts = """
    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[1]: a = 1

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[2]: a
    \N{OUTBOX TRAY}\N{OUTBOX TRAY}\N{OUTBOX TRAY}[2]: 1

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[3]: print(a)
    1
    \N{OUTBOX TRAY}\N{OUTBOX TRAY}\N{OUTBOX TRAY}[3]: None

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[4]: def test():
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢    for i in range(10):
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢        print(i)
    """

    python_prompts = """
>>> a = 1
>>> a
1
>>> print(a)
1
>>> def test():
...     for i in range(10):
...         print(i)
    """

    ipython_prompts = """
In [1]: a = 1

In [2]: a
Out[2]: 1

In [3]: print(a)
1

In [4]: def test():
   ...:     for i in range(10):
   ...:         print(i)
   ...:
    """

    assert split_prompts(mypython_prompts) == split_prompts(python_prompts) == \
    split_prompts(ipython_prompts) == ['a = 1\n', 'a\n', 'print(a)\n',
        'def test():\n    for i in range(10):\n        print(i)\n\n']

    assert split_prompts(mypython_prompts, indent='    ') == \
        split_prompts(python_prompts, indent='    ') == \
        split_prompts(ipython_prompts, indent='    ') == \
        ['a = 1\n', '    a\n', '    print(a)\n',
        '    def test():\n        for i in range(10):\n            print(i)\n\n']

    mypython_magic = """
\N{SNAKE}\N{SNAKE}\N{SNAKE}[1]: %doctest
doctest mode enabled
>>> %sympy
    import sympy
    from sympy import *
    x, y, z, t = symbols('x y z t')
    k, m, n = symbols('k m n', integer=True)
    f, g, h = symbols('f g h', cls=Function)
>>> Integral(x, x)
Integral(x, x)
    """

    assert split_prompts(mypython_magic) == ['%doctest\n', '%sympy\n',
        'Integral(x, x)\n']

    syntax_error = """
>>> def test():
...     pass
>>> a a
>>> a = 1
>>> a
1
    """

    assert split_prompts(syntax_error) == ['''\
def test():
    pass


a a

a = 1

a
''']
