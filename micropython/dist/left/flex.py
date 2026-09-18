import time
from machine import ADC, Pin


class FlexReader:
    def __init__(self, select_pins, signal_pin, channels, calibration=None):
        self.select = [Pin(pin, Pin.OUT, value=0) for pin in select_pins]
        self.adc = ADC(Pin(signal_pin))
        try:
            self.adc.atten(ADC.ATTN_11DB)
        except AttributeError:
            pass
        self.channels = tuple(channels)
        self.calibration = calibration

    def _select_channel(self, channel):
        for bit, pin in enumerate(self.select):
            pin.value((channel >> bit) & 1)
        time.sleep_us(8)

    def read_raw(self):
        values = []
        for channel in self.channels:
            self._select_channel(channel)
            total = 0
            for _ in range(4):
                total += self.adc.read_u16()
            values.append(total // 4)
        return values

    def read(self):
        raw = self.read_raw()
        if not self.calibration:
            return raw
        straight = self.calibration["straight"]
        bent = self.calibration["bent"]
        return [self._normalize(raw[i], straight[i], bent[i]) for i in range(5)]

    @staticmethod
    def _normalize(raw, straight, bent):
        span = bent - straight
        if abs(span) < 500:
            raise ValueError("Flex calibration range is too small")
        value = (raw - straight) * 100.0 / span
        return max(0.0, min(100.0, value))

