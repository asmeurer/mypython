from prompt_toolkit.key_binding.bindings.named_commands import (accept_line,
    self_insert, backward_delete_char, beginning_of_line)
from prompt_toolkit.key_binding.bindings.basic import if_no_repeat
from prompt_toolkit.key_binding.bindings.basic import load_basic_bindings
from prompt_toolkit.key_binding.bindings.emacs import load_emacs_bindings, load_emacs_search_bindings
from prompt_toolkit.key_binding.bindings.mouse import load_mouse_bindings
from prompt_toolkit.key_binding.bindings.cpr import load_cpr_bindings

from prompt_toolkit.key_binding import KeyBindings, merge_key_bindings
from prompt_toolkit.keys import Keys, ALL_KEYS
from prompt_toolkit.filters import Condition, HasSelection, is_searching
from prompt_toolkit.selection import SelectionState
from prompt_toolkit.clipboard import ClipboardData
from prompt_toolkit.input.vt100_parser import ANSI_SEQUENCES
from prompt_toolkit.application.current import get_app
from prompt_toolkit.application import run_in_terminal

from .multiline import (auto_newline, tab_should_insert_whitespace,
    document_is_multiline_python)
from .tokenize import inside_string, matching_parens
from .theme import emoji
from .processors import get_pyflakes_warnings

import re
import subprocess
import sys
import textwrap
import platform

def get_key_bindings():
    # Based on prompt_toolkit.key_binding.defaults.load_key_bindings()
    return merge_key_bindings([
        load_basic_bindings(),

        load_emacs_bindings(),
        load_emacs_search_bindings(),

        load_mouse_bindings(),
        load_cpr_bindings(),

        custom_key_bindings,
    ])

r = custom_key_bindings = KeyBindings()

def warning_positions(event):
    document = event.current_buffer.document
    warnings = get_pyflakes_warnings(document.text, frozenset(event.current_buffer.session._locals))
    positions = []
    for (row, col, msg, m) in warnings:
        # Handle SyntaxErrorMessage which is the same warning for the whole
        # line.
        if m.col != col:
            continue
        pos = document.translate_row_col_to_index(row, col)
        positions.append(pos)
    return positions

@r.add_binding(Keys.Escape, 'p')
def previous_warning(event):
    positions = warning_positions(event)
    buffer = event.current_buffer
    buffer._show_syntax_warning = True
    if not positions or positions[0] >= buffer.cursor_position:
        return
    p = positions[0]
    for pos in positions:
        if pos >= buffer.cursor_position:
            break
        p = pos
    event.current_buffer._show_syntax_warning = True
    event.current_buffer.cursor_position = p

@r.add_binding(Keys.Escape, 'n')
def next_warning(event):
    positions = warning_positions(event)
    buffer = event.current_buffer
    buffer._show_syntax_warning = True
    if not positions or positions[-1] <= buffer.cursor_position:
        return
    p = positions[-1]
    for pos in reversed(positions):
        if pos <= buffer.cursor_position:
            break
        p = pos
    event.current_buffer.cursor_position = p

# This can be removed once
# https://github.com/prompt-toolkit/python-prompt-toolkit/pull/857 is in a
# released version of prompt-toolkit.
ANSI_SEQUENCES['\x1b[1;9A'] = (Keys.Escape, Keys.Up)
ANSI_SEQUENCES['\x1b[1;9B'] = (Keys.Escape, Keys.Down)

@r.add_binding(Keys.Escape, Keys.Up)
def previous_history_search(event):
    event.key_sequence[-1].accept_next = True
    buffer = event.current_buffer
    buffer.history_backward(count=event.arg, history_search=True)

@r.add_binding(Keys.Escape, 'P')
@r.add_binding(Keys.Escape, Keys.Down)
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
    Move to the end
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

