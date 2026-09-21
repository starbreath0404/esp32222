import os


for path in ("/config", "/gestures_single"):
    try:
        os.mkdir(path)
    except OSError:
        pass
