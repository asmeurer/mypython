"""
Based on prompt_toolkit.tests.test_cli
"""
import sys
import re
from io import StringIO
import linecache
import ast

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import PipeInput, Input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from ..mypython import (get_cli, _default_globals, get_eventloop,
    startup, normalize, magic, PythonSyntaxValidator, execute_command,
    getsource, smart_eval, NoResult)
from .. import mypython
from ..keys import get_registry

from pytest import raises, skip

_test_globals = _default_globals.copy()

class _TestOutput(DummyOutput):
    def __init__(self):
        self.written_data = ''
        self.written_raw_data = ''

    def write(self, data):
        self.written_data += data

    # Since we use patch_stdout_context(raw=True) (but only for cli.run()),
    # things like iTerm2 sequences will go here.
    def write_raw(self, data):
        self.written_raw_data += data

def _cli_with_input(text, history=None, _globals=None, _locals=None,
    registry=None, eventloop=None, close=True):

    if isinstance(text, Input):
        _input = text
    else:
        assert text.endswith('\n')
        if '\n' in text[:-1]:
            assert text.endswith('\n\n')
        _input = PipeInput()
        _input.send_text(text)

    history = history or _history()
    _globals = _globals or _test_globals.copy()
    _locals = _locals or _globals
    # TODO: Factor this out from main()
    registry = registry or get_registry()

    eventloop = eventloop or get_eventloop()

    try:
        cli = get_cli(history=history, _globals=_globals, _locals=_locals,
            registry=registry, _input=_input, output=_TestOutput(), eventloop=eventloop)
        result = cli.run()
        return result, cli
    finally:
        if close:
            eventloop.close()
            _input.close()

def _history():
    h = InMemoryHistory()
    h.append('history1')
    h.append('history2')
    h.append('history3')
    return h

def keyboard_interrupt_handler(s, f):
    raise KeyboardInterrupt('testing')

TERMINAL_SEQUENCE = re.compile(r'(\x1b.*?\x07)|(\x1b\[.*?m)')

def _test_output(_input, *, doctest_mode=False, remove_terminal_sequences=True,
    _globals=None, _locals=None, prompt_number=None):
    """
    Test the output from a given input

    IMPORTANT: Only things printed directly to stdout/stderr are tested.
    Things printed via prompt_toolkit (e.g., print_tokens) are not caught.

    For now, the input must be a single command. Use \x1b\n (M-Enter) to keep
    multiple lines in the same input.
    """
    mypython.DOCTEST_MODE = doctest_mode

    _globals = _globals or  _test_globals.copy()
    _locals = _locals or _globals

    custom_stdout = StringIO()
    custom_stderr = StringIO()
    try:
        old_stdout, sys.stdout = sys.stdout, custom_stdout
        old_stderr, sys.stderr = sys.stderr, custom_stderr
        # TODO: Test things printed to this
        old_print_tokens = mypython.print_tokens = lambda *args, **kwargs: None

        if not prompt_number:
            startup(_globals, _locals, quiet=True)

        result, cli = _cli_with_input(_input, _globals=_globals, _locals=_locals)
        if prompt_number is not None:
            cli.prompt_number = prompt_number

        if isinstance(result, Document):  # Backwards-compatibility.
            command = result.text
        else:
            command = result

        execute_command(command, cli, _locals=_locals, _globals=_globals)
    finally:
        sys.stdout = old_stdout
        sys.stderr = old_stderr
        mypython.print_tokens = old_print_tokens

    ret = (custom_stdout.getvalue(), custom_stderr.getvalue())
    if remove_terminal_sequences:
        ret = (TERMINAL_SEQUENCE.sub('', ret[0]), TERMINAL_SEQUENCE.sub('', ret[1]))

    return ret

def test_get_cli():
    result, cli = _cli_with_input('1\n')
    assert result.text == '1'

def test_autoindent():
        # Test all the indent rules
    result, cli = _cli_with_input("""\
    def test():
while True:
if 1:
continue
else:
break
pass
return

""")
    assert result.text == """\
def test():
    while True:
        if 1:
            continue
        else:
            break
        pass
    return"""

    result, cli = _cli_with_input("""\
(
\t123)

""")
    assert result.text == """\
(
    123)"""

def test_startup():
    _globals = _locals = {}
    try:
        # TODO: Test things printed to this
        old_print_tokens = mypython.print_tokens = lambda *args, **kwargs: None

        startup(_globals, _locals)
    finally:
        mypython.print_tokens = old_print_tokens

    assert _globals.keys() == _locals.keys() == {'__builtins__', 'In', 'Out', 'PROMPT_NUMBER'}
    assert _globals['PROMPT_NUMBER'] == 1