WORD = re.compile(r'([a-z0-9]+|[A-Z]{2,}|[a-zA-Z0-9][a-z0-9]*)')
@r.add_binding(Keys.Escape, 'f')
@r.add_binding(Keys.Escape, Keys.Right)
def forward_word(event):
    text = event.current_buffer.text
    cursor_position = event.current_buffer.cursor_position
    for m in WORD.finditer(text):
        if m.end(0) > cursor_position:
            event.current_buffer.cursor_position = m.end(0)
            return
    event.current_buffer.cursor_position = len(text)

@r.add_binding(Keys.Escape, 'b')
@r.add_binding(Keys.Escape, Keys.Left)
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
        event.app.clipboard.set_text(deleted)

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
        event.app.clipboard.set_text(deleted)

def insert_text_ovewrite(buffer, data, move_cursor=True):
    """
    Insert characters at cursor position.

    :param fire_event: Fire `on_text_insert` event. This is mainly used to
        trigger autocompletion while typing.
    """
    # Original text & cursor position.
    otext = buffer.text
    ocpos = buffer.cursor_position

    # Don't overwrite the newline itself. Just before the line ending,
    # it should act like insert mode.
    overwritten_text = otext[ocpos:ocpos + len(data)]

    buffer.text = otext[:ocpos] + data + otext[ocpos + len(overwritten_text):]

    if move_cursor:
        buffer.cursor_position += len(data)

@r.add_binding(Keys.Escape, 'l')
def downcase_word(event):
    buffer = event.current_buffer
    text = buffer.text
    cursor_position = event.current_buffer.cursor_position
    for m in WORD.finditer(text):
        pos = m.end(0)
        if pos > cursor_position:
            word = buffer.document.text[cursor_position:pos]
            insert_text_ovewrite(buffer, word.lower())
            return
    event.current_buffer.cursor_position = len(text)

@r.add_binding(Keys.Escape, 'u')
def upcase_word(event):
    buffer = event.current_buffer
    text = buffer.text
    cursor_position = event.current_buffer.cursor_position
    for m in WORD.finditer(text):
        pos = m.end(0)
        if pos > cursor_position:
            word = buffer.document.text[cursor_position:pos]
            insert_text_ovewrite(buffer, word.upper())
            return
    event.current_buffer.cursor_position = len(text)

@r.add_binding(Keys.Escape, 'c')
def capitalize_word(event):
    buffer = event.current_buffer
    text = buffer.text
    cursor_position = event.current_buffer.cursor_position
    for m in WORD.finditer(text):
        pos = m.end(0)
        if pos > cursor_position:
            word = buffer.document.text[cursor_position:pos]
            # Don't use word.capitalize() because the first character could be
            # - or _
            for i, c in enumerate(word):
                if c.isalnum():
                    word = word[:i] + c.capitalize() + word[i+1:].lower()
                    break
            insert_text_ovewrite(buffer, word)
            return
    event.current_buffer.cursor_position = len(text)

@r.add_binding(Keys.Escape, Keys.ControlF)
def forward_sexp(event):
    buffer = event.current_buffer
    document = buffer.document
    text = buffer.text

    row, col = document.translate_index_to_position(buffer.cursor_position)
    row += 1
    matching, mismatching = matching_parens(text)

    for opening, closing in matching:
        if opening.start == (row, col):
            new_pos = document.translate_row_col_to_index(closing.end[0]-1, closing.end[1])
            buffer.cursor_position = new_pos
            return
    event.app.output.bell()

@r.add_binding(Keys.Escape, Keys.ControlB)
def backward_sexp(event):
    buffer = event.current_buffer
    document = buffer.document
    text = buffer.text

    row, col = document.translate_index_to_position(buffer.cursor_position)
    row += 1
    matching, mismatching = matching_parens(text)

    for opening, closing in matching:
        if closing.end == (row, col):
            new_pos = document.translate_row_col_to_index(opening.start[0]-1, opening.start[1])
            buffer.cursor_position = new_pos
            return
    event.app.output.bell()

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
    event.app.exit(exception=EOFError, style='class:exiting')

