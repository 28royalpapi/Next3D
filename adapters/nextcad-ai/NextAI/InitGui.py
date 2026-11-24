"""Attach the native NextAI widget to the dock created by the NextCAD patch."""

try:
    from PySide import QtCore, QtWidgets
except ImportError:
    try:
        from PySide2 import QtCore, QtWidgets
    except ImportError:
        from PySide6 import QtCore, QtWidgets

import FreeCADGui as Gui
from NextAI.next_ai.ui import NextAIWidget


def _attach_next_ai_workspace():
    main_window = Gui.getMainWindow()
    if main_window is None:
        return
    dock = main_window.findChild(QtWidgets.QDockWidget, "NextAIWorkspace")
    if dock is None or dock.property("nextAIWidgetAttached"):
        return
    widget = NextAIWidget(dock)
    dock.setWidget(widget)
    dock.setWindowTitle("Next AI")
    dock.setProperty("nextAIWidgetAttached", True)
    dock.show()


QtCore.QTimer.singleShot(0, _attach_next_ai_workspace)
