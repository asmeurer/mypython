from ..keys import BLANK_LINES, LEADING_WHITESPACE, WORD, split_prompts, do_cycle_spacing

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
    test_text = 'abc defGhiJKL_mno012_345N123N'
    assert WORD.findall(test_text) == ['abc', 'def', 'Ghi', 'JKL', 'mno012',
        '345', 'N123', 'N']
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
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN} ⎢     for i in range(10):
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN} ⎢         print(i)

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[5]: b = 2
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN} ⎢
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN} ⎢ c = 2

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[6]: b
    \N{OUTBOX TRAY}\N{OUTBOX TRAY}\N{OUTBOX TRAY}[6]: 2

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[7]: c
    \N{OUTBOX TRAY}\N{OUTBOX TRAY}\N{OUTBOX TRAY}[7]: 2

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[8]: a
    \N{OUTBOX TRAY}\N{OUTBOX TRAY}\N{OUTBOX TRAY}[8]: 1

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[9]: a
    \N{OUTBOX TRAY}\N{OUTBOX TRAY}\N{OUTBOX TRAY}[9]: 1

    \N{INBOX TRAY}\N{INBOX TRAY}\N{INBOX TRAY}[10]: def test():
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢     for i in range(10):
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢         print(i)

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
>>> b = 2
...
... c = 2
>>> b
2
>>> c
2
>>> a
1
>>> a
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

In [5]: b = 2
   ...:
   ...: c = 2

In [6]: b
Out[6]: 2

In [7]: c
Out[7]: 2

In [8]: a
Out[8]: 1

In [9]: a
Out[9]: 1

In [10]: def test():
    ...:     for i in range(10):
    ...:         print(i)
    ...:
    """

    assert split_prompts(mypython_prompts) == split_prompts(python_prompts) == \
    split_prompts(ipython_prompts) == ['a = 1', 'a', 'print(a)',
        'def test():\n    for i in range(10):\n        print(i)', 'b = 2\n\nc = 2', 'b', 'c', 'a', 'a', 'def test():\n    for i in range(10):\n        print(i)']

    assert split_prompts(mypython_prompts, indent='    ') == \
        split_prompts(python_prompts, indent='    ') == \
        split_prompts(ipython_prompts, indent='    ') == \
        ['a = 1', '    a', '    print(a)',
        '    def test():\n        for i in range(10):\n            print(i)', '    b = 2\n\n    c = 2', '    b', '    c', '    a', '    a', '    def test():\n        for i in range(10):\n            print(i)']

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

    assert split_prompts(mypython_magic) == ['%doctest', '%sympy',
        'Integral(x, x)']

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

a''']

    # Test DARK SUNGLASSES, which has spaces between the emoji
    mypython_prompts2 = """
    \N{DARK SUNGLASSES} \N{DARK SUNGLASSES} \N{DARK SUNGLASSES} [1]: def test():
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢     pass

    \N{DARK SUNGLASSES} \N{DARK SUNGLASSES} \N{DARK SUNGLASSES} [2]: a = 1

    \N{DARK SUNGLASSES} \N{DARK SUNGLASSES} \N{DARK SUNGLASSES} [3]: a
    \N{SMILING FACE WITH SUNGLASSES}\N{SMILING FACE WITH SUNGLASSES}\N{SMILING FACE WITH SUNGLASSES}[3]: 1
    """

    assert split_prompts(mypython_prompts2) == [
        'def test():\n    pass', 'a = 1', 'a']

    # Test splitting only continuation (PS2) prompts

    mypython_prompts = """\
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢     for i in range(10):
    \N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}\N{CLAPPING HANDS SIGN}⎢         print(i)
"""

    python_prompts = """\
...     for i in range(10):
...         print(i)
"""

    ipython_prompts = """\
   ...:     for i in range(10):
   ...:         print(i)
"""

    ipython_prompts2 = """\
   ...:     for i in range(10):
   ...:         print(i)
   ...:
"""

    assert split_prompts(mypython_prompts) == \
        split_prompts(python_prompts) == \
        split_prompts(ipython_prompts) == \
        split_prompts(ipython_prompts2) == \
    ['for i in range(10):\n    print(i)']

def test_do_cycle_spacing():
    text, cursor_position = 'a b', 1

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 2)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 2)

    text, cursor_position = 'a  b', 1

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 2)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a  b', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 2)


    text = """\
def test():
    return 1\
"""
    cursor_position = 15

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('def test(): return 1', 12)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('def test():return 1', 11)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ("""\
def test():
    return 1""", 15)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('def test(): return 1', 12)

    text, cursor_position = 'ab', 1

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 2)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('a b', 2)

    text, cursor_position = 'ab', 0

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ab', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ab', 1)

    text, cursor_position = 'ab', 2

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab ', 3)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 2)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 2)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab ', 3)


    # Don't reuse ab, it will use the state from the last test.
    text, cursor_position = 'cd ', 3

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('cd ', 3)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('cd', 2)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('cd ', 3)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('cd ', 3)


    text, cursor_position = ' ab', 0

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ab', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('ab', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ab', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ab', 1)

    text, cursor_position = '', 0

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)


    # Clear the state
    do_cycle_spacing('clear', 0)

    text, cursor_position = ' ', 0

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)

    # Clear the state
    do_cycle_spacing('clear', 0)

    text, cursor_position = ' ', 1

    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == ('', 0)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)
    text, cursor_position = do_cycle_spacing(text, cursor_position)
    assert (text, cursor_position) == (' ', 1)