# Not called test_globals to avoid confusion with _test_globals
def test_test_globals():
    assert _test_globals.keys() == {'__package__', '__loader__',
    '__name__', '__doc__', '__cached__', '__file__', '__builtins__',
    '__spec__'}
    assert _test_globals['__name__'] == _default_globals['__name__'] == '__main__'

def test_builtin_names():
    _globals = _test_globals.copy()

    startup(_globals, _globals)

    i = 1
    out, err = _test_output("In\n", _globals=_globals, prompt_number=i)
    assert out == "{1: 'In'}\n\n"
    assert not err
    i += 1
    out, err = _test_output("Out\n", _globals=_globals, prompt_number=i)
    assert out == "{1: {1: 'In', 2: 'Out'}, 2: {...}}\n\n"
    assert not err

    for name in ["In", "Out", "_", "__", "___"]:
        assert name in _globals

        i += 1
        out, err = _test_output("del {name}\n".format(name=name),
            _globals=_globals, prompt_number=i)
        assert out == "\n"
        assert err == ""

        i += 1
        out, err = _test_output("{name} = 1\n".format(name=name),
            _globals=_globals, prompt_number=i)
        assert out == '\n'
        assert err == ''

        i += 1
        out, err = _test_output("{name}\n".format(name=name),
            _globals=_globals, prompt_number=i)
        assert out == '1\n\n'
        assert err == ''

        i += 1
        out, err = _test_output("del {name}\n".format(name=name),
            _globals=_globals, prompt_number=i)
        assert out == '\n'
        assert err == ''

    i += 1
    out, err = _test_output("PROMPT_NUMBER\n", _globals=_globals, prompt_number=i)
    assert out == str(i) + '\n\n'
    assert err == ''

    i += 1
    out, err = _test_output("del PROMPT_NUMBER\n", _globals=_globals, prompt_number=i)
    assert out == '\n'
    assert err == ''

    i += 1
    out, err = _test_output("PROMPT_NUMBER\n", _globals=_globals, prompt_number=i)
    assert out == str(i) + '\n\n'
    assert err == ''

    i += 1
    out, err = _test_output("PROMPT_NUMBER = 0\n", _globals=_globals, prompt_number=i)
    assert out == '\n'
    assert err == ''

    i += 1
    out, err = _test_output("PROMPT_NUMBER\n", _globals=_globals, prompt_number=i)
    assert out == str(i) + '\n\n'
    assert err == ''

    i += 1
    _test_output("1\n", _globals=_globals, prompt_number=i)
    i += 1
    _test_output("2\n", _globals=_globals, prompt_number=i)
    i += 1
    _test_output("3\n", _globals=_globals, prompt_number=i)
    i += 1
    out, err = _test_output("_\n", _globals=_globals, prompt_number=i)
    assert out == "3\n\n"
    assert not err

    i += 1
    _test_output("1\n", _globals=_globals, prompt_number=i)
    i += 1
    _test_output("2\n", _globals=_globals, prompt_number=i)
    i += 1
    _test_output("3\n", _globals=_globals, prompt_number=i)
    i += 1
    out, err = _test_output("__\n", _globals=_globals, prompt_number=i)
    assert out == "2\n\n"
    assert not err

    i += 1
    _test_output("1\n", _globals=_globals, prompt_number=i)
    i += 1
    _test_output("2\n", _globals=_globals, prompt_number=i)
    i += 1
    _test_output("3\n", _globals=_globals, prompt_number=i)
    i += 1
    out, err = _test_output("___\n", _globals=_globals, prompt_number=i)
    assert out == "1\n\n"
    assert not err

    i += 1
    out, err = _test_output("_%d\n" % (i-1), _globals=_globals, prompt_number=i)
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
    _globals = _test_globals.copy()
    out, err = _test_output('def test():\nraise ValueError("error")\n\n',
        _globals=_globals)

    assert getsource('test', _globals, _globals, ret=True, include_info=False) == """\
def test():
    raise ValueError("error")
"""

    out, err = _test_output('class Test:\npass\n\n', _globals=_globals, prompt_number=2)
    assert getsource('Test', _globals, _globals, ret=True, include_info=False) == \
        getsource('Test', _globals, _globals, ret=True, include_info=False) == """\
class Test:
    pass
"""

