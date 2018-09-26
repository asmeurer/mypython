"""
Based on prompt_toolkit.tests.test_cli
"""
import sys
import re
from io import StringIO
import linecache
import ast

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input.defaults import create_pipe_input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from ..mypython import (_default_globals, Session, normalize, magic,
    PythonSyntaxValidator, execute_command, getsource, smart_eval, NoResult)
from .. import mypython

from pytest import raises, skip, fixture

_test_globals = _default_globals.copy()

class _TestOutput(DummyOutput):
    def __init__(self):
        self.written_data = ''
        self.written_raw_data = ''

    def write(self, data):
        self.written_data += data

    # Since we use patch_stdout_context(raw=True),
    # things like iTerm2 sequences will go here.
    def write_raw(self, data):
        self.written_raw_data += data

def _run_session_with_text(session, text, close=False):
    assert text.endswith('\n')
    if '\n' in text[:-1]:
        assert text.endswith('\n\n')
    session.input.send_text(text)

    try:
        with session._auto_refresh_context():
            session.default_buffer.reset(Document(session.default))
            result = session.app.run()
        return result
    finally:
        if close:
            session.input.close()

def _history():
    h = InMemoryHistory()
    h.append_string('history1')
    h.append_string('history2')
    h.append_string('history3')
    return h

def keyboard_interrupt_handler(s, f):
    raise KeyboardInterrupt('testing')

TERMINAL_SEQUENCE = re.compile(r'(\x1b.*?\x07)|(\x1b\[.*?m)')

@fixture
def check_output(pytestconfig):
    return _get_check_output()

def _build_test_session():
    _globals = _test_globals.copy()
    _locals = _globals
    _input = create_pipe_input()
    _output = _TestOutput()
    session = Session(_globals=_globals, _locals=_locals, history=_history(),
        input=_input, output=_output, quiet=True)
    return session

def _get_check_output(session=None):
    """
    Fixture to generate a check_output() function with a persistent session.
    """
    session = session or _build_test_session()

    def _test_output(text, *, doctest_mode=False, remove_terminal_sequences=True):
        """
        Test the output from a given input

        IMPORTANT: Only things printed directly to stdout/stderr are tested.
        Things printed via prompt_toolkit (e.g., print_tokens) are not caught.

        For now, the input must be a single command. Use \x1b\n (M-Enter) to keep
        multiple lines in the same input.

        """
        mypython.DOCTEST_MODE = doctest_mode

        custom_stdout = StringIO()
        custom_stderr = StringIO()
        try:
            old_stdout, sys.stdout = sys.stdout, custom_stdout
            old_stderr, sys.stderr = sys.stderr, custom_stderr
            # TODO: Test things printed to this
            old_print_formatted_text = mypython.print_formatted_text
            mypython.print_formatted_text = lambda *args, **kwargs: None

            command = _run_session_with_text(session, text)

            execute_command(command, session, _locals=session._locals, _globals=session._globals)
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr
            mypython.print_formatted_text = old_print_formatted_text

        ret = (custom_stdout.getvalue(), custom_stderr.getvalue())
        if remove_terminal_sequences:
            ret = (TERMINAL_SEQUENCE.sub('', ret[0]), TERMINAL_SEQUENCE.sub('', ret[1]))

        return ret
    return _test_output

def test_run_session_with_text():
    session = _build_test_session()
    assert _run_session_with_text(session, '1 + 1\n') == '1 + 1'
    assert _run_session_with_text(session, ' 1\n') == '1'

def test_autoindent():
    session = _build_test_session()

    # Test all the indent rules
    result = _run_session_with_text(session, """\
    def test():
while True:
if 1:
continue
else:
break
pass
return

""")
    assert result == """\
def test():
    while True:
        if 1:
            continue
        else:
            break
        pass
    return"""

    result = _run_session_with_text(session, """\
(
\t123)

""")
    assert result == """\
(
    123)"""

def test_startup():
    session = _build_test_session()
    session._globals = session._locals = {}
    session.startup()
    # TODO: Test things printed with quiet=False

    assert session._globals.keys() == session._locals.keys() == {'__builtins__', 'In', 'Out', 'PROMPT_NUMBER'}
    assert session.builtins.keys() == {'In', 'Out', 'PROMPT_NUMBER'}
    assert session._globals['PROMPT_NUMBER'] == 1

