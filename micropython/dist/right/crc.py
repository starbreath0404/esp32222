def crc16(data):
    value = 0xFFFF
    for byte in data:
        value ^= byte << 8
        for _ in range(8):
            if value & 0x8000:
                value = ((value << 1) ^ 0x1021) & 0xFFFF
            else:
                value = (value << 1) & 0xFFFF
    return value


def crc32_update(state, data):
    for byte in data:
        state ^= byte
        for _ in range(8):
            if state & 1:
                state = (state >> 1) ^ 0xEDB88320
            else:
                state >>= 1
    return state & 0xFFFFFFFF


def crc32_finish(state):
    return state ^ 0xFFFFFFFF
