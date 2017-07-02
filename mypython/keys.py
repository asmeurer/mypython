from prompt_toolkit.key_binding.bindings.named_commands import (accept_line,
    self_insert, backward_delete_char)
from prompt_toolkit.key_binding.bindings.basic import if_no_repeat
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.registry import Registry, MergedRegistry
from prompt_toolkit.keys import Keys, Key
from prompt_toolkit.filters import Condition, HasSelection
from prompt_toolkit.selection import SelectionState
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.terminal.vt100_input import ANSI_SEQUENCES

from .multiline import (auto_newline, TabShouldInsertWhitespaceFilter,
    document_is_multiline_python)
from .tokenize import inside_string

import re
import subprocess
import sys
import textwrap

def get_registry():
    registry = MergedRegistry([
        load_key_bindings(
            enable_abort_and_exit_bindings=True,
            enable_search=True,
            # Not using now but may in the future
            enable_auto_suggest_bindings=True,
            enable_extra_page_navigation=True,
            # Needs prompt_toolkit release
            # enable_open_in_editor=True,
            enable_system_bindings=True,
        ),
        custom_bindings_registry,
    ])

    return registry

r = custom_bindings_registry = Registry()

@r.add_binding(Keys.Escape, 'p')
def previous_history_search(event):
    event.key_sequence[-1].accept_next = True
    buffer = event.current_buffer
    buffer.history_backward(count=event.arg, history_search=True)

@r.add_binding(Keys.Escape, 'P')
def forward_history_search(event):
    event.key_sequence[-1].accept_next = True
    buffer = event.current_buffer
    buffer.history_forward(count=event.arg, history_search=True)

@r.add_binding(Keys.Escape, '<')
def beginning(event):
    """
    Move to the beginning
    """
    event.current_buffer.cursor_position = 0

@r.add_binding(Keys.Escape, '>')
def end(event):
    """
    Move to the beginning
    """
    event.current_buffer.cursor_position = len(event.current_buffer.text)

# Document.start_of_paragraph/end_of_paragraph don't treat multiple blank
# lines correctly.

# Gives the positions right before one or more blank lines
BLANK_LINES = re.compile(r'\S *(\n *\n)')
@r.add_binding(Keys.Escape, '}')
def forward_paragraph(event):
    """
    Move forward one paragraph of text
    """
    text = event.current_buffer.text
    cursor_position = event.current_buffer.cursor_position
    for m in BLANK_LINES.finditer(text):
        if m.start(0) > cursor_position:
            event.current_buffer.cursor_position = m.start(1)+1
            return
    event.current_buffer.cursor_position = len(text)

@r.add_binding(Keys.Escape, '{')
def backward_paragraph(event):
    """
    Move back one paragraph of text
    """
    text = event.current_buffer.text
    cursor_position = event.current_buffer.cursor_position

    for m in BLANK_LINES.finditer(text[::-1]):
        if m.start(0) > len(text) - cursor_position:
            event.current_buffer.cursor_position = len(text) - m.end(1) + 1
            return
    event.current_buffer.cursor_position = 0

WORD = re.compile(r'([a-z0-9]+|[A-Z0-9]{2,}|[a-zA-Z0-9][a-z0-9]+)')
@r.add_binding(Keys.Escape, 'f') # Keys.Escape, Keys.Right
def forward_word(event):
    text = event.current_buffer.text
    cursor_position = event.current_buffer.cursor_position
    for m in WORD.finditer(text):
        if m.end(0) > cursor_position:
            event.current_buffer.cursor_position = m.end(0)
            return

@r.add_binding(Keys.Escape, 'd')
def kill_word(event):
    buffer = event.current_buffer
    text = buffer.text
    cursor_position = buffer.cursor_position
    pos = None
    for m in WORD.finditer(text):
        if m.end(0) > cursor_position:
            pos = m.end(0) - cursor_position
            break

    if pos:
        deleted = buffer.delete(count=pos)
        event.cli.clipboard.set_text(deleted)

@r.add_binding(Keys.Escape, 'b') # Keys.Escape, Keys.Left
def backward_word(event):
    """
    Move back one paragraph of text
    """
    text = event.current_buffer.text
    cursor_position = event.current_buffer.cursor_position

    for m in reversed(list(WORD.finditer(text))):
        if m.start(0) <  cursor_position:
            event.current_buffer.cursor_position = m.start(0)
            return
    event.current_buffer.cursor_position = 0

