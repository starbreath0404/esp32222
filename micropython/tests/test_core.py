"""PC-side checks for code shared with the two MicroPython boards."""

import binascii
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "common"))
sys.path.insert(0, str(ROOT / "right_glove"))

import crc
import dtw
import packet


def frame(flex=10.0, accel=0.0):
    one_hand = [flex] * 5 + [accel] * 9
    return one_hand + one_hand


def main():
    features = [float(index) for index in range(14)]
    payload = packet.encode(7, 123456, features)
    sequence, timestamp, decoded = packet.decode(payload)
    assert sequence == 7
    assert timestamp == 123456
    assert decoded == features

    damaged = bytearray(payload)
    damaged[10] ^= 0x01
    try:
        packet.decode(damaged)
        raise AssertionError("damaged packet was accepted")
    except ValueError as error:
        assert "CRC" in str(error)

    data = b"gesture glove CRC test"
    state = crc.crc32_update(0xFFFFFFFF, data)
    assert crc.crc32_finish(state) == (binascii.crc32(data) & 0xFFFFFFFF)

    first = [frame(10.0, 0.0) for _ in range(20)]
    close = [frame(12.0, 0.02) for _ in range(24)]
    far = [frame(90.0, 1.5) for _ in range(20)]
    assert dtw.distance(first, first) == 0.0
    assert dtw.distance(first, close) < dtw.distance(first, far)
    assert dtw.estimate_threshold([first, close, first]) is not None

    print("PASS: packet CRC, CRC32 and DTW checks")


if __name__ == "__main__":
    main()