# Not called test_globals to avoid confusion with _test_globals
def test_test_globals():
    assert _test_globals.keys() == {'__package__', '__loader__',
    '__name__', '__doc__', '__cached__', '__builtins__',
    '__spec__'}
    assert _test_globals['__name__'] == _default_globals['__name__'] == '__main__'
    assert _test_globals['__spec__'] == _default_globals['__package__'] == _default_globals['__cached__'] == None
    import builtins
    assert _test_globals['__builtins__'] is builtins

def test_local_import(check_output):
    out, err = check_output('from .tests import *\n')
    assert out == '\n'
    assert err == \
"""Traceback (most recent call last):
  File "<mypython-1>", line 1, in <module>
    from .tests import *
ImportError: attempted relative import with no known parent package
"""

    out, err = check_output('from .test import *\n')
    assert out == '\n'
    assert err == \
"""Traceback (most recent call last):
  File "<mypython-1>", line 1, in <module>
    from .test import *
ImportError: attempted relative import with no known parent package
"""

def test_builtin_names():
    session = _build_test_session()
    check_output = _get_check_output(session)

    i = 1
    out, err = check_output("In\n")
    assert out == "{1: 'In'}\n\n"
    assert not err
    i += 1
    out, err = check_output("Out\n")
    assert out == "{1: {1: 'In', 2: 'Out'}, 2: {...}}\n\n"
    assert not err

    # If a name is deleted, it is restored, but if it is reassigned, the
    # reassigned name is used.
    for name in ["In", "Out", "_", "__", "___", "PROMPT_NUMBER"]:
        assert name in session._globals
        assert session._globals[name] is session.builtins[name]

        i += 1
        out, err = check_output("del {name}\n".format(name=name))
        assert out == "\n"
        assert err == ""

        i += 1
        out, err = check_output("{name}\n".format(name=name))
        # The prompt number is incremented in the post_command, so it will be
        # one more in the _globals after the command is executed.
        res = session.builtins[name] - 1 if name == 'PROMPT_NUMBER' else session.builtins[name]
        assert session._globals[name] is session.builtins[name]
        assert out == repr(res) + "\n\n", name
        assert err == ""

        # _ name and PROMPT_NUMBER are always updated (we don't attempt to
        # detect if they were changed manually).
        if '_' not in name:
            i += 1
            out, err = check_output("{name} = 1\n".format(name=name))
            assert out == '\n'
            assert err == ''

            i += 1
            out, err = check_output("{name}\n".format(name=name))
            assert out == '1\n\n'
            assert err == ''

            i += 1
            out, err = check_output("del {name}\n".format(name=name))
            assert out == '\n'
            assert err == ''

            i += 1
            out, err = check_output("{name}\n".format(name=name))
            assert out == repr(session._globals[name]) + "\n\n"
            assert err == ""

    # Test PROMPT_NUMBER
    # Prompt number not incremented for error or empty commands
    out, err = check_output("\n")
    assert out == "\n"
    assert err == ""

    out, err = check_output("     \n")
    assert out == "\n"
    assert err == ""

    out, err = check_output("fdjksfldj\n")
    assert out == "\n"
    assert err == """\
Traceback (most recent call last):
  File "<mypython-%d>", line 1, in <module>
    fdjksfldj
NameError: name 'fdjksfldj' is not defined
""" % (i + 1)

    i += 1
    out, err = check_output("PROMPT_NUMBER\n")
    assert out == str(i) + '\n\n'
    assert err == ''

    i += 1
    out, err = check_output("del PROMPT_NUMBER\n")
    assert out == '\n'
    assert err == ''

    i += 1
    out, err = check_output("PROMPT_NUMBER\n")
    assert out == str(i) + '\n\n'
    assert err == ''

    i += 1
    out, err = check_output("PROMPT_NUMBER = 0\n")
    assert out == '\n'
    assert err == ''

    i += 1
    out, err = check_output("PROMPT_NUMBER\n")
    assert out == str(i) + '\n\n'
    assert err == ''

    # Test _
    i += 1
    check_output("1\n")
    i += 1
    check_output("2\n")
    i += 1
    check_output("3\n")
    i += 1
    out, err = check_output("_\n")
    assert out == "3\n\n"
    assert not err

    i += 1
    check_output("1\n")
    i += 1
    check_output("2\n")
    i += 1
    check_output("3\n")
    i += 1
    out, err = check_output("__\n")
    assert out == "2\n\n"
    assert not err

    i += 1
    check_output("1\n")
    i += 1
    check_output("2\n")
    i += 1
    check_output("3\n")
    i += 1
    out, err = check_output("___\n")
    assert out == "1\n\n"
    assert not err

    i += 1
    out, err = check_output("_%d\n" % (i-1))
    assert out == "1\n\n"
    assert not err


