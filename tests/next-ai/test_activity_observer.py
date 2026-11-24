from __future__ import annotations

import sys
import unittest
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
ADAPTER = ROOT / "adapters/nextcad-ai/NextAI"
sys.path.insert(0, str(ADAPTER))

from next_ai.activity_observer import NextCADActivityObserver


class FakeSelection:
    def __init__(self):
        self.observer = None
        self.selected = []

    def addObserver(self, observer):
        self.observer = observer

    def removeObserver(self, observer):
        if self.observer is observer:
            self.observer = None

    def getSelection(self):
        return self.selected


class ActivityObserverTests(unittest.TestCase):
    def make_observer(self):
        doc = SimpleNamespace(Name="Document", Objects=[object(), object()])
        app = SimpleNamespace(ActiveDocument=doc)
        app.addDocumentObserver = lambda observer: setattr(app, "observer", observer)
        app.removeDocumentObserver = lambda observer: setattr(app, "observer", None)
        selection = FakeSelection()
        gui = SimpleNamespace(
            Selection=selection,
            activeWorkbench=lambda: SimpleNamespace(name=lambda: "PartDesignWorkbench"),
        )
        return NextCADActivityObserver(app, gui), app, selection

    def test_records_manual_events_and_snapshot(self):
        observer, _app, _selection = self.make_observer()
        observer.start()
        observer.slotCreatedObject(SimpleNamespace(Name="Pad", TypeId="PartDesign::Pad"))
        observer.slotChangedObject(None, SimpleNamespace(Name="Pad", TypeId="PartDesign::Pad"), "Length")
        snapshot = observer.snapshot()
        self.assertTrue(snapshot["enabled"])
        self.assertEqual(snapshot["workbench"], "PartDesignWorkbench")
        self.assertEqual(snapshot["events"][-1]["property"], "Length")
        self.assertNotIn("Label", snapshot["events"][-1])
        observer.stop()
        self.assertFalse(observer.snapshot()["enabled"])

    def test_suspends_ai_generated_changes(self):
        observer, _app, _selection = self.make_observer()
        observer.start()
        observer.set_suspended(True)
        observer.slotCreatedObject(SimpleNamespace(Name="AIObject", TypeId="Part::Feature"))
        self.assertEqual(len(observer.snapshot()["events"]), 1)
        observer.set_suspended(False)
        observer.slotCreatedObject(SimpleNamespace(Name="ManualObject", TypeId="Part::Feature"))
        self.assertEqual(observer.snapshot()["events"][-1]["object"], "ManualObject")

    def test_never_records_property_values_or_object_labels(self):
        observer, _app, _selection = self.make_observer()
        observer.start()
        obj = SimpleNamespace(Name="Sketch", TypeId="Sketcher::SketchObject", Label="private job name")
        observer.slotChangedObject(None, obj, "Geometry")
        event = observer.snapshot()["events"][-1]
        self.assertNotIn("private job name", str(event))
        self.assertNotIn("value", event)


if __name__ == "__main__":
    unittest.main()
