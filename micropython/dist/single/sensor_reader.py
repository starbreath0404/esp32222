import json
from machine import I2C, Pin

import config
from flex import FlexReader
from mpu9250 import MPU9250


def _load_json(path, default=None):
    try:
        with open(path, "r") as file:
            return json.load(file)
    except OSError:
        return default


class SensorReader:
    def __init__(self):
        calibration = _load_json("/config/calibration.json", {})
        self.flex = FlexReader(
            config.MUX_SELECT_PINS,
            config.MUX_SIGNAL_PIN,
            config.FLEX_CHANNELS,
            calibration.get("flex"),
        )
        i2c = I2C(
            config.I2C_ID,
            sda=Pin(config.I2C_SDA_PIN),
            scl=Pin(config.I2C_SCL_PIN),
            freq=config.I2C_FREQUENCY,
        )
        self.imu = MPU9250(i2c, calibration.get("imu"))

    def read(self):
        values = self.flex.read() + self.imu.read()
        if len(values) != 14:
            raise RuntimeError("sensor frame is not 14-dimensional")
        return values