def test_normalize(capsys):
    _globals = _locals = _test_globals.copy()

    def _normalize(command):
        return normalize(command, _globals, _locals)

    assert _normalize('1') == '1'
    assert _normalize('  1') == '1'
    assert _normalize('  1  ') == '1'
    assert _normalize('  def test():\n      pass\n') == 'def test():\n    pass'
    normalize_help =  _normalize('test?')
    assert 'myhelp' in normalize_help
    compile(normalize_help, '<test>', 'exec')
    normalize_source = _normalize('test??')
    assert 'getsource' in normalize_source
    compile(normalize_source, '<test>', 'exec')
    assert _normalize('test???') == 'test???'
    assert _normalize('%timeit 1') == magic('%timeit 1')
    assert _normalize('%notacommand') == '%notacommand'
    assert _normalize('%notacommand 1') == '%notacommand 1'

    compile(_normalize('%timeit 1'), '<test>', 'exec')
    compile(_normalize('%timeit'), '<test>', 'exec')
    compile(_normalize('%time 1'), '<test>', 'exec')
    compile(_normalize('%time'), '<test>', 'exec')
    compile(_normalize('%sympy'), '<test>', 'exec')
    compile(_normalize('%sympy 1'), '<test>', 'exec')

    from .. import mypython
    compile(_normalize('%doctest'), '<test>', 'exec')
    assert not mypython.DOCTEST_MODE
    compile(_normalize('%doctest 1'), '<test>', 'exec')
    assert not mypython.DOCTEST_MODE
    compile(_normalize('%debug'), '<test>', 'exec')
    assert not mypython.DEBUG
    compile(_normalize('%debug 1'), '<test>', 'exec')
    assert not mypython.DEBUG

    out, err = capsys.readouterr()
    assert not out
    assert not err

def test_syntax_validator():
    validator = PythonSyntaxValidator()

    def validate(text):
        return validator.validate(Document(text, len(text)))

    def doesntvalidate(text):
        raises(ValidationError, lambda: validate(text))

    # Valid Python
    validate('1')
    validate('  1')
    validate('')
    validate(' ')
    validate('\n')
    validate('def test():\n    pass')
    validate('a = 1')
    validate('  def test():\n      pass')

    # Incomplete multiline Python (also tested in test_multiline.py)
    doesntvalidate('def test():')
    doesntvalidate('"""')
    doesntvalidate('(')
    doesntvalidate('1 + \\')

    # Custom extensions
    validate('test?')
    validate('test??')
    validate('%timeit 1')
    validate('%timeit  1')
    validate('%timeit')
    validate('%timeit?')

    doesntvalidate('test???')
    doesntvalidate('1 2')
    doesntvalidate('a =')
    doesntvalidate('def test():\n')
    doesntvalidate('%notarealmagic')
    doesntvalidate('%notarealmagic 1')
    doesntvalidate('%notarealmagic?')
    doesntvalidate('a b?')
    doesntvalidate('a b??')
    doesntvalidate('%timeit a b')
    doesntvalidate('%timeit a?')
    doesntvalidate('%timeit a??')
    doesntvalidate('%timeit a???')
    doesntvalidate('%timeit  a b')
    doesntvalidate('%timeit  a b?')

def test_getsource():
    session = _build_test_session()
    check_output = _get_check_output(session)
    _globals = session._globals

    out, err = check_output('def test():\nraise ValueError("error")\n\n')

    assert getsource('test', _globals, _globals, ret=True, include_info=False) == """\
def test():
    raise ValueError("error")
"""

    out, err = check_output('class Test:\npass\n\n')
    assert getsource('Test', _globals, _globals, ret=True, include_info=False) == \
        getsource('Test', _globals, _globals, ret=True, include_info=False) == """\
class Test:
    pass
"""

