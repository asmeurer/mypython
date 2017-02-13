"""
Based on prompt_toolkit.tests.test_cli
"""

from prompt_toolkit.history import InMemoryHistory
from prompt_toolkit.input import PipeInput
from prompt_toolkit.key_binding.manager import KeyBindingManager
from prompt_toolkit.output import DummyOutput

from ..mypython import get_cli, _globals as mypython_globals, get_eventloop

def _cli_with_input(text, history=None, _globals=None, _locals=None,
    manager=None):

    assert text.endswith('\n')

    history = history or _history()
    _globals = _globals or mypython_globals
    _locals = _locals or _globals
    # TODO: Factor this out from main()
    manager = manager or KeyBindingManager.for_prompt()
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
