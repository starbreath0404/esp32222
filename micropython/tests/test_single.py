"""PC-side checks for the standalone 14-feature glove implementation."""

import shutil
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "single_glove"))

import dtw
from storage import TemplateStore


def frame(flex=10.0, accel=0.0):
    return [flex] * 5 + [accel] * 9


def sequence(flex, accel, count=30):
    return [frame(flex + (index % 3), accel) for index in range(count)]


def main():
    first = sequence(10.0, 0.0)
    close = sequence(12.0, 0.02, 34)
    far = sequence(90.0, 1.5)
    assert dtw.distance(first, first) == 0.0
    assert dtw.distance(first, close) < dtw.distance(first, far)

    root = tempfile.mkdtemp(prefix="single_glove_test_")
    try:
        store = TemplateStore(root)
        store.add("hello", first)
        store.add("hello", close)
        gesture = store.add("hello", sequence(11.0, 0.01, 32))
        assert gesture["threshold"] is not None
        loaded = store.load_sequence(gesture["samples"][0])
        assert len(loaded) == len(first)
        result = store.recognize(sequence(11.0, 0.01, 31))
        assert result is not None
        assert result["gesture"]["label"] == "hello"
    finally:
        shutil.rmtree(root)

    print("PASS: single-glove DTW, storage and recognition checks")


if __name__ == "__main__":
    main()