def test_main_loop(check_output):
    assert check_output('\n') == ('\n', '')
    assert check_output('1 + 1\n') == ('2\n\n', '')
    assert check_output('None\n') == ('None\n\n', '')
    assert check_output('a = 1\n') == ('\n', '')

    assert check_output('\n', remove_terminal_sequences=False) == ('\x1b]133;C\x07\n\x1b]133;D;0\x07', '')
    assert check_output('1 + 1\n', remove_terminal_sequences=False) == ('\x1b]133;C\x072\n\n\x1b]133;D;0\x07', '')

    assert check_output('\n', remove_terminal_sequences=False, doctest_mode=True) == ('\x1b]133;C\x07\x1b]133;D;0\x07', '')
    assert check_output('1 + 1\n', remove_terminal_sequences=False, doctest_mode=True) == ('\x1b]133;C\x072\n\x1b]133;D;0\x07', '')

    assert check_output('\n', doctest_mode=True) == ('', '')
    assert check_output('1 + 1\n', doctest_mode=True) == ('2\n', '')
    assert check_output('None\n', doctest_mode=True) == ('', '')
    assert check_output('a = 1\n', doctest_mode=True) == ('', '')

    assert check_output('a = 1\n') == ('\n', '')
    assert check_output('a\n') == ('1\n\n', '')

    # Also tests automatic indentation
    assert check_output('def test():\nreturn 1\n\n') == ('\n', '')
    assert check_output('test()\n') == ('1\n\n', '')

    assert check_output('a = 1;2\n') == ('2\n\n', '')
    assert check_output('1;2\n') == ('2\n\n', '')
    assert check_output('1;a = 2\n') == ('\n', '')
    # \x1b\n == M-Enter
    assert check_output('a = 1\x1b\n2\n\n') == ('2\n\n', '')
    assert check_output('1\x1b\n2\n\n') == ('2\n\n', '')
    assert check_output('1\x1b\na = 2\n\n') == ('\n', '')

    assert check_output('# comment\n') == ('\n', '')

    out, err = check_output('raise ValueError("error")\n')
    assert out == '\n'
    assert err == \
r"""Traceback (most recent call last):
  File "<mypython-20>", line 1, in <module>
    raise ValueError("error")
ValueError: error
"""

    out, err = check_output('raise ValueError("error")\n', doctest_mode=True)
    assert out == ''
    assert err == \
r"""Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ValueError: error
"""

    out, err = check_output('def test():\nraise ValueError("error")\n\n')
    assert (out, err) == ('\n', '')
    out, err = check_output('test()\n')
    assert out == '\n'
    assert err == \
r"""Traceback (most recent call last):
  File "<mypython-21>", line 1, in <module>
    test()
  File "<mypython-20>", line 2, in test
    raise ValueError("error")
ValueError: error
"""

    out, err = check_output('def test():\nraise ValueError("error")\n\n',
         doctest_mode=True)
    assert (out, err) == ('', '')
    out, err = check_output('test()\n', doctest_mode=True)
    assert out == ''
    assert err == \
r"""Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "<stdin>", line 2, in test
ValueError: error
"""

    # Non-eval syntax + last line expr
    out, err = check_output('import os;undefined\n')
    assert out == '\n'
    assert err == \
"""Traceback (most recent call last):
  File "<mypython-22>", line 1, in <module>
    import os;undefined
NameError: name 'undefined' is not defined
"""
    # \x1b\n == M-Enter
    out, err = check_output('import os\x1b\nundefined\n\n')
    assert out == '\n'
    assert err == \
"""Traceback (most recent call last):
  File "<mypython-22>", line 2, in <module>
    undefined
NameError: name 'undefined' is not defined
"""

def test_traceback_exception():
    # Functions from the traceback module shouldn't include any mypython lines
    # \x1b\n = M-Enter. _test_output only works with a single command
    out, err = _test_output('import traceback\x1b\ntry:\nraise ValueError("error")\nexcept:\ntraceback.print_exc()\n\n')
    assert out == '\n'
    assert err == \
r"""Traceback (most recent call last):
  File "<mypython-1>", line 3, in <module>
    raise ValueError("error")
ValueError: error
"""