@r.add_binding(Keys.Escape, Keys.Backspace)
def backward_kill_word(event):
    buffer = event.current_buffer
    text = buffer.text
    cursor_position = buffer.cursor_position

    for m in reversed(list(WORD.finditer(text))):
        if m.start(0) < cursor_position:
            pos = cursor_position - m.start(0)
            break
    else:
        pos = buffer.cursor_position

    if pos:
        deleted = buffer.delete_before_cursor(count=pos)
        event.cli.clipboard.set_text(deleted)

@r.add_binding(Keys.Left)
def left_multiline(event):
    """
    Left that wraps around in multiline.
    """
    if event.current_buffer.cursor_position - event.arg >= 0:
        event.current_buffer.cursor_position -= event.arg

    if getattr(event.current_buffer.selection_state, "shift_arrow", False):
        event.current_buffer.selection_state = None

@r.add_binding(Keys.Right)
def right_multiline(event):
    """
    Right that wraps around in multiline.
    """
    if event.current_buffer.cursor_position + event.arg <= len(event.current_buffer.text):
        event.current_buffer.cursor_position += event.arg

    if getattr(event.current_buffer.selection_state, "shift_arrow", False):
        event.current_buffer.selection_state = None

@r.add_binding(Keys.ControlD)
def exit(event):
    raise EOFError("Control-D")

is_returnable = Condition(
    lambda cli: cli.current_buffer.accept_action.is_returnable)

@r.add_binding(Keys.Enter, filter=is_returnable)
def multiline_enter(event):
    """
    When not in multiline, execute. When in multiline, try to
    intelligently add a newline or execute.
    """
    buffer = event.current_buffer
    document = buffer.document
    multiline = document_is_multiline_python(document)

    text_after_cursor = document.text_after_cursor
    text_before_cursor = document.text_before_cursor
    text = buffer.text
    # isspace doesn't respect vacuous truth
    if (not text_after_cursor or text_after_cursor.isspace()) and text_before_cursor.replace(' ', '').endswith('\n'):
        row, col = document.translate_index_to_position(buffer.cursor_position)
        row += 1
        if multiline and inside_string(text, row, col):
            # We are inside a docstring
            auto_newline(event.current_buffer)
        else:
            accept_line(event)
    elif not multiline:
        accept_line(event)
    else:
        auto_newline(event.current_buffer)

# Always accept the line if the previous key was Up
# Requires https://github.com/jonathanslenders/python-prompt-toolkit/pull/492.
# We don't need a parallel for down because down is already at the end of the
# prompt.

@r.add_binding(Keys.Enter, filter=is_returnable)
def accept_after_history_backward(event):
    pks = event.previous_key_sequence
    if pks and getattr(pks[-1], 'accept_next', False) and ((len(pks) == 1 and isinstance(pks[0].key, Key) and pks[0].key.name == "<Up>") \
       or (len(pks) == 2 and isinstance(pks[0].key, Key) and pks[0].key.name == "<Escape>"
           and isinstance(pks[1].key, str) and pks[1].key in 'pP')):
        accept_line(event)
    else:
        multiline_enter(event)

@r.add_binding(Keys.Escape, Keys.Enter)
def insert_newline(event):
    event.current_buffer.newline()

# M-[ a g is set to S-Enter in iTerm2 settings
Keys.ShiftEnter = Key("<Shift-Enter>")
ANSI_SEQUENCES['\x1b[ag'] = Keys.ShiftEnter

r.add_binding(Keys.ShiftEnter)(accept_line)

@r.add_binding(Keys.Tab, filter=TabShouldInsertWhitespaceFilter())
def indent(event):
    """
    When tab should insert whitespace, do that instead of completion.
    """
    # Text before cursor on the line must be whitespace because of the
    # TabShouldInsertWhitespaceFilter.
    before_cursor = event.cli.current_buffer.document.current_line_before_cursor
    event.cli.current_buffer.insert_text(' '*(4 - len(before_cursor)%4))

LEADING_WHITESPACE = re.compile(r'( *)[^ ]?')
@r.add_binding(Keys.Escape, 'm')
def back_to_indentation(event):
    """
    Move back to the beginning of the line, ignoring whitespace.
    """
    current_line = event.cli.current_buffer.document.current_line
    before_cursor = event.cli.current_buffer.document.current_line_before_cursor
    indent = LEADING_WHITESPACE.search(current_line)
    if indent:
        event.cli.current_buffer.cursor_position -= len(before_cursor) - indent.end(1)

@r.add_binding(Keys.Backspace, save_before=if_no_repeat)
def delete_char_or_unindent(event):
    buffer = event.cli.current_buffer
    if (buffer.document.current_line_before_cursor.isspace() and
        len(buffer.document.current_line_before_cursor) >= 4):
        buffer.delete_before_cursor(count=4)
    else:
        backward_delete_char(event)

