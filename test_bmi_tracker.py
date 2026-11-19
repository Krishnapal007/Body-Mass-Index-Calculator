"""
test_bmi_tracker.py
-------------------
Automated tests for BMI logic, SQLite persistence, CSV export and graphs.
Run from the project folder:   python -m unittest -v
The tests use a temporary database, so your real bmi_tracker.db is never touched.
"""

import csv
import os
import tempfile
import unittest

import bmi_calculator as bmi
from database import Database, export_records_to_csv


class TestBMILogic(unittest.TestCase):
    def test_calculation_accuracy(self):
        self.assertEqual(bmi.calculate_bmi(70, 1.75), 22.86)
        self.assertEqual(bmi.calculate_bmi(50, 1.80), 15.43)
        self.assertEqual(bmi.calculate_bmi(85, 1.70), 29.41)
        self.assertEqual(bmi.calculate_bmi(100, 1.60), 39.06)

    def test_categories_and_boundaries(self):
        cases = [(18.49, "Underweight"), (18.5, "Normal"), (24.9, "Normal"),
                 (25.0, "Overweight"), (29.9, "Overweight"), (30.0, "Obese"),
                 (45.0, "Obese")]
        for value, expected in cases:
            self.assertEqual(bmi.get_category(value), expected, value)

    def test_colours(self):
        self.assertEqual(bmi.get_color("Underweight"), "#2563EB")
        self.assertEqual(bmi.get_color("Normal"), "#16A34A")
        self.assertEqual(bmi.get_color("Overweight"), "#F97316")
        self.assertEqual(bmi.get_color("Obese"), "#DC2626")

    def test_invalid_inputs(self):
        bad = [("", "70", "1.75"), ("Ann", "", "1.75"), ("Ann", "70", ""),
               ("Ann", "abc", "1.75"), ("Ann", "70", "xyz"), ("Ann", "-5", "1.75"),
               ("Ann", "70", "-1.7"), ("Ann", "70", "0"), ("Ann", "0", "1.75"),
               ("Ann", "nan", "1.75"), ("Ann", "70", "175"), ("   ", "70", "1.75"),
               ("Ann<script>", "70", "1.75")]
        for args in bad:
            with self.assertRaises(bmi.ValidationError, msg=str(args)):
                bmi.validate_inputs(*args)

    def test_valid_inputs(self):
        self.assertEqual(bmi.validate_inputs("  John   Doe ", "70,5", "1.75"),
                         ("John Doe", 70.5, 1.75))


class TestDatabase(unittest.TestCase):
    def setUp(self):
        fd, self.path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        self.db = Database(self.path)

    def tearDown(self):
        os.remove(self.path)

    def add(self, user, weight, height, when):
        value = bmi.calculate_bmi(weight, height)
        return self.db.insert_record(user, weight, height, value,
                                     bmi.get_category(value), when)

    def test_crud(self):
        rid = self.add("Alice", 60, 1.65, "2026-01-01 10:00:00")
        record = self.db.get_record(rid)
        self.assertEqual(record["username"], "Alice")
        self.assertEqual(record["bmi"], 22.04)
        self.assertTrue(self.db.update_record(rid, 90, 1.65, 33.06, "Obese"))
        self.assertEqual(self.db.get_record(rid)["category"], "Obese")
        self.assertTrue(self.db.delete_record(rid))
        self.assertIsNone(self.db.get_record(rid))

    def test_multiple_users_search_and_counters(self):
        self.add("Alice", 60, 1.65, "2026-01-01 10:00:00")
        self.add("alice", 62, 1.65, "2026-02-01 10:00:00")   # same user, other case
        self.add("Bob", 95, 1.70, "2026-01-05 09:00:00")
        self.assertEqual(self.db.count_records(), 3)
        self.assertEqual(self.db.count_users(), 2)
        self.assertEqual(self.db.get_usernames(), ["Alice", "Bob"])
        self.assertEqual(len(self.db.get_records_by_user("ALICE")), 2)
        self.assertEqual(len(self.db.search_records("ali")), 2)
        self.assertEqual(len(self.db.search_records("", "Obese")), 1)
        self.assertEqual(len(self.db.search_records("Bob", exact=True)), 1)
        self.assertEqual(len(self.db.search_records("%")), 0)  # wildcard is escaped
        summary = {s["username"]: s for s in self.db.get_user_summaries()}
        self.assertEqual(summary["Alice"]["total_records"], 2)
        self.assertEqual(summary["Alice"]["latest_bmi"], 22.77)
        self.assertEqual(self.db.get_category_counts()["Obese"], 1)

    def test_persistence_after_reopen(self):
        self.add("Carol", 70, 1.75, "2026-03-01 08:00:00")
        reopened = Database(self.path)
        self.assertEqual(reopened.count_records(), 1)
        self.assertEqual(reopened.get_all_records()[0]["username"], "Carol")

    def test_delete_multiple_and_user(self):
        ids = [self.add("Dan", 70, 1.75, f"2026-04-0{i} 08:00:00") for i in range(1, 4)]
        self.assertEqual(self.db.delete_records(ids[:2]), 2)
        self.assertEqual(self.db.count_records(), 1)
        self.assertEqual(self.db.delete_user("dan"), 1)
        self.assertEqual(self.db.count_records(), 0)

    def test_csv_export(self):
        self.add("Eve", 55, 1.60, "2026-05-01 08:00:00")
        fd, csv_path = tempfile.mkstemp(suffix=".csv")
        os.close(fd)
        try:
            count = export_records_to_csv(self.db.get_all_records(), csv_path)
            self.assertEqual(count, 1)
            with open(csv_path, newline="", encoding="utf-8-sig") as handle:
                rows = list(csv.reader(handle))
            self.assertEqual(rows[0][1], "Username")
            self.assertEqual(rows[1][1], "Eve")
            self.assertEqual(rows[1][4], "21.48")
        finally:
            os.remove(csv_path)

    def test_connection_error(self):
        from database import DatabaseError
        with self.assertRaises(DatabaseError):
            Database(os.path.join(tempfile.gettempdir(), "no_such_dir_xyz", "x.db"))


class TestVisualization(unittest.TestCase):
    def test_figures(self):
        import visualization as viz
        records = [
            {"bmi": 22.0, "recorded_at": "2026-01-01 10:00:00"},
            {"bmi": 23.1, "recorded_at": "2026-02-01 10:00:00"},
            {"bmi": 26.5, "recorded_at": "2026-03-01 10:00:00"},
        ]
        fig = viz.create_trend_figure({"Alice": records, "Bob": records[:1]})
        ax = fig.axes[0]
        self.assertEqual(ax.get_xlabel(), "Date")
        self.assertEqual(ax.get_ylabel(), "BMI")
        self.assertIsNotNone(ax.get_legend())
        self.assertIsNotNone(viz.create_category_figure({"Normal": 2}))
        with self.assertRaises(viz.GraphError):
            viz.create_trend_figure({})


if __name__ == "__main__":
    unittest.main(verbosity=2)
