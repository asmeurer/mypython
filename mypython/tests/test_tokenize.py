from pytest import raises

from ..tokenize import inside_string

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
    raises(ValueError, lambda: inside_string(s, 2, 7))


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
    raises(ValueError, lambda: inside_string(s, 2, 7))

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
