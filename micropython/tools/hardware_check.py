import gc
import os
import sys

print("Python:", sys.implementation)
print("Board:", os.uname())
print("Free heap:", gc.mem_free())

try:
    import espnow
    print("PASS: espnow", getattr(espnow, "MAX_DATA_LEN", 250))
except Exception as error:
    print("FAIL: espnow", repr(error))

try:
    from machine import I2S
    print("PASS: I2S", I2S)
except Exception as error:
    print("FAIL: I2S", repr(error))

try:
    with open("/write_test.txt", "w") as file:
        file.write("ok")
    os.remove("/write_test.txt")
    print("PASS: filesystem")
except Exception as error:
    print("FAIL: filesystem", repr(error))

