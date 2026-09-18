import math

import config


class MotionDetector:
    def __init__(self, sample_rate=50):
        self.sample_rate = sample_rate
        self.baseline_values = []
        self.previous = None
        self.baseline_mean = 0.0
        self.baseline_std = 0.0
        self.ready = False
        self.active = False
        self.pre_roll = []
        self.sequence = []
        self.quiet_frames = 0

    def _energy(self, frame):
        if self.previous is None:
            self.previous = frame
            return 0.0
        flex_change = sum(abs(frame[i] - self.previous[i]) for i in range(5))
        flex_change += sum(abs(frame[14 + i] - self.previous[14 + i]) for i in range(5))
        gyro = sum(abs(frame[i]) for i in (8, 9, 10, 22, 23, 24))
        self.previous = frame
        return flex_change / 10.0 + gyro / 150.0

    def update(self, frame):
        energy = self._energy(frame)
        if not self.ready:
            self.baseline_values.append(energy)
            if len(self.baseline_values) >= self.sample_rate * 2:
                self.baseline_mean = sum(self.baseline_values) / len(self.baseline_values)
                variance = sum(
                    (value - self.baseline_mean) ** 2 for value in self.baseline_values
                ) / len(self.baseline_values)
                self.baseline_std = max(math.sqrt(variance), 0.01)
                self.ready = True
                self.baseline_values = []
            return None

        start_threshold = self.baseline_mean + config.MOTION_START_SIGMA * self.baseline_std
        stop_threshold = self.baseline_mean + config.MOTION_STOP_SIGMA * self.baseline_std

        if not self.active:
            self.pre_roll.append(tuple(frame))
            if len(self.pre_roll) > config.MOTION_PRE_ROLL_FRAMES:
                self.pre_roll.pop(0)
            if energy > start_threshold:
                self.active = True
                self.sequence = list(self.pre_roll)
                self.quiet_frames = 0
            return None

        self.sequence.append(tuple(frame))
        if energy < stop_threshold:
            self.quiet_frames += 1
        else:
            self.quiet_frames = 0

        max_frames = self.sample_rate * config.MAX_GESTURE_SECONDS
        finished = self.quiet_frames >= config.MOTION_QUIET_FRAMES
        if len(self.sequence) >= max_frames:
            finished = True
        if not finished:
            return None

        result = self.sequence
        self.active = False
        self.sequence = []
        self.pre_roll = []
        self.quiet_frames = 0
        if len(result) < self.sample_rate // 2:
            return None
        return result

