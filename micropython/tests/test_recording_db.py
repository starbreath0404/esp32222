"""PC-side checks for recording backup and CSV export."""

import csv
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "desktop"))

from recording_db import RecordingDatabase


def main():
    with tempfile.TemporaryDirectory(prefix="glove_db_test_") as folder:
        database_path = Path(folder) / "recordings.sqlite3"
        csv_path = Path(folder) / "recordings.csv"
        database = RecordingDatabase(database_path)
        frames = [[float(sample + feature) for feature in range(14)] for sample in range(5)]
        row_id = database.add("你好", 7, "single", frames, 50)
        rows = database.list_recordings()
        assert len(rows) == 1
        assert rows[0]["id"] == row_id
        assert rows[0]["label"] == "你好"
        assert rows[0]["frame_count"] == 5

        exported = database.export_csv(csv_path, [row_id])
        assert exported == 5
        with open(csv_path, "r", encoding="utf-8-sig", newline="") as file:
            csv_rows = list(csv.reader(file))
        assert len(csv_rows) == 6
        assert csv_rows[0][-14:] == [
            "flex_thumb",
            "flex_index",
            "flex_middle",
            "flex_ring",
            "flex_little",
            "accel_x",
            "accel_y",
            "accel_z",
            "gyro_x",
            "gyro_y",
            "gyro_z",
            "mag_x",
            "mag_y",
            "mag_z",
        ]
        assert csv_rows[1][2] == "你好"

    print("PASS: desktop SQLite backup and CSV export checks")


if __name__ == "__main__":
    main()
