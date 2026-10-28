import csv
from contextlib import closing
from datetime import datetime
import json
import os
from pathlib import Path
import sqlite3


HEADERS = [
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


def default_database_path():
    local = os.environ.get("LOCALAPPDATA")
    base = Path(local) if local else Path.home() / "AppData" / "Local"
    folder = base / "GloveRecorder"
    folder.mkdir(parents=True, exist_ok=True)
    return folder / "recordings.sqlite3"


class RecordingDatabase:
    def __init__(self, path=None):
        self.path = Path(path) if path else default_database_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._create_schema()

    def _connect(self):
        return sqlite3.connect(str(self.path))

    def _create_schema(self):
        with closing(self._connect()) as connection:
            with connection:
                connection.execute(
                    """
                    CREATE TABLE IF NOT EXISTS recordings (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        created_at TEXT NOT NULL,
                        label TEXT NOT NULL,
                        gesture_id INTEGER,
                        mode TEXT NOT NULL,
                        sample_rate_hz INTEGER NOT NULL,
                        frame_count INTEGER NOT NULL,
                        frames_json TEXT NOT NULL
                    )
                    """
                )

    def add(self, label, gesture_id, mode, frames, sample_rate_hz=50):
        clean_frames = [[float(value) for value in frame] for frame in frames]
        if not clean_frames or any(len(frame) != 14 for frame in clean_frames):
            raise ValueError("recording must contain 14-value frames")
        created_at = datetime.now().astimezone().isoformat(timespec="seconds")
        with closing(self._connect()) as connection:
            with connection:
                cursor = connection.execute(
                    """
                    INSERT INTO recordings
                        (created_at, label, gesture_id, mode, sample_rate_hz,
                         frame_count, frames_json)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        created_at,
                        label,
                        gesture_id,
                        mode,
                        sample_rate_hz,
                        len(clean_frames),
                        json.dumps(clean_frames, separators=(",", ":")),
                    ),
                )
                return cursor.lastrowid

    def list_recordings(self):
        with closing(self._connect()) as connection:
            rows = connection.execute(
                """
                SELECT id, created_at, label, gesture_id, mode, frame_count
                FROM recordings ORDER BY id DESC
                """
            ).fetchall()
        return [
            {
                "id": row[0],
                "created_at": row[1],
                "label": row[2],
                "gesture_id": row[3],
                "mode": row[4],
                "frame_count": row[5],
            }
            for row in rows
        ]

    def _load_rows(self, recording_ids=None):
        query = "SELECT id, created_at, label, gesture_id, mode, sample_rate_hz, frames_json FROM recordings"
        values = []
        if recording_ids:
            placeholders = ",".join("?" for _ in recording_ids)
            query += " WHERE id IN (%s)" % placeholders
            values = [int(value) for value in recording_ids]
        query += " ORDER BY id"
        with closing(self._connect()) as connection:
            return connection.execute(query, values).fetchall()

    def export_csv(self, destination, recording_ids=None):
        rows = self._load_rows(recording_ids)
        with open(destination, "w", newline="", encoding="utf-8-sig") as file:
            writer = csv.writer(file)
            writer.writerow(
                [
                    "recording_id",
                    "created_at",
                    "label",
                    "gesture_id",
                    "mode",
                    "sample_rate_hz",
                    "sample_index",
                    "time_seconds",
                ]
                + HEADERS
            )
            exported = 0
            for row in rows:
                recording_id, created_at, label, gesture_id, mode, rate, payload = row
                for index, frame in enumerate(json.loads(payload)):
                    writer.writerow(
                        [
                            recording_id,
                            created_at,
                            label,
                            gesture_id,
                            mode,
                            rate,
                            index,
                            "%.4f" % (index / rate),
                        ]
                        + frame
                    )
                    exported += 1
        return exported
