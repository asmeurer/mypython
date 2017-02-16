from ..keys import BLANK_LINES, LEADING_WHITESPACE

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


def test_leading_indentation():
    t = '    1'
    assert LEADING_WHITESPACE.search(t).end(1) == 4

    t = '1'
    # Could change to not match
    assert LEADING_WHITESPACE.search(t) is None or LEADING_WHITESPACE.search(t).end(1) == 0
