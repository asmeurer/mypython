"""
Based on prompt_toolkit.tests.test_cli
"""

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import PipeInput
from prompt_toolkit.output import DummyOutput

from ..mypython import (get_cli, _globals as mypython_globals, get_eventloop,
    startup, get_manager)

_test_globals = mypython_globals.copy()

def _cli_with_input(text, history=None, _globals=None, _locals=None,
    manager=None):

    assert text.endswith('\n')

    history = history or _history()
    _globals = _globals or _test_globals.copy()
    _locals = _locals or _globals
    # TODO: Factor this out from main()
    manager = manager or get_manager()
    _input = PipeInput()
    _input.send_text(text)

    eventloop = get_eventloop()

    try:
        cli = get_cli(history=history, _globals=_globals, _locals=_locals,
            manager=manager, _input=_input, output=DummyOutput(), eventloop=eventloop)

        result = cli.run()
        return result, cli
    finally:
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
