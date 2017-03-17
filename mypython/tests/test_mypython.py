"""
Based on prompt_toolkit.tests.test_cli
"""
import sys
import re
from io import StringIO
import time
import threading

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import PipeInput, Input
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from ..mypython import (get_cli, _default_globals, get_eventloop,
    startup, normalize, magic, PythonSyntaxValidator, execute_command)
from .. import mypython
from ..keys import get_registry

from pytest import raises

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
    _globals=None, _locals=None):
    """
    Test the output from a given input

    IMPORTANT: Only things printed directly to stdout/stderr are tested.
    Things printed via prompt_toolkit (e.g., print_tokens) are not caught.
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

        startup(_globals, _locals, quiet=True)

        result, cli = _cli_with_input(_input, _globals=_globals, _locals=_locals)

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

UP_TO_TAB = re.compile('[^\t]*\t?')
def _input_with_tabs(text, _input, sleep_time=0.3):
    """
    Send the input with a pause after tabs, to allow the (async) completion
    happen.

    This should be run in a separate thread, like

        _input = PipeInput()
        threading.Thread(target=lambda: _input_with_tabs(text, _input)
        result, cli = _cli_with_input(_input)

    If the test fails because the completion didn't happen, you may need to
    increase the sleep_time.
    """
    assert text.endswith('\n')

    for t in UP_TO_TAB.findall(text):
        if not t:
            continue
        _input.send_text(t)
        time.sleep(sleep_time)

def _test_completion(text):
    # TODO: Figure out how to test this without executing the command

    # Make sure we have a globals dict with the builtins in it
    _globals = {}
    exec('', _globals)
    assert _globals

    _input = PipeInput()
    t = threading.Thread(target=lambda: _input_with_tabs(text, _input))
    t.start()
    result, cli = _cli_with_input(_input, _globals=_globals)
    return result.text

def test_completions():
    assert _test_completion('copy\t\n') == "copyright"

    # Only 'class' and 'classmethod' start with 'class'
    assert _test_completion("cl\tm\t\n") == 'classmethod'

    # Only 'KeyboardInterrupt' and 'KeyError' start with 'Ke'
    assert _test_completion("Ke\t\n") == 'Key'

    # Test case insensitivity
    assert _test_completion("tru\t\n") == 'True'

    # Test magic completion
    assert _test_completion("%ti\t\n") == "%time"
    # The extra space at the end is removed by the validator
    assert _test_completion("%sy\t\n") == "%sympy"

def test_startup():
    _globals = _locals = {}
    try:
        # TODO: Test things printed to this
        old_print_tokens = mypython.print_tokens = lambda *args, **kwargs: None

        startup(_globals, _locals)
    finally:
        mypython.print_tokens = old_print_tokens

    assert _globals.keys() == _locals.keys() == {'__builtins__', 'In', 'Out'}

# Not called test_globals to avoid confusion with test_globals
def test_test_globals():
    assert _test_globals.keys() == {'__package__', '__loader__',
    '__name__', '__doc__', '__cached__', '__file__', '__builtins__',
    '__spec__'}

def test_normalize():
    _globals = _locals = _test_globals.copy()

    def _normalize(command):
        return normalize(command, _globals, _locals)

    assert _normalize('1') == '1'
    assert _normalize('  1') == '1'
    assert _normalize('  1  ') == '1'
    assert _normalize('  def test():\n      pass\n') == 'def test():\n    pass'
    assert _normalize('test?') == 'help(test)'
    # TODO: Make ?? testable
    assert _normalize('test???') == 'test???'
    assert _normalize('%timeit 1') == magic('%timeit 1')
    assert _normalize('%notacommand') == '%notacommand'
    assert _normalize('%notacommand 1') == '%notacommand 1'

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

    # Incomplete multiline Python (also tested in test_multiline.py)
    validate('def test():')
    validate('"""')
    validate('(')
    validate('1 + \\')

    # Custom extensions
    validate('test?')
    validate('test??')
    validate('%timeit 1')
    validate('%timeit')

    doesntvalidate('test???')
    doesntvalidate('1 2')
    doesntvalidate('a =')
    doesntvalidate('def test():\n')
    doesntvalidate('%notarealmagic')
    doesntvalidate('%notarealmagic 1')

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
    assert _test_output('# comment\n') == ('\n', '')

    out, err = _test_output('raise ValueError("error")\n')
    assert out == '\n'
    assert re.match(
r"""Traceback \(most recent call last\):
  File ".*", line \d+, in execute_command
    res = smart_eval\(command, _globals, _locals\)
  File ".*", line \d+, in smart_eval
    raise e
  File ".*", line \d+, in smart_eval
    exec\(code, _globals, _locals\)
  File "<mypython>", line 1, in <module>
ValueError: error

""", err), err

    _globals = _test_globals.copy()
    out, err = _test_output('def test():raise ValueError("error")\n\n',
        _globals=_globals)
    assert out, err == ('\n\n', '')
    out, err = _test_output('test()\n', _globals=_globals)
    assert out == '\n'
    assert re.match(
r"""Traceback \(most recent call last\):
  File ".*", line \d+, in execute_command
    res = smart_eval\(command, _globals, _locals\)
  File ".*", line \d+, in smart_eval
    res = eval\(code, _globals, _locals\)
  File "<mypython>", line 1, in <module>
  File "<mypython>", line 1, in test
ValueError: error

""", err), err
