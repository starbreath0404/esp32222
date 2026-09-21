import gc
import time


class GestureRecorder:
    IDLE, RECORDING, RECORDED = range(3)

    def __init__(self, sample_rate=50, max_ms=3000):
        self.sample_rate = sample_rate
        self.max_ms = max_ms
        self.state = self.IDLE
        self.frames = []

    def start(self):
        if self.state == self.RECORDING:
            raise RuntimeError("already recording")
        gc.collect()
        self.frames = []
        self.started_at = time.ticks_ms()
        self.state = self.RECORDING

    def add(self, frame):
        if self.state != self.RECORDING:
            return False
        if time.ticks_diff(time.ticks_ms(), self.started_at) >= self.max_ms:
            self.stop()
            return False
        if len(frame) != 14:
            raise ValueError("single-hand frame must contain 14 features")
        self.frames.append(tuple(frame))
        return True

    def stop(self):
        if self.state != self.RECORDING:
            raise RuntimeError("not recording")
        if len(self.frames) < self.sample_rate // 2:
            self.cancel()
            raise ValueError("recording is too short")
        self.state = self.RECORDED
        return self.frames

    def cancel(self):
        self.frames = []
        self.state = self.IDLE
        gc.collect()

    def take(self):
        if self.state != self.RECORDED:
            raise RuntimeError("no completed recording")
        frames = self.frames
        self.frames = []
        self.state = self.IDLE
        return frames
