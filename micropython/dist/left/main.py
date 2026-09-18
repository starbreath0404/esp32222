import json
import time

import espnow
import network

import config
import packet
from sensor_reader import SensorReader


def load_right_mac():
    try:
        with open("/config/device.json", "r") as file:
            value = json.load(file)["right_mac"]
    except (OSError, KeyError, ValueError):
        value = config.RIGHT_HAND_MAC
    if not value:
        raise RuntimeError("right-hand MAC is not configured")
    return bytes(int(part, 16) for part in value.split(":"))


def main():
    sensors = SensorReader()
    sta = network.WLAN(network.STA_IF)
    sta.active(True)
    radio = espnow.ESPNow()
    radio.active(True)
    peer = load_right_mac()
    radio.add_peer(peer)

    sequence = 0
    interval = 1000 // config.SAMPLE_RATE_HZ
    next_sample = time.ticks_ms()
    print("LEFT_READY", ":".join("%02X" % byte for byte in sta.config("mac")))

    while True:
        now = time.ticks_ms()
        if time.ticks_diff(now, next_sample) < 0:
            time.sleep_ms(1)
            continue
        next_sample = time.ticks_add(next_sample, interval)
        try:
            payload = packet.encode(sequence, now, sensors.read())
            radio.send(peer, payload, False)
            sequence = (sequence + 1) & 0xFFFFFFFF
        except Exception as error:
            print("LEFT_ERROR", repr(error))
            time.sleep_ms(100)


try:
    main()
except Exception as error:
    print("LEFT_FATAL", repr(error))

