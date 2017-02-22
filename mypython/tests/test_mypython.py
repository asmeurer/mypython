"""
Based on prompt_toolkit.tests.test_cli
"""

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import PipeInput
from prompt_toolkit.output import DummyOutput
from prompt_toolkit.document import Document
from prompt_toolkit.validation import ValidationError

from ..mypython import (get_cli, _globals as mypython_globals, get_eventloop,
    startup, normalize, magic, PythonSyntaxValidator, main_loop)
from ..keys import get_registry

from pytest import raises

_test_globals = mypython_globals.copy()

class _TestOutput(DummyOutput):
    def __init__(self):
        self.written_data = []

    def write(self, data):
        self.written_data.append(data)


def _cli_with_input(text, history=None, _globals=None, _locals=None,
    registry=None, eventloop=None, close=True):

    assert text.endswith('\n')

    history = history or _history()
    _globals = _globals or _test_globals.copy()
    _locals = _locals or _globals
    # TODO: Factor this out from main()
    registry = registry or get_registry()
    _input = PipeInput()
    _input.send_text(text)

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


def test_get_cli():
    result, cli = _cli_with_input('1\n')
    assert result.text == '1'

def test_startup():
    _globals = _locals = {}
    startup(_globals, _locals)
    assert _globals.keys() == _locals.keys() == {'__builtins__', 'In', 'Out'}

def test_globals():
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
    from prompt_toolkit.shortcuts import create_eventloop
    import signal
    result, cli = _cli_with_input('1\n', eventloop=create_eventloop(), close=False)
    def handler(s, f): raise KeyboardInterrupt
    signal.signal(signal.SIGALRM, lambda s, f: handler(s, f))
    signal.setitimer(signal.ITIMER_REAL, 1)

    main_loop(cli)
    cli.eventloop.close()
    cli.input.close()
    assert not cli.output.written_data

if __name__ == '__main__':
    test_main_loop()
