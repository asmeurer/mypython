import threading
import time
import re

from prompt_toolkit.input.defaults import create_pipe_input

from ..dircompletion import DirCompleter

from .test_mypython import _run_session_with_text, _build_test_session

import flaky
retry = flaky.flaky(max_runs=5)

UP_TO_TAB = re.compile('[^\t]*\t?')
def _input_with_tabs(text, _input, sleep_time=0.8):
    """
    Send the input with a pause after tabs, to allow the (async) completion
    happen.

    This should be run in a separate thread, like

        with create_pipe_input() as _input:
            session = _build_test_session(_input=_input)
            threading.Thread(target=lambda: _input_with_tabs(text, _input))
            result = _run_session_with_text(session, '', close=True)

    If the test fails because the completion didn't happen, you may need to
    increase the sleep_time.
    """
    assert text.endswith('\n')

    for t in UP_TO_TAB.findall(text):
        if not t:
            continue
        _input.send_text(t)
        time.sleep(sleep_time)

def _test_completion(text, min_time=0.1, max_time=2, runs=3):
    # TODO: Figure out how to test this without executing the command

    # Make sure we have a globals dict with the builtins in it
    _globals = {}
    exec('', _globals)
    assert _globals

    for t in range(runs):
        # Increase sleep time linearly until success
        sleep_time = min_time + (max_time - min_time)*t/(runs - 1)
        with create_pipe_input() as _input:
            session = _build_test_session(_input=_input)
            t = threading.Thread(target=lambda: _input_with_tabs(text, _input, sleep_time=sleep_time))
            t.start()
            result = _run_session_with_text(session, '', close=True)
            if result != text.rstrip():
                break
    return result

@retry
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
    # Completion without %
    assert _test_completion("sym\t\n") == "%sympy"

    # Test Python completion with magic
    assert _test_completion('%time copy\t\n') == '%time copyright'

    # Jedi completion
    assert _test_completion('[1][0].bit\t\n') == '[1][0].bit_length'

    # Jedi completion with magic
    assert _test_completion('%time [1][9].bit\t\n') == '%time [1][9].bit_length'

def test_DirCompletion():
    # Only test the modifications

    completer = DirCompleter({'A': 1., 'b': [], 'B': (), 'abcd': 0, 'ABCD': 0})

    # Case insensitive.
    assert completer.attr_matches('a.')[0] == \
        completer.attr_matches('A.')[0] == \
        completer.attr_matches('A.as')[0] == \
        completer.attr_matches('A.As')[0] == \
        'A.as_integer_ratio'

    assert completer.attr_matches('b.')[0] == 'b.append'
    assert completer.attr_matches('B.')[0] == 'B.count'

    assert set(completer.global_matches('abc')) == set(completer.global_matches('ABC')) == {'abcd', 'ABCD'}

    # Make sure 1. doesn't complete to 1.bit_length
    assert completer.complete('1.', 0) == None

    # Dir completion doesn't happen on imports
    assert completer.complete('import copy.', 0) == None
    assert completer.complete('from copy.', 0) == None

    # Test that dircompletion doesn't evaluate property methods
    class Test:
        @property
        def test(self):
            raise RuntimeError("This exception should not be raised from the completer")

    completer = DirCompleter({'t': Test()})

    assert completer.complete('t.t', 0) == 't.test'