@r.add_binding(Keys.ControlC, filter=~is_searching)
def keyboard_interrupt(event):
    event.app.exit(exception=KeyboardInterrupt, style='class:aborting')

is_returnable = Condition(
    lambda: get_app().current_buffer.is_returnable)

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
        # If we are at the end of the buffer, accept unless we are in a
        # docstring
        row, col = document.translate_index_to_position(buffer.cursor_position)
        row += 1
        if multiline and inside_string(text, row, col):
            # We are inside a docstring
            auto_newline(event.current_buffer)
        else:
            accept_line(event)
    elif not multiline:
        # Always accept a single valid line. Also occurs for unclosed single
        # quoted strings (which will give a syntax error)
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
    if pks and getattr(pks[-1], 'accept_next', False) and ((len(pks) == 1 and
        pks[0].key == "up") or (len(pks) == 2 and pks[0].key == "escape"
            and isinstance(pks[1].key, str) and pks[1].key in 'pP')):
        accept_line(event)
    else:
        multiline_enter(event)

@r.add_binding(Keys.Escape, Keys.Enter)
@r.add_binding(Keys.Escape, Keys.ControlJ)
def insert_newline(event):
    auto_newline(event.current_buffer)

@r.add_binding(Keys.ControlO)
def open_line(event):
    event.current_buffer.newline(copy_margin=False)
    event.current_buffer.cursor_left()

# M-[ a g is set to S-Enter in iTerm2 settings
Keys.ShiftEnter = "<Shift-Enter>"
ALL_KEYS.append('<Shift-Enter>')
ANSI_SEQUENCES['\x1b[ag'] = Keys.ShiftEnter
ANSI_SEQUENCES['\x1bOM'] = Keys.ShiftEnter

r.add_binding(Keys.ShiftEnter)(accept_line)

@r.add_binding(Keys.Tab, filter=tab_should_insert_whitespace)
def indent(event):
    """
    When tab should insert whitespace, do that instead of completion.
    """
    # Text before cursor on the line must be whitespace because of the
    # TabShouldInsertWhitespaceFilter.
    before_cursor = event.app.current_buffer.document.current_line_before_cursor
    event.app.current_buffer.insert_text(' '*(4 - len(before_cursor)%4))

LEADING_WHITESPACE = re.compile(r'( *)[^ ]?')
@r.add_binding(Keys.Escape, 'm')
def back_to_indentation(event):
    """
    Move back to the beginning of the line, ignoring whitespace.
    """
    current_line = event.app.current_buffer.document.current_line
    before_cursor = event.app.current_buffer.document.current_line_before_cursor
    indent = LEADING_WHITESPACE.search(current_line)
    if indent:
        event.app.current_buffer.cursor_position -= len(before_cursor) - indent.end(1)

@r.add_binding(Keys.Backspace, save_before=if_no_repeat)
def delete_char_or_unindent(event):
    buffer = event.app.current_buffer
    if (buffer.document.current_line_before_cursor.isspace() and
        len(buffer.document.current_line_before_cursor) >= 4):
        buffer.delete_before_cursor(count=4)
    else:
        backward_delete_char(event)

    # Reset the history search text
    buffer.history_search_text = None

@r.add_binding(Keys.Escape, ' ')
def cycle_spacing(event):
    """
    Based on emacs's cycle-spacing

    On first call, remove all whitespace (if any) from around the cursor and
    replace it with a single space.

    On second call, remove all whitespace.

    On third call, restore the original whitespace and cursor position.
    """
    buffer = event.app.current_buffer

    # Avoid issues when text grows or shrinks below, keeping the cursor
    # position out of sync
    cursor_position = buffer.cursor_position
    buffer.cursor_position = 0

    buffer.text, buffer.cursor_position = do_cycle_spacing(buffer.text, cursor_position)