def test_main_loop():
    assert _test_output('\n', remove_terminal_sequences=False) == ('\x1b]133;C\x07\n\x1b]133;D;0\x07', '')
    assert _test_output('1 + 1\n', remove_terminal_sequences=False) == ('\x1b]133;C\x072\n\n\x1b]133;D;0\x07', '')

    assert _test_output('\n', remove_terminal_sequences=False, doctest_mode=True) == ('\x1b]133;C\x07\x1b]133;D;0\x07', '')
    assert _test_output('1 + 1\n', remove_terminal_sequences=False, doctest_mode=True) == ('\x1b]133;C\x072\n\x1b]133;D;0\x07', '')

    assert _test_output('\n') == ('\n', '')
    assert _test_output('1 + 1\n') == ('2\n\n', '')
    assert _test_output('None\n') == ('None\n\n', '')
    assert _test_output('a = 1\n') == ('\n', '')

    assert _test_output('\n', doctest_mode=True) == ('', '')
    assert _test_output('1 + 1\n', doctest_mode=True) == ('2\n', '')
    assert _test_output('None\n', doctest_mode=True) == ('', '')
    assert _test_output('a = 1\n', doctest_mode=True) == ('', '')

    _globals = _test_globals.copy()
    assert _test_output('a = 1\n', _globals=_globals) == ('\n', '')
    assert _test_output('a\n', _globals=_globals) == ('1\n\n', '')

    _globals = _test_globals.copy()
    # Also tests automatic indentation
    assert _test_output('def test():\nreturn 1\n\n', _globals=_globals) == ('\n', '')
    assert _test_output('test()\n', _globals=_globals) == ('1\n\n', '')

    assert _test_output('a = 1;2\n') == ('2\n\n', '')
    assert _test_output('1;2\n') == ('2\n\n', '')
    assert _test_output('1;a = 2\n') == ('\n', '')
    # \x1b\n == M-Enter
    assert _test_output('a = 1\x1b\n2\n\n') == ('2\n\n', '')
    assert _test_output('1\x1b\n2\n\n') == ('2\n\n', '')
    assert _test_output('1\x1b\na = 2\n\n') == ('\n', '')

    assert _test_output('# comment\n') == ('\n', '')

    out, err = _test_output('raise ValueError("error")\n')
    assert out == '\n'
    assert err == \
r"""Traceback (most recent call last):
  File "<mypython-1>", line 1, in <module>
    raise ValueError("error")
ValueError: error
"""

    out, err = _test_output('raise ValueError("error")\n', doctest_mode=True)
    assert out == ''
    assert err == \
r"""Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
ValueError: error
"""

    _globals = _test_globals.copy()
    out, err = _test_output('def test():\nraise ValueError("error")\n\n',
        _globals=_globals)
    assert (out, err) == ('\n', '')
    out, err = _test_output('test()\n', _globals=_globals, prompt_number=2)
    assert out == '\n'
    assert err == \
r"""Traceback (most recent call last):
  File "<mypython-2>", line 1, in <module>
    test()
  File "<mypython-1>", line 2, in test
    raise ValueError("error")
ValueError: error
"""

    _globals = _test_globals.copy()
    out, err = _test_output('def test():\nraise ValueError("error")\n\n',
        _globals=_globals, doctest_mode=True)
    assert (out, err) == ('', '')
    out, err = _test_output('test()\n', _globals=_globals, doctest_mode=True, prompt_number=2)
    assert out == ''
    assert err == \
r"""Traceback (most recent call last):
  File "<stdin>", line 1, in <module>
  File "<stdin>", line 2, in test
ValueError: error
"""

    # Non-eval syntax + last line expr
    _globals = _test_globals.copy()
    out, err = _test_output('import os;undefined\n', _globals=_globals)
    assert out == '\n'
    assert err == \
"""Traceback (most recent call last):
  File "<mypython-1>", line 1, in <module>
    import os;undefined
NameError: name 'undefined' is not defined
"""
    # \x1b\n == M-Enter
    out, err = _test_output('import os\x1b\nundefined\n\n', _globals=_globals)
    assert out == '\n'
    assert err == \
"""Traceback (most recent call last):
  File "<mypython-1>", line 2, in <module>
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
    _globals = _test_globals.copy()
    out, err = _test_output(command, _globals=_globals)
    assert out == '\n'
    assert "RecursionError" in err
    # assert print_tokens_output == "Warning: RecursionError from mypython_excepthook"

def test_error_magic():
    # Make sure %error shows the full mypython traceback.
    # Here instead of test_magic.py because it tests the exception handling
    _globals = _test_globals.copy()
    out, err = _test_output('%error\n', _globals=_globals)
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

def test_local_scopes():
    _globals = _test_globals.copy()
    out, err = _test_output('[x for x in range(10)]\n', _globals=_globals)
    assert out == '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9]\n\n'
    assert err == ''

    _globals = _test_globals.copy()
    out, err = _test_output('x = range(3); [i for i in x]\n', _globals=_globals)
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
