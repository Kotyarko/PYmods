import BigWorld
from . import ModEvent

__all__ = ('fini',)

fini = ModEvent()


def delayed_hooks():
    global fini
    from gui.app_loader.loader import AppLoader
    from .. import overrideMethod
    fini = overrideMethod(AppLoader, 'fini', fini)  # well, it's not the 'game' itself, but this is called from there


BigWorld.callback(0, delayed_hooks)