def do_cycle_spacing(text, cursor_position, state=[]):
    rstripped = text[:cursor_position].rstrip()
    lstripped = text[cursor_position:].lstrip()

    text_before_cursor = text[:cursor_position]

    # The first element of state is the original text. The last element is the
    # buffer text and cursor position as we last left them. If either of those
    # have changed, reset. The state here is global, but that's fine, because
    # we consider any change to be enough clear the state. The worst that
    # happens here is that we resume when we shouldn't if things look exactly
    # as they did where we left off.

    # TODO: Use event.previous_key_sequence instead.
    if state and state[-1] != (text, cursor_position):
        state.clear()

    if len(state) == 0:
        # Replace all whitespace at the cursor (if any) with a single space.
        state.append((text, cursor_position))
        cursor_position -= len(text_before_cursor) - len(rstripped) -1
        text = rstripped + ' ' + lstripped
        state.append((text, cursor_position))
    elif len(state) == 2:
        # Exactly one space at the cursor. Remove it.
        cursor_position -= 1
        text = rstripped + lstripped
        state.append((text, cursor_position))
    elif len(state) == 3:
        # Restore original text and cursor position
        text, cursor_position = state[0]
        state.clear()

    if cursor_position < 0:
        cursor_position = 0
    if cursor_position > len(text):
        cursor_position = len(text)

    return text, cursor_position

@r.add_binding(Keys.ControlX, Keys.ControlO)
def delete_blank_lines(event):
    """
    On blank line, delete all surrounding blank lines, leaving just one.
    On isolated blank line, delete that one.
    On nonblank line, delete any immediately following blank lines.
    """
    buffer = event.app.current_buffer
    document = buffer.document
    lines_up_to_current = document.lines[:document.cursor_position_row+1]
    lines_after_current = document.lines[document.cursor_position_row+1:]

    blank_lines_before = 0
    for line in lines_up_to_current[::-1]:
        if not line.strip():
            blank_lines_before += 1
        else:
            break

    blank_lines_after = 0
    for line in lines_after_current:
        if not line.strip():
            blank_lines_after += 1
        else:
            break

    if not blank_lines_before:
        stripped_before = lines_up_to_current
    else:
        stripped_before = lines_up_to_current[:-blank_lines_before]
    stripped_after = lines_after_current[blank_lines_after:]

    # XXX: Emacs always keeps a newline at the end of the file, but I don't
    # think it matters here.

    if (not blank_lines_before and blank_lines_after) or blank_lines_before + blank_lines_after == 1:
        new_text = '\n'.join(stripped_before + stripped_after)
    elif blank_lines_before + blank_lines_after == 0:
        return
    else:
        buffer.cursor_up(max(blank_lines_before-1, 0))
        new_text = '\n'.join(stripped_before + [''] + stripped_after)

    # Even though we do auto_up, it can be out of bounds from trailing
    # whitespace
    buffer.cursor_position = min(buffer.cursor_position, len(new_text))
    buffer.text = new_text

@r.add_binding(Keys.ControlX, Keys.ControlT)
def transpose_lines(event):
    buffer = event.current_buffer
    document = buffer.document
    row = document.cursor_position_row
    new_lines = document.lines[:]

    if len(new_lines) == 1:
        new_lines.append('')

    if row == 0:
        buffer.cursor_down()
        row += 1

    if row == len(new_lines) - 1:
        new_lines.append('')

    new_lines[row], new_lines[row-1] = new_lines[row-1], new_lines[row]

    buffer.text = '\n'.join(new_lines)

    buffer.cursor_down()
    beginning_of_line(event)

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
    event.app.clipboard.set_data(data)

