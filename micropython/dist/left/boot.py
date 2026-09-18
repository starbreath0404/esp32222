import os


for path in ("/config",):
    try:
        os.mkdir(path)
    except OSError:
        pass

