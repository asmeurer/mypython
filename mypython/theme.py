"""
Based on https://github.com/asmeurer/dotfiles/blob/master/.emacs.d/themes/1am-theme.el

Translated from http://raebear.net/comp/emacscolors.html
"""
from pygments.token import Keyword, Name, Comment, String, Operator
from pygments.style import Style

class OneAM(Style):
    styles = {
        String:              "#ff0000", # red
        String.Doc:          "#ffff00", # yellow
        Comment:             "#ffffff", # white
        Keyword:             "#a020f0", # purple
        Operator.Word:       "#a020f0", # purple
        # Doesn't work for some reason. Should highlight True, False, and
        # None.
        Keyword.Constant:    "#008b8b", # dark cyan
        Name.Builtin:        "#483d8b", # dark slate blue
        Name.Function:       "#0000ff", # Blue1
        Name.Class:          "#228b22", # ForestGreen
        Name.Exception:      "#228b22", # ForestGreen
        Name.Decorator:      "#228b22", # ForestGreen
        # Doesn't work
        Name.Variable:       "#a0522d", # sienna

    }
