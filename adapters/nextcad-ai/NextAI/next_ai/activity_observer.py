"""Opt-in, local semantic observation of manual FreeCAD document activity.

Only object identity/type and changed property names are retained. Property values,
file paths, labels, drawing contents and chat text are deliberately excluded.
Nothing is sent until the user submits a prompt with observation enabled.
"""
from __future__ import annotations

from collections import deque
import time


class NextCADActivityObserver:
    """Small in-memory observer for manual document and selection changes."""

    def __init__(self, app=None, gui=None, limit: int = 60):
        self._app = app
        self._gui = gui
        self._events = deque(maxlen=max(1, min(int(limit), 120)))
        self._enabled = False
        self._suspended = False

    @staticmethod
    def _safe(value, maximum=80):
        text = str(value or "")
        return "".join(ch for ch in text if ch.isalnum() or ch in "_-. ")[:maximum]

    @classmethod
    def _object_info(cls, obj):
        if obj is None:
            return {}
        return {
            "object": cls._safe(getattr(obj, "Name", "")),
            "type": cls._safe(getattr(obj, "TypeId", "")),
        }

    def _record(self, event, **details):
        if not self._enabled or self._suspended:
            return
        item = {"event": self._safe(event), "at": int(time.time())}
        for key, value in details.items():
            if value is None:
                continue
            if key == "object_info" and isinstance(value, dict):
                item.update(value)
            elif isinstance(value, bool):
                item[key] = value
            elif isinstance(value, int):
                item[key] = value
            elif isinstance(value, str):
                item[key] = self._safe(value, 100)
        self._events.append(item)

    def start(self):
        if self._enabled:
            return True
        if self._app is None:
            import FreeCAD as app
            self._app = app
        if self._gui is None:
            import FreeCADGui as gui
            self._gui = gui
        add_doc = getattr(self._app, "addDocumentObserver", None)
        add_selection = getattr(getattr(self._gui, "Selection", None), "addObserver", None)
        if not callable(add_doc) or not callable(add_selection):
            raise RuntimeError("This FreeCAD version does not expose the document and selection observer APIs.")
        add_doc(self)
        try:
            add_selection(self)
        except Exception:
            remove_doc = getattr(self._app, "removeDocumentObserver", None)
            if callable(remove_doc):
                remove_doc(self)
            raise
        self._enabled = True
        self._record("observation_started")
        return True

    def stop(self):
        if self._enabled:
            remove_selection = getattr(getattr(self._gui, "Selection", None), "removeObserver", None)
            remove_doc = getattr(self._app, "removeDocumentObserver", None)
            if callable(remove_selection):
                try:
                    remove_selection(self)
                except Exception:
                    pass
            if callable(remove_doc):
                try:
                    remove_doc(self)
                except Exception:
                    pass
        self._enabled = False
        self._events.clear()

    def set_suspended(self, suspended: bool):
        self._suspended = bool(suspended)

    def snapshot(self):
        if not self._enabled:
            return {"enabled": False, "events": []}
        active = getattr(self._app, "ActiveDocument", None)
        workbench = ""
        try:
            workbench_obj = self._gui.activeWorkbench()
            workbench = workbench_obj.name() if callable(getattr(workbench_obj, "name", None)) else str(workbench_obj)
        except Exception:
            pass
        selected = []
        try:
            for item in self._gui.Selection.getSelection()[:30]:
                selected.append(self._object_info(item))
        except Exception:
            pass
        return {
            "enabled": True,
            "workbench": self._safe(workbench),
            "document": self._safe(getattr(active, "Name", "")) if active else "",
            "object_count": len(getattr(active, "Objects", []) or []) if active else 0,
            "selection": selected,
            "events": list(self._events),
        }

    # Observer signatures accept *args because callback signatures vary slightly across releases.
    def slotCreatedObject(self, *args):
        obj = args[-1] if args else None
        self._record("object_created", object_info=self._object_info(obj))

    def slotDeletedObject(self, *args):
        obj = args[-1] if args else None
        self._record("object_deleted", object_info=self._object_info(obj))

    def slotChangedObject(self, *args):
        obj = args[-2] if len(args) >= 2 else (args[-1] if args else None)
        prop = args[-1] if len(args) >= 2 else ""
        self._record("object_changed", object_info=self._object_info(obj), property=self._safe(prop))

    def slotRecomputedDocument(self, *args):
        doc = args[-1] if args else None
        self._record("document_recomputed", document=self._safe(getattr(doc, "Name", "")))

    def slotActivatedDocument(self, *args):
        doc = args[-1] if args else None
        self._record("document_activated", document=self._safe(getattr(doc, "Name", "")))

    def slotCreatedDocument(self, *args):
        doc = args[-1] if args else None
        self._record("document_created", document=self._safe(getattr(doc, "Name", "")))

    def slotDeletedDocument(self, *args):
        doc = args[-1] if args else None
        self._record("document_deleted", document=self._safe(getattr(doc, "Name", "")))

    def addSelection(self, doc, obj, sub, point):
        self._record("selection_added", document=self._safe(doc), object=self._safe(obj), subelement=self._safe(sub))

    def removeSelection(self, doc, obj, sub):
        self._record("selection_removed", document=self._safe(doc), object=self._safe(obj), subelement=self._safe(sub))

    def clearSelection(self, doc):
        self._record("selection_cleared", document=self._safe(doc))

    def setSelection(self, doc):
        self._record("selection_set", document=self._safe(doc))
