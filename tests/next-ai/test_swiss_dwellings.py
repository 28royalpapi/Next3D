import csv
import importlib.util
import json
import tempfile
import unittest
import zipfile
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[2] / "training/nextai/prepare_swiss_dwellings.py"
spec = importlib.util.spec_from_file_location("prepare_swiss_dwellings", SCRIPT)
swiss = importlib.util.module_from_spec(spec)
spec.loader.exec_module(swiss)


@unittest.skipUnless(
    __import__("importlib").util.find_spec("PIL") is not None
    and __import__("importlib").util.find_spec("shapely") is not None,
    "Pillow and Shapely are installed by the NextAI training-data CI step",
)
class SwissDwellingsPipelineTests(unittest.TestCase):
    def _building_for_split(self, split, start=0):
        for index in range(start, start + 2000):
            building = f"building-{index}"
            if swiss.building_split("site-test", building) == split:
                return building
        self.fail(f"could not find a stable {split} building id")

    def _make_zip(self, path):
        fields = [
            "site_id", "building_id", "floor_id", "plan_id",
            "apartment_id", "unit_id", "area_id", "unit_usage",
            "entity_type", "entity_subtype", "geometry", "elevation", "height",
        ]
        rows = []
        for split in ("train", "validation", "test"):
            building = self._building_for_split(split)
            shared = {
                "site_id": "site-test",
                "building_id": building,
                "floor_id": "floor-1",
                "plan_id": "plan-1",
                "unit_usage": "RESIDENTIAL",
                "elevation": "0",
                "height": "2.7",
            }
            rows.extend([
                {
                    **shared, "apartment_id": "apt-1", "unit_id": "unit-1",
                    "area_id": "area-1", "entity_type": "area",
                    "entity_subtype": "LIVING_ROOM",
                    "geometry": "POLYGON ((0 0, 6 0, 6 4, 0 4, 0 0))",
                },
                {
                    **shared, "apartment_id": "apt-1", "unit_id": "unit-1",
                    "area_id": "area-2", "entity_type": "area",
                    "entity_subtype": "KITCHEN",
                    "geometry": "POLYGON ((6 0, 10 0, 10 4, 6 4, 6 0))",
                },
                {
                    **shared, "apartment_id": "", "unit_id": "", "area_id": "",
                    "entity_type": "separator", "entity_subtype": "WALL",
                    "geometry": "LINESTRING (0 0, 10 0)",
                },
                {
                    **shared, "apartment_id": "apt-1", "unit_id": "unit-1",
                    "area_id": "area-1", "entity_type": "opening",
                    "entity_subtype": "DOOR",
                    "geometry": "LINESTRING (6 1, 6 2)",
                },
                {
                    **shared, "apartment_id": "apt-1", "unit_id": "unit-1",
                    "area_id": "area-2", "entity_type": "feature",
                    "entity_subtype": "SINK",
                    "geometry": "POINT (8 2)",
                },
            ])
        with zipfile.ZipFile(path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            with archive.open("folder/geometries.csv", "w") as raw:
                import io
                text = io.TextIOWrapper(raw, encoding="utf-8", newline="")
                writer = csv.DictWriter(text, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
                text.flush()

    def test_zip_pipeline_renders_images_and_keeps_metric_room_geometry(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            archive = root / "swiss.zip"
            out = root / "prepared"
            self._make_zip(archive)
            manifest = swiss.prepare(
                archive, out,
                max_train=1, max_validation=1, max_test=1,
                image_size=256, seed=42,
            )
            self.assertEqual(manifest["records"], {"train": 1, "validation": 1, "test": 1})
            self.assertTrue(manifest["split_by_building_to_prevent_floor_leakage"])
            self.assertTrue(manifest["training_source_only_not_runtime_dependency"])

            for split in ("train", "validation", "test"):
                lines = (out / f"{split}.jsonl").read_text(encoding="utf-8").splitlines()
                self.assertEqual(len(lines), 1)
                record = json.loads(lines[0])
                self.assertEqual(record["license"], "CC-BY-4.0")
                self.assertEqual(record["source_doi"], "10.5281/zenodo.7788422")
                image = Path(record["images"][0])
                self.assertTrue(image.is_file())
                self.assertEqual(record["domain"], "swiss_dwellings_floorplan")

            train = json.loads((out / "train.jsonl").read_text(encoding="utf-8").splitlines()[0])
            target = json.loads(train["completion"])
            self.assertEqual(target["units"], "metres")
            self.assertEqual(target["coordinate_frame"]["x_axis"], "east")
            self.assertEqual(len(target["rooms"]), 2)
            self.assertEqual(target["rooms"][0]["calculated_area_m2"], 24.0)
            self.assertEqual(target["rooms"][1]["calculated_area_m2"], 16.0)
            self.assertEqual(len(target["room_shared_boundary_graph"]), 1)
            self.assertEqual(target["room_shared_boundary_graph"][0]["shared_boundary_m"], 4.0)
            self.assertEqual(target["element_counts_by_category"]["opening:DOOR"], 1)

    def test_building_split_is_stable_for_all_floors(self):
        building = self._building_for_split("train")
        first = swiss.building_split("same-site", building)
        second = swiss.building_split("same-site", building)
        self.assertEqual(first, second)
        self.assertEqual(first, "train")

    def test_floor_key_requires_site_building_and_floor(self):
        self.assertIsNone(swiss.floor_key({"site_id": "s", "building_id": "b", "floor_id": ""}))
        self.assertEqual(
            swiss.floor_key({"site_id": "s", "building_id": "b", "floor_id": "f", "plan_id": "p"}),
            ("s", "b", "f", "p"),
        )


if __name__ == "__main__":
    unittest.main()
