import espnow
import network
import time

import packet


class LeftHandReceiver:
    def __init__(self):
        self.sta = network.WLAN(network.STA_IF)
        self.sta.active(True)
        self.radio = espnow.ESPNow()
        self.radio.active(True)
        self.last_sequence = None
        self.last_frame = None
        self.last_received_ms = None
        self.dropped = 0

    def poll(self):
        host, payload = self.radio.recv(0)
        if not payload:
            return None
        try:
            sequence, remote_time, features = packet.decode(payload)
        except ValueError:
            return None
        if self.last_sequence is not None:
            gap = (sequence - self.last_sequence) & 0xFFFFFFFF
            if 1 < gap < 0x80000000:
                self.dropped += gap - 1
        self.last_sequence = sequence
        self.last_frame = features
        self.last_received_ms = time.ticks_ms()
        return features

    def current(self, max_age_ms=100):
        if self.last_frame is None:
            return None
        if time.ticks_diff(time.ticks_ms(), self.last_received_ms) > max_age_ms:
            return None
        return self.last_frame