def system_copy(text):
    if "Linux" in platform.platform():
        copy_command = ['xclip', '-selection', 'c']
    else:
        copy_command = ['pbcopy']

    try:
        # In Python 3.6 we can do this:
        # run(copy_command, input=text, encoding='utf-8', check=True)
        subprocess.run(copy_command, input=text.encode('utf-8'), check=True)
    except FileNotFoundError:
        print("Error: could not find", copy_command[0], file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(copy_command[0], "error:", e, file=sys.stderr)

def system_paste():
    if "Linux" in platform.platform():
        paste_command = ['xsel', '-b']
    else:
        paste_command = ['pbpaste']

    try:
        # In Python 3.6 we can do this:
        # run(paste_command, input=text, encoding='utf-8')
        p = subprocess.run(paste_command, stdout=subprocess.PIPE, check=True)
    except FileNotFoundError:
        print("Error: could not find", paste_command[0], file=sys.stderr)
    except subprocess.CalledProcessError as e:
        print(paste_command[0], "error:", e, file=sys.stderr)

    return p.stdout.decode('utf-8')


@r.add_binding(Keys.ControlX, Keys.ControlW)
def copy_to_clipboard(event):
    if event.current_buffer.document.selection:
        from_, to = event.current_buffer.document.selection_range()
        run_in_terminal(lambda:system_copy(event.current_buffer.document.text[from_:to + 1]))

@r.add_binding(Keys.ControlX, Keys.ControlY)
def paste_from_clipboard(event):
    paste_text_future = run_in_terminal(system_paste)

    event.current_buffer.cut_selection()
    paste_text_future.add_done_callback(lambda future:\
        event.current_buffer.paste_clipboard_data(ClipboardData(future.result())))

# M-[ a b is set to C-S-/ (C-?) in iTerm2 settings
Keys.ControlQuestionmark = "<C-?>"
ALL_KEYS.append("<C-?>")
ANSI_SEQUENCES['\x1b[ab'] = Keys.ControlQuestionmark

# This won't work until
# https://github.com/jonathanslenders/python-prompt-toolkit/pull/484 is
# merged.
@r.add_binding(Keys.ControlQuestionmark, save_before=lambda e: False)
def redo(event):
    event.current_buffer.redo()


# Need to escape all spaces here because of verbose (x) option below
ps1_prompts = [r'>>>\ '] + [re.escape(i) + r'\[\d+\]:\ ' for i, j in emoji] + [r'In\ \[\d+\]:\ ']
ps2_prompts = [r'\.\.\.\ ', '\N{CLAPPING HANDS SIGN}+\\ ?⎢\\ '] + [r'\ *\.\.\.:\ ']
PS1_PROMPTS_RE = re.compile('|'.join(ps1_prompts))
PS2_PROMPTS_RE = re.compile('|'.join(ps2_prompts))
PROMPTED_TEXT_RE = re.compile(r'''(?x) # Multiline and verbose

    (?P<prompt>
        (?P<ps1prompt>{PS1_PROMPTS_RE.pattern})   # Match prompts at the front
      | (?P<ps2prompt>{PS2_PROMPTS_RE.pattern}))? # of the line.

    (?P<noprompt>(?(prompt)\r|))?                 # If the prompt is not
                                                  # matched, this is a special
                                                  # marker group that will match
                                                  # the empty string.
                                                  # Otherwise it will not
                                                  # match (because all \r's
                                                  # have been stripped from
                                                  # the string).

    (?P<line>.*)\n                                # The actual line.
'''.format(PS1_PROMPTS_RE=PS1_PROMPTS_RE, PS2_PROMPTS_RE=PS2_PROMPTS_RE))

def prompt_repl(match):
    r"""
    repl function for re.sub for clearing prompts

    Replaces PS1 prompts with \r and removes PS2 prompts.
    """
    # TODO: Remove the lines with no prompt
    if match.group('ps1prompt') is not None:
        return '\r' + match.group('line') + '\n'
    elif match.group('ps2prompt') is not None:
        return match.group('line') + '\n'
    return ''

def split_prompts(text, indent=''):
    r"""
    Takes text copied from mypython, Python, or IPython session and returns a
    list of inputs

    Outputs are stripped. If no prompts are found the text is left alone.

    The resulting text is indented by indent, except for the first line.

    It is assumed that the text contains no carriage returns (\r).

    Example:

    >>> split_prompts('''
    ... In [1]: a = 1
    ...
    ... In [2]: a
    ... Out[2]: 1
    ...
    ... In [3]: def test():
    ...    ...:     pass
    ...    ...:
    ... ''')
    ['a = 1\n', 'a\n', 'def test():\n    pass\n\n']

    """
    from .mypython import validate_text

    text = textwrap.dedent(text).strip() + '\n'
    text = textwrap.dedent(PROMPTED_TEXT_RE.sub(prompt_repl, text)).lstrip()

    lines = text.split('\r')

    # Make sure multilines end in two newlines
    for i, line in enumerate(lines):
        try:
            validate_text(line)
        except SyntaxError:
            # If there is a syntax error, we can't use the CMD_QUEUE (it
            # breaks things).
            lines = ['\n'.join(lines)]
            break
        if '\n' in line.rstrip():
            lines[i] += '\n'

    lines[0] = textwrap.indent(lines[0], indent,
        # Don't indent the first line, it's already indented
        lambda line, _x=[]: bool(_x or _x.append(1)))

    for i in range(1, len(lines)):
        lines[i] = textwrap.indent(lines[i], indent)

    return lines

@r.add_binding(Keys.BracketedPaste)
def bracketed_paste(event):
    from .mypython import CMD_QUEUE

    data = event.data
    buffer = event.current_buffer

    # Be sure to use \n as line ending.
    # This part is the same as the default binding
    # Some terminals (Like iTerm2) seem to paste \r\n line endings in a
    # bracketed paste. See: https://github.com/ipython/ipython/issues/9737
    data = data.replace('\r\n', '\n')
    data = data.replace('\r', '\n')
    # Replace tabs with four spaces (C-x C-y will still paste the text exactly)
    data = data.replace('\t', '    ')

    # Strip prompts off pasted text
    document = buffer.document
    row, col = document.translate_index_to_position(buffer.cursor_position)
    row += 1
    if not inside_string(event.current_buffer.text, row, col):
        indent = LEADING_WHITESPACE.match(document.current_line_before_cursor)
        current_line_indent = indent.group(1) if indent else ''
        if PS1_PROMPTS_RE.match(data.strip()) or PS2_PROMPTS_RE.match(data.strip()):
            lines = split_prompts(data, current_line_indent)
        else:
            lines = [textwrap.indent(data, current_line_indent,
                # Don't indent the first line, it's already indented
                lambda line, _x=[]: bool(_x or _x.append(1)))]
    else:
        lines = [data]

    event.current_buffer.insert_text(lines[0])

    for text in lines[1:]:
        # TODO: Send last chunk as bracketed paste, so it can be edited
        CMD_QUEUE.append(text)
    if CMD_QUEUE:
        accept_line(event)

@r.add_binding(Keys.Escape, ';')
def comment(event):
    buffer = event.current_buffer
    document = buffer.document

    cursor_line, cursor_col = document.translate_index_to_position(document.cursor_position)
    if document.selection:
        from_, to = document.selection_range()
        start_line, start_col = document.translate_index_to_position(from_ + 1)
        end_line, end_col = document.translate_index_to_position(to - 1)
        end_line += 1
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
    n_changed = 2*(cursor_line - start_line + 1)
    if cursor_col <= min_indent:
        n_changed -= 2

    if uncomment:
        buffer.cursor_position -= n_changed
        buffer.text = new_text
    else:
        buffer.text = new_text
        buffer.cursor_position += n_changed


@r.add_binding(Keys.ControlX, Keys.ControlE)
def open_in_editor(event):
    event.current_buffer.open_in_editor(event.app)

@r.add_binding(Keys.ControlX, Keys.ControlS)
@r.add_binding(Keys.ControlX, Keys.ControlC)
def noop(event):
    pass
