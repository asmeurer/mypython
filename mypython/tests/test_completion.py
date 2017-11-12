import threading
import time
import re

from prompt_toolkit.input import PipeInput

from ..mypython import startup

from .test_mypython import _cli_with_input

UP_TO_TAB = re.compile('[^\t]*\t?')
def _input_with_tabs(text, _input, sleep_time=0.7):
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
    mybuiltins = startup(_globals, _globals, quiet=True)

    _input = PipeInput()
    t = threading.Thread(target=lambda: _input_with_tabs(text, _input))
    t.start()
    result, cli = _cli_with_input(_input, _globals=_globals, builtins=mybuiltins)
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

    # Test Python completion with magic
    assert _test_completion('%time copy\t\n')
