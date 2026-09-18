import struct
from machine import I2S, Pin

import config


class AudioPlayer:
    def __init__(self):
        self.i2s = I2S(
            config.I2S_ID,
            sck=Pin(config.I2S_BCLK_PIN),
            ws=Pin(config.I2S_LRC_PIN),
            sd=Pin(config.I2S_DIN_PIN),
            mode=I2S.TX,
            bits=16,
            format=I2S.MONO,
            rate=config.I2S_RATE,
            ibuf=config.I2S_BUFFER_BYTES,
        )

    def play(self, path):
        if not path:
            return
        with open(path, "rb") as file:
            riff = file.read(12)
            if len(riff) != 12 or riff[:4] != b"RIFF" or riff[8:] != b"WAVE":
                raise ValueError("audio is not a WAV file")
            data_size = None
            while True:
                header = file.read(8)
                if len(header) != 8:
                    break
                chunk_id, chunk_size = struct.unpack("<4sI", header)
                if chunk_id == b"fmt ":
                    fmt = file.read(chunk_size)
                    audio_format, channels, rate, _, _, bits = struct.unpack(
                        "<HHIIHH", fmt[:16]
                    )
                    if (audio_format, channels, rate, bits) != (1, 1, 16000, 16):
                        raise ValueError("WAV must be PCM mono 16-bit 16000 Hz")
                elif chunk_id == b"data":
                    data_size = chunk_size
                    break
                else:
                    file.seek(chunk_size + (chunk_size & 1), 1)
            if data_size is None:
                raise ValueError("WAV data chunk not found")
            remaining = data_size
            while remaining:
                chunk = file.read(min(1024, remaining))
                if not chunk:
                    break
                self.i2s.write(chunk)
                remaining -= len(chunk)
