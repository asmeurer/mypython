from pytest import importorskip, raises

from ..iterm2 import Output, image_sequence
from ..printing import latex_in_terminal

# A two-pixel square GIF
GIF = b'GIF87a\x02\x00\x02\x00\x80\x00\x00\x00\x00\x00\xff\xff\xff,\x00\x00\x00\x00\x02\x00\x02\x00\x00\x02\x02\x84Q\x00;'
GIF_SEQUENCE = '\033]1337;File=inline=1;size=35:R0lGODdhAgACAIAAAAAAAP///ywAAAAAAgACAAACAoRRADs=\a'

def test_Output(capsys):
    with Output():
        print("output")
    assert capsys.readouterr().out == '\033]133;C\aoutput\n\033]133;D;0\a'

def test_Output_command_status(capsys):
    with Output() as o:
        print("output")
        o.set_command_status(1)
    assert capsys.readouterr().out == '\033]133;C\aoutput\n\033]133;D;1\a'

def test_Output_exception(capsys):
    with raises(ZeroDivisionError):
        with Output():
            1/0
    assert capsys.readouterr().out == '\033]133;C\a\033]133;D;0\a'

def test_set_command_status_range():
    o = Output()
    o.set_command_status(0)
    o.set_command_status(255)
    raises(ValueError, o.set_command_status, 256)
    raises(ValueError, o.set_command_status, -1)

def test_image_sequence():
    assert image_sequence(GIF) == GIF_SEQUENCE

def test_latex_in_terminal(capsys, monkeypatch):
    importorskip('sympy')

    def preview(expr, outputbuffer, **kwargs):
        outputbuffer.write(GIF)

    monkeypatch.setattr('sympy.preview', preview)
    latex_in_terminal('x')
    assert capsys.readouterr().out == GIF_SEQUENCE + '\n'
