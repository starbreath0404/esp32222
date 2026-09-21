import binascii
import json
import os
import struct


MAGIC = b"GSS1"
FEATURE_COUNT = 14
HEADER_FORMAT = "<4sHH"
FRAME_FORMAT = "<14f"
FRAME_BYTES = 56


def _mkdir(path):
    try:
        os.mkdir(path)
    except OSError:
        pass


class TemplateStore:
    def __init__(self, root="/gestures_single"):
        self.root = root
        self.index_path = root + "/index.json"
        _mkdir(root)
        self.index = self._load_index()

    def _load_index(self):
        try:
            with open(self.index_path, "r") as file:
                data = json.load(file)
            if data.get("version") != 1 or data.get("features") != FEATURE_COUNT:
                raise ValueError("unsupported single-hand gesture index")
            return data
        except OSError:
            return {"version": 1, "features": FEATURE_COUNT, "gestures": []}

    def _save_index(self):
        temporary = self.index_path + ".tmp"
        with open(temporary, "w") as file:
            json.dump(self.index, file)
        try:
            os.remove(self.index_path)
        except OSError:
            pass
        os.rename(temporary, self.index_path)

    def _find_label(self, label):
        for gesture in self.index["gestures"]:
            if gesture["label"] == label:
                return gesture
        return None

    def find_id(self, gesture_id):
        for gesture in self.index["gestures"]:
            if gesture["id"] == gesture_id:
                return gesture
        return None

    def set_audio(self, gesture_id, path):
        gesture = self.find_id(gesture_id)
        if gesture is None:
            raise ValueError("gesture id not found")
        gesture["audio"] = path
        self._save_index()

    def add(self, label, frames):
        label = label.strip()
        if not label:
            raise ValueError("label is empty")
        gesture = self._find_label(label)
        if gesture is None:
            next_id = max([item["id"] for item in self.index["gestures"]] or [0]) + 1
            gesture = {
                "id": next_id,
                "label": label,
                "samples": [],
                "threshold": None,
                "audio": None,
            }
            self.index["gestures"].append(gesture)
        folder = "%s/%04d" % (self.root, gesture["id"])
        _mkdir(folder)
        path = folder + "/sample_%02d.bin" % (len(gesture["samples"]) + 1)
        self._write_sequence(path, frames)
        gesture["samples"].append(path)
        self._refresh_threshold(gesture)
        self._save_index()
        return gesture

    def _write_sequence(self, path, frames):
        if not frames or any(len(frame) != FEATURE_COUNT for frame in frames):
            raise ValueError("invalid single-hand gesture sequence")
        body = bytearray()
        for frame in frames:
            body.extend(struct.pack(FRAME_FORMAT, *frame))
        header = struct.pack(HEADER_FORMAT, MAGIC, len(frames), FEATURE_COUNT)
        checksum = binascii.crc32(header + body) & 0xFFFFFFFF
        with open(path + ".tmp", "wb") as file:
            file.write(header)
            file.write(body)
            file.write(struct.pack("<I", checksum))
        try:
            os.remove(path)
        except OSError:
            pass
        os.rename(path + ".tmp", path)

    def load_sequence(self, path):
        with open(path, "rb") as file:
            raw = file.read()
        header_size = struct.calcsize(HEADER_FORMAT)
        if len(raw) < header_size + 4:
            raise ValueError("gesture file is truncated")
        magic, frame_count, feature_count = struct.unpack(HEADER_FORMAT, raw[:header_size])
        if magic != MAGIC or feature_count != FEATURE_COUNT:
            raise ValueError("invalid single-hand gesture file")
        expected = header_size + frame_count * FRAME_BYTES + 4
        if len(raw) != expected:
            raise ValueError("gesture file length mismatch")
        expected_crc = struct.unpack("<I", raw[-4:])[0]
        if (binascii.crc32(raw[:-4]) & 0xFFFFFFFF) != expected_crc:
            raise ValueError("gesture file CRC mismatch")
        frames = []
        offset = header_size
        for _ in range(frame_count):
            frames.append(list(struct.unpack(FRAME_FORMAT, raw[offset:offset + FRAME_BYTES])))
            offset += FRAME_BYTES
        return frames

    def _refresh_threshold(self, gesture):
        if len(gesture["samples"]) < 3:
            gesture["threshold"] = None
            return
        import dtw
        samples = [self.load_sequence(path) for path in gesture["samples"]]
        gesture["threshold"] = dtw.estimate_threshold(samples)

    def recognize(self, frames):
        import dtw
        best = None
        for gesture in self.index["gestures"]:
            threshold = gesture.get("threshold")
            if threshold is None:
                continue
            for path in gesture["samples"]:
                score = dtw.distance(frames, self.load_sequence(path))
                if best is None or score < best["score"]:
                    best = {"gesture": gesture, "score": score}
        if best is None or best["score"] > best["gesture"]["threshold"]:
            return None
        return best
