"""
Translation for LayerEditor package

Usage:
    In file declare::
    from lang_le import gettext as _
"""
import gettext as gt
import os

# pylint: disable=C0103
_d = os.path.dirname(os.path.realpath(__file__))
# pylint: disable=C0103
_t = gt.translation('editor', _d+'/../locale', fallback=True)

def gettext(text):
    """Translate to current lang"""
    return _t.gettext(text)