@r.add_binding(Keys.Escape, ' ')
def just_one_space(event):
    buffer = event.cli.current_buffer
    rstripped = buffer.text[:buffer.cursor_position].rstrip()
    lstripped = buffer.text[buffer.cursor_position:].lstrip()
    if (len(buffer.text[:buffer.cursor_position]) - len(rstripped) == 1 and
        len(lstripped) == len(buffer.text[buffer.cursor_position:])):
        buffer.cursor_position -= 1
        buffer.text = rstripped + lstripped
    else:
        buffer.cursor_position -= len(buffer.document.text_before_cursor) - len(rstripped) - 1
        buffer.text = rstripped + ' ' + lstripped

# Selection stuff

@r.add_binding(Keys.ShiftLeft)
def select_left(event):
    buffer = event.current_buffer

    if buffer.document.text_before_cursor:
        if not buffer.selection_state:
            buffer.start_selection()
            buffer.selection_state.shift_arrow = True
        buffer.cursor_position -= event.arg

@r.add_binding(Keys.ShiftRight)
def select_right(event):
    buffer = event.current_buffer

    if buffer.document.text_after_cursor:
        if not buffer.selection_state:
            buffer.start_selection()
            buffer.selection_state.shift_arrow = True
        buffer.cursor_position += event.arg

@r.add_binding(Keys.Up)
def auto_up(event):
    buffer = event.current_buffer
    count = event.arg
    if buffer.document.cursor_position_row > 0:
        buffer.cursor_up(count=count)
    elif not buffer.selection_state:
        event.key_sequence[-1].accept_next = True
        buffer.history_backward(count=count)
    if getattr(buffer.selection_state, "shift_arrow", False):
        buffer.selection_state = None

@r.add_binding(Keys.Down)
def auto_down(event):
    buffer = event.current_buffer
    count = event.arg
    if buffer.document.cursor_position_row < buffer.document.line_count - 1:
        buffer.cursor_down(count=count)
    elif not buffer.selection_state:
        buffer.history_forward(count=count)

    if getattr(buffer.selection_state, "shift_arrow", False):
        buffer.selection_state = None

@r.add_binding(Keys.ShiftUp)
def select_line_up(event):
    buffer = event.current_buffer

    if buffer.document.text_before_cursor:
        if not buffer.selection_state:
            buffer.start_selection()
            buffer.selection_state.shift_arrow = True
        up_position = buffer.document.get_cursor_up_position()
        buffer.cursor_position += up_position
        if not up_position:
            buffer.cursor_position = 0

@r.add_binding(Keys.ShiftDown)
def select_line_down(event):
    buffer = event.current_buffer

    if buffer.document.text_after_cursor:
        if not buffer.selection_state:
            buffer.start_selection()
            buffer.selection_state.shift_arrow = True
        down_position = buffer.document.get_cursor_down_position()
        buffer.cursor_position += down_position
        if not down_position:
            buffer.cursor_position = len(buffer.document.text)


# The default doesn't toggle correctly
@r.add_binding(Keys.ControlSpace)
def toggle_selection(event):
    buffer = event.current_buffer

    if buffer.selection_state:
        buffer.selection_state = None
    else:
        buffer.start_selection()

@r.add_binding(Keys.ControlX, 'h')
def select_all(event):
    buffer = event.current_buffer

    buffer.selection_state = SelectionState(len(buffer.document.text))
    buffer.cursor_position = 0

@r.add_binding(Keys.Delete, filter=HasSelection())
@r.add_binding(Keys.Backspace, filter=HasSelection())
def delete_selection(event):
    event.current_buffer.cut_selection()

@r.add_binding(Keys.Any, filter=HasSelection())
def self_insert_and_clear_selection(event):
    event.current_buffer.cut_selection()
    self_insert(event)

@r.add_binding(Keys.ControlK, filter=HasSelection())
@r.add_binding(Keys.ControlU, filter=HasSelection())
def kill_selection(event):
    data = event.current_buffer.cut_selection()
    event.cli.clipboard.set_data(data)

