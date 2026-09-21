import struct
import time


class MPU9250:
    MPU_ADDR = 0x68
    MAG_ADDR = 0x0C

    def __init__(self, i2c, calibration=None):
        self.i2c = i2c
        self.calibration = calibration or {}
        self._write(self.MPU_ADDR, 0x6B, 0x00)
        time.sleep_ms(100)
        who = self._read(self.MPU_ADDR, 0x75, 1)[0]
        if who not in (0x71, 0x73):
            raise OSError("MPU9250 not found, WHO_AM_I=0x%02X" % who)
        self._write(self.MPU_ADDR, 0x1A, 0x03)
        self._write(self.MPU_ADDR, 0x1B, 0x00)  # gyro +/-250 dps
        self._write(self.MPU_ADDR, 0x1C, 0x00)  # accel +/-2 g
        self._write(self.MPU_ADDR, 0x37, 0x02)  # I2C bypass
        time.sleep_ms(10)
        mag_who = self._read(self.MAG_ADDR, 0x00, 1)[0]
        if mag_who != 0x48:
            raise OSError("AK8963 magnetometer not found")
        self._write(self.MAG_ADDR, 0x0A, 0x00)
        time.sleep_ms(10)
        self._write(self.MAG_ADDR, 0x0A, 0x16)  # 16-bit, continuous 100 Hz

    def _write(self, address, register, value):
        self.i2c.writeto_mem(address, register, bytes((value,)))

    def _read(self, address, register, count):
        return self.i2c.readfrom_mem(address, register, count)

    def read(self):
        raw = self._read(self.MPU_ADDR, 0x3B, 14)
        ax, ay, az, _, gx, gy, gz = struct.unpack(">hhhhhhh", raw)
        accel = [ax / 16384.0, ay / 16384.0, az / 16384.0]
        gyro = [gx / 131.0, gy / 131.0, gz / 131.0]

        mag = [0.0, 0.0, 0.0]
        if self._read(self.MAG_ADDR, 0x02, 1)[0] & 1:
            mag_raw = self._read(self.MAG_ADDR, 0x03, 7)
            if not (mag_raw[6] & 0x08):
                mx, my, mz = struct.unpack("<hhh", mag_raw[:6])
                mag = [mx * 0.15, my * 0.15, mz * 0.15]

        gyro_bias = self.calibration.get("gyro_bias", (0.0, 0.0, 0.0))
        mag_offset = self.calibration.get("mag_offset", (0.0, 0.0, 0.0))
        mag_scale = self.calibration.get("mag_scale", (1.0, 1.0, 1.0))
        gyro = [gyro[i] - gyro_bias[i] for i in range(3)]
        mag = [(mag[i] - mag_offset[i]) * mag_scale[i] for i in range(3)]
        return accel + gyro + mag

