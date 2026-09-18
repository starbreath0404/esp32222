import os


for path in ("/config", "/gestures"):
    try:
        os.mkdir(path)
    except OSError:
        pass