def osx_copy(text):
    try:
        # In Python 3.6 we can do this:
        # run('pbcopy', input=text, encoding='utf-8', check=True)
        subprocess.run('pbcopy', input=text.encode('utf-8'), check=True)
    except FileNotFoundError:
        print("Error: could not find pbcopy", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("pbcopy error:", e, file=sys.stderr)

def osx_paste():
    try:
        # In Python 3.6 we can do this:
        # run('pbcopy', input=text, encoding='utf-8')
        p = subprocess.run('pbpaste', stdout=subprocess.PIPE, check=True)
    except FileNotFoundError:
        print("Error: could not find pbpaste", file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print("pbpaste error:", e, file=sys.stderr)

    return p.stdout.decode('utf-8')

@r.add_binding(Keys.ControlX, Keys.ControlW)
def copy_to_clipboard(event):
    if event.current_buffer.document.selection:
        from_, to = event.current_buffer.document.selection_range()
        event.cli.run_in_terminal(lambda:osx_copy(event.current_buffer.document.text[from_:to + 1]))

@r.add_binding(Keys.ControlX, Keys.ControlY)
def paste_from_clipboard(event):
    paste_text = ''
    def get_paste():
        nonlocal paste_text
        paste_text = osx_paste()

    event.cli.run_in_terminal(get_paste)

    event.current_buffer.cut_selection()
    event.current_buffer.paste_clipboard_data(ClipboardData(paste_text))

# M-[ a b is set to C-S-/ (C-?) in iTerm2 settings
Keys.ControlQuestionmark = Key("<C-?>")
ANSI_SEQUENCES['\x1b[ab'] = Keys.ControlQuestionmark

# This won't work until
# https://github.com/jonathanslenders/python-prompt-toolkit/pull/484 is
# merged.
@r.add_binding(Keys.ControlQuestionmark, save_before=lambda e: False)
def redo(event):
    event.current_buffer.redo()


@r.add_binding(Keys.BracketedPaste)
def bracketed_paste(event):
    from .mypython import emoji

    data = event.data
    buffer = event.current_buffer

    # Be sure to use \n as line ending.
    # This part is the same as the default binding
    # Some terminals (Like iTerm2) seem to paste \r\n line endings in a
    # bracketed paste. See: https://github.com/ipython/ipython/issues/9737
    data = data.replace('\r\n', '\n')
    data = data.replace('\r', '\n')

    # Strip prompts off pasted text
    document = buffer.document
    row, col = document.translate_index_to_position(buffer.cursor_position)
    row += 1
    if not inside_string(event.current_buffer.text, row, col):
        indent = LEADING_WHITESPACE.match(document.current_line_before_cursor)
        current_line_indent = indent.group(1) if indent else ''
        dedented_data = textwrap.dedent(data)
        ps1_prompts = [r'>>> '] + [i*3 + r'\[\d+\]: ' for i, j in emoji]
        ps2_prompts = [r'\.\.\. ', '\N{CLAPPING HANDS SIGN}+⎢']
        PROMPTS_RE = re.compile('|'.join(ps1_prompts + ps2_prompts))
        dedented_data = PROMPTS_RE.sub('', dedented_data)
        data = textwrap.indent(dedented_data, current_line_indent,
            # Don't indent the first line, it's already indented
            lambda line, _x=[]: bool(_x or _x.append(1)))

    event.current_buffer.insert_text(data)

@r.add_binding(Keys.Escape, ';')
def comment(event):
    buffer = event.current_buffer
    document = buffer.document

    cursor_line, _ = document.translate_index_to_position(document.cursor_position)
    if document.selection:
        from_, to = document.selection_range()
        start_line, start_col = document.translate_index_to_position(from_ + 1)
        end_line, end_col = document.translate_index_to_position(to - 1)
    else:
        start_line = cursor_line
        end_line = start_line + 1

    # Get the indentation for the comment delimiters
    min_indent = float('inf')
    for line in document.lines[start_line:end_line]:
        if not line.strip():
            continue
        indent = LEADING_WHITESPACE.search(line)
        if indent:
            min_indent = min(min_indent, len(indent.group(1)))
        else:
            min_indent = 0
        if min_indent == 0:
            break
    if min_indent == float('inf'):
        min_indent = 0

    uncomment = all(not line.strip() or line[min_indent] == '#' for line in document.lines[start_line:end_line])

    lines = []
    for i, line in enumerate(document.lines):
        if start_line <= i < end_line:
            if uncomment:
                lines.append(line[:min_indent] + line[min_indent+2:])
            else:
                lines.append(line[:min_indent] + '# ' + line[min_indent:])
        else:
            lines.append(line)

    new_text = '\n'.join(lines)
    # TODO: Set the cursor position correctly
    if uncomment:
        buffer.cursor_position -= 2*(cursor_line - start_line + 1)
    else:
        buffer.cursor_position += 2*(cursor_line - start_line + 1)
    buffer.text = new_text
