import binascii
import json
import os
import select
import sys

from crc import crc32_finish, crc32_update


class SerialControl:
    def __init__(self, store):
        self.store = store
        self.poller = select.poll()
        self.poller.register(sys.stdin, select.POLLIN)
        self.upload = None

    def emit(self, event, **values):
        payload = {"event": event}
        payload.update(values)
        print(json.dumps(payload))

    def poll(self):
        if not self.poller.poll(0):
            return None
        line = sys.stdin.readline()
        if not line:
            return None
        try:
            command = json.loads(line)
            if not isinstance(command, dict) or "command" not in command:
                raise ValueError("invalid command")
            return command
        except Exception as error:
            self.emit("error", code="BAD_COMMAND", detail=str(error))
            return None

    def audio_begin(self, command):
        gesture_id = int(command["gesture_id"])
        size = int(command["size"])
        checksum = int(command["crc32"])
        gesture = self.store.find_id(gesture_id)
        if gesture is None:
            raise ValueError("gesture id not found")
        folder = "%s/%04d" % (self.store.root, gesture_id)
        temporary = folder + "/audio.wav.tmp"
        self.upload = {
            "id": gesture_id,
            "path": folder + "/audio.wav",
            "temporary": temporary,
            "size": size,
            "written": 0,
            "expected_crc": checksum,
            "crc_state": 0xFFFFFFFF,
            "file": open(temporary, "wb"),
        }
        self.emit("audio_ready", gesture_id=gesture_id)

    def audio_chunk(self, command):
        if self.upload is None:
            raise RuntimeError("no audio upload active")
        data = binascii.a2b_base64(command["data"])
        self.upload["file"].write(data)
        self.upload["written"] += len(data)
        self.upload["crc_state"] = crc32_update(self.upload["crc_state"], data)

    def audio_end(self):
        if self.upload is None:
            raise RuntimeError("no audio upload active")
        upload = self.upload
        self.upload = None
        upload["file"].close()
        actual_crc = crc32_finish(upload["crc_state"])
        if upload["written"] != upload["size"] or actual_crc != upload["expected_crc"]:
            try:
                os.remove(upload["temporary"])
            except OSError:
                pass
            raise ValueError("audio size or CRC mismatch")
        try:
            os.remove(upload["path"])
        except OSError:
            pass
        os.rename(upload["temporary"], upload["path"])
        self.store.set_audio(upload["id"], upload["path"])
        self.emit("audio_saved", gesture_id=upload["id"])
