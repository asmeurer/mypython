def magic(command):
    """
    You can do magic, you can have anything that you desire
    """
    if not ' ' in command:
        magic_command, rest = command, ''
    else:
        magic_command, rest = command.split(' ', 1)

    if magic_command not in MAGICS:
        return command

    return MAGICS[magic_command](rest)

def timeit_magic(rest):
    if not rest:
        return """
print('nothing to time')
pass
"""
    return """
from mypython.timeit import MyTimer, time_format
number, time_taken = MyTimer({rest!r}, globals=globals()).autorange()
print(time_format(number, time_taken))
del MyTimer, time_format
""".format(rest=rest)

def doctest_magic(rest):
    from . import mypython

    if rest:
        print("%doctest takes no arguments")

    mypython.DOCTEST_MODE ^= True

    if mypython.DOCTEST_MODE:
        print("doctest mode enabled")
    else:
        print("doctest mode disabled")

    return ''

MAGICS = {
    '%timeit': timeit_magic,
    '%doctest': doctest_magic,
    }
