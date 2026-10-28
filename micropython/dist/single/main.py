import gc
import json
import time

import config
from audio import AudioPlayer
from motion_detector import MotionDetector
from recorder import GestureRecorder
from sensor_reader import SensorReader
from serial_control import SerialControl
from storage import TemplateStore


def main():
    sensors = SensorReader()
    store = TemplateStore()
    recorder = GestureRecorder(config.SAMPLE_RATE_HZ, config.MAX_GESTURE_SECONDS * 1000)
    detector = MotionDetector(config.SAMPLE_RATE_HZ)
    audio = AudioPlayer()
    control = SerialControl(store)
    control.emit("ready", protocol=1, mode="single", features=14)

    interval = 1000 // config.SAMPLE_RATE_HZ
    next_sample = time.ticks_ms()
    last_spoken_id = None
    cooldown_until = 0
    sample_number = 0

    while True:
        command = control.poll()
        if command:
            name = command["command"]
            try:
                if name == "status":
                    control.emit(
                        "status",
                        mode="single",
                        features=14,
                        recording=recorder.state == recorder.RECORDING,
                        gestures=len(store.index["gestures"]),
                        detector_ready=detector.ready,
                    )
                elif name == "start_record":
                    recorder.max_ms = min(int(command.get("max_ms", 3000)), 10000)
                    recorder.start()
                    control.emit("recording", mode="single")
                elif name == "stop_record":
                    frames = recorder.stop()
                    control.emit("recorded", frames=len(frames), mode="single")
                elif name == "cancel":
                    recorder.cancel()
                    control.emit("cancelled")
                elif name == "save":
                    frames = recorder.take()
                    gesture = store.add(command["label"], frames)
                    control.emit(
                        "saved",
                        gesture_id=gesture["id"],
                        samples=len(gesture["samples"]),
                        ready=gesture["threshold"] is not None,
                        mode="single",
                    )
                elif name == "list":
                    control.emit("gesture_list", gestures=store.index["gestures"])
                elif name == "audio_begin":
                    control.audio_begin(command)
                elif name == "audio_chunk":
                    control.audio_chunk(command)
                elif name == "audio_end":
                    control.audio_end()
                else:
                    raise ValueError("unknown command")
            except Exception as error:
                control.emit("error", code="COMMAND_FAILED", detail=str(error))

        now = time.ticks_ms()
        if time.ticks_diff(now, next_sample) < 0:
            time.sleep_ms(1)
            continue
        next_sample = time.ticks_add(next_sample, interval)

        try:
            snapshot = sensors.read_snapshot()
            frame = snapshot["frame"]
        except Exception as error:
            control.emit("error", code="SENSOR_READ_FAILED", detail=str(error))
            time.sleep_ms(100)
            continue

        sample_number += 1
        if recorder.state == recorder.RECORDING:
            if recorder.add(frame):
                control.emit("record_frame", values=frame)
            continue

        if sample_number % 5 == 0:
            control.emit(
                "sensor",
                calibrated=snapshot["calibrated"],
                flex_raw=snapshot["flex_raw"],
                flex=snapshot["flex"],
                accel=snapshot["accel"],
                gyro=snapshot["gyro"],
                mag=snapshot["mag"],
            )
        if time.ticks_diff(now, cooldown_until) < 0:
            continue

        sequence = detector.update(frame)
        if sequence is None:
            continue
        gc.collect()
        result = store.recognize(sequence)
        if result is None:
            control.emit("unknown")
            last_spoken_id = None
            cooldown_until = time.ticks_add(time.ticks_ms(), 700)
            continue

        gesture = result["gesture"]
        control.emit(
            "recognized",
            gesture_id=gesture["id"],
            label=gesture["label"],
            score=result["score"],
            mode="single",
        )
        if gesture["id"] != last_spoken_id and gesture.get("audio"):
            try:
                audio.play(gesture["audio"])
            except Exception as error:
                control.emit("error", code="AUDIO_FAILED", detail=str(error))
        last_spoken_id = gesture["id"]
        cooldown_until = time.ticks_add(time.ticks_ms(), 1000)


try:
    main()
except Exception as error:
    print(json.dumps({"event": "fatal", "mode": "single", "detail": repr(error)}))
