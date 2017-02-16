from prompt_toolkit.key_binding.bindings.named_commands import accept_line
from prompt_toolkit.key_binding.defaults import load_key_bindings
from prompt_toolkit.key_binding.registry import Registry, MergedRegistry
from prompt_toolkit.keys import Keys
from prompt_toolkit.filters import Condition


from .multiline import (ends_in_multiline_string,
    document_is_multiline_python, auto_newline,
    TabShouldInsertWhitespaceFilter)

import re

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

# XXX: These are a total hack. We should reimplement this manually, or
# upstream something better.
@r.add_binding(Keys.Escape, 'p')
def previous_history_search(event):
    buffer = event.current_buffer
    prev_enable_history_search = buffer.enable_history_search
    cursor_position = buffer.cursor_position
    buffer.history_search_text = buffer.text[:cursor_position]
    try:
        buffer.enable_history_search = lambda: True
        buffer.history_backward(count=event.arg)
        # Keep it from moving the cursor to the end of the line
        buffer.cursor_position = cursor_position
    finally:
        buffer.enable_history_search = prev_enable_history_search

@r.add_binding(Keys.Escape, 'P')
def forward_history_search(event):
    buffer = event.current_buffer
    prev_enable_history_search = buffer.enable_history_search
    cursor_position = buffer.cursor_position
    buffer.history_search_text = buffer.text[:cursor_position]
    try:
        buffer.enable_history_search = lambda: True
        buffer.history_forward(count=event.arg)
        # Keep it from moving the cursor to the end of the line
        buffer.cursor_position = cursor_position
    finally:
        buffer.enable_history_search = prev_enable_history_search

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
def back_paragraph(event):
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

@r.add_binding(Keys.Left)
def left_multiline(event):
    """
    Left that wraps around in multiline.
    """
    if event.current_buffer.cursor_position - event.arg >= 0:
        event.current_buffer.cursor_position -= event.arg

@r.add_binding(Keys.Right)
def right_multiline(event):
    """
    Right that wraps around in multiline.
    """
    if event.current_buffer.cursor_position + event.arg <= len(event.current_buffer.text):
        event.current_buffer.cursor_position += event.arg

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
    document = event.current_buffer.document
    multiline = document_is_multiline_python(document)

    text_after_cursor = event.current_buffer.document.text_after_cursor
    text_before_cursor = event.current_buffer.document.text_before_cursor
    if ends_in_multiline_string(document):
        auto_newline(event.current_buffer)
    elif not multiline:
        accept_line(event)
    # isspace doesn't respect vacuous truth
    elif (not text_after_cursor or text_after_cursor.isspace()) and text_before_cursor.replace(' ', '').endswith('\n'):
        accept_line(event)
    else:
        auto_newline(event.current_buffer)

@r.add_binding(Keys.Escape, Keys.Enter)
def insert_newline(event):
    event.current_buffer.newline()

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