def test_exceptionhook_catches_recursionerror():
    # Make sure this doesn't crash
    try:
        import numpy, sympy
        numpy, sympy # silence pyflakes
    except ImportError:
        skip("NumPy or SymPy not installed")

    # \x1b\n == M-Enter
    command = """\
import numpy, sympy\x1b
b = numpy.array([sympy.Float(1.1, 30) + sympy.Float(1.1, 30)*sympy.I]*1000)\x1b
numpy.array(b, dtype=float)\x1b

"""
    out, err = _test_output(command)
    assert out == '\n'
    assert "RecursionError" in err
    # assert print_tokens_output == "Warning: RecursionError from mypython_excepthook"

def test_error_magic():
    # Make sure %error shows the full mypython traceback.
    # Here instead of test_magic.py because it tests the exception handling
    out, err = _test_output('%error\n')
    assert out == '\n'
    assert re.match(
r"""Traceback \(most recent call last\):
  File\ ".*/mypython/mypython\.py", line \d+, in execute_command
    command = normalize\(command, _globals, _locals\)
  File ".*/mypython/mypython\.py", line \d+, in normalize
    return magic\(command\)
  File ".*/mypython/magic\.py", line \d+, in magic
    result = MAGICS\[magic_command\]\(rest\)
  File ".*/mypython/magic\.py", line \d+, in error_magic
    raise RuntimeError\("Error magic"\)
RuntimeError: Error magic
"""
# Should include this, but it's printed with print_tokens:

# !!!!!! ERROR from mypython !!!!!!
, err), repr(err)

def test_exception_hiding():
    # Also handled by test_error_magic() above
    out, err = _test_output('raise ValueError\n')
    assert out == '\n'
    # TODO: make sure "ERROR from mypython" is not printed (it wouldn't be
    # included here because it's printed with print_tokens())
    assert err == """\
Traceback (most recent call last):
  File "<mypython-1>", line 1, in <module>
    raise ValueError
ValueError
"""

    out, err = _test_output('%time raise ValueError\n')
    assert out == '\n'
    # TODO: make sure "ERROR from mypython" is not printed (it wouldn't be
    # included here because it's printed with print_tokens())
    assert re.match(
r"""Traceback \(most recent call last\):
  File "<mypython-1>", line \d, in <module>
    res = _smart_eval\('raise ValueError', globals\(\), locals\(\)\)
  File "<mypython>", line 1, in <module>
ValueError""", err), repr(err)

    _globals = _test_globals.copy()

    mybuiltins = startup(_globals, _globals, quiet=True)

    out, err = _test_output('class Test:\ndef __repr__(self):\nraise ValueError\n\n',
        _globals=_globals, mybuiltins=mybuiltins)
    assert out == '\n'
    assert err == ''
    out, err = _test_output('Test()\n', _globals=_globals,
        mybuiltins=mybuiltins)
    assert out == '\n'
    # TODO: make sure "ERROR from mypython" is not printed (it wouldn't be
    # included here because it's printed with print_tokens())
    assert err == """\
Traceback (most recent call last):
  File "<mypython-1>", line 3, in __repr__
    raise ValueError
ValueError
"""

def test_local_scopes():
    out, err = _test_output('[x for x in range(10)]\n')
    assert out == '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]\n\n'
    assert err == ''

    out, err = _test_output('x = range(3); [i for i in x]\n')
    assert out == '[0, 1, 2]\n\n'
    assert err == ''

def test_smart_eval():
    filename = '<smart_eval-test>'

    d = {}
    res = smart_eval('a = 1', d, d, filename=filename)
    assert d['a'] == 1
    assert linecache.getlines('<smart_eval-test>') == ['a = 1']
    assert res == NoResult

    d = {}
    res = smart_eval("", d, d, filename=filename)
    assert res == NoResult

    d = {}
    res = smart_eval("1 + 1", d, d, filename=filename)
    assert res == 2

    d = {}
    res = smart_eval("a = 1\na + 1", d, d, filename=filename)
    assert d['a'] == 1
    assert res == 2

    def _increment_numbers(p):
        class IncrementNumbers(ast.NodeTransformer):
            def visit_Num(self, node):
                return ast.copy_location(ast.Num(node.n + 1), node)

        return IncrementNumbers().visit(p)

    d = {}
    res = smart_eval('a = 1\na + 1', d, d, filename=filename,
        ast_transformer=_increment_numbers)
    assert d['a'] == 2
    assert res == 4
