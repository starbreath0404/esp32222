import struct

from crc import crc16


PROTOCOL_VERSION = 1
FEATURE_COUNT = 14
_BODY_FORMAT = "<BII14f"
_PACKET_FORMAT = "<BII14fH"
PACKET_SIZE = struct.calcsize(_PACKET_FORMAT)


def encode(sequence, timestamp_ms, features):
    if len(features) != FEATURE_COUNT:
        raise ValueError("single-hand frame must contain 14 features")
    body = struct.pack(
        _BODY_FORMAT,
        PROTOCOL_VERSION,
        sequence,
        timestamp_ms,
        *features,
    )
    return body + struct.pack("<H", crc16(body))


def decode(payload):
    if len(payload) != PACKET_SIZE:
        raise ValueError("invalid packet size")
    body = payload[:-2]
    received_crc = struct.unpack("<H", payload[-2:])[0]
    if crc16(body) != received_crc:
        raise ValueError("packet CRC mismatch")
    values = struct.unpack(_PACKET_FORMAT, payload)
    if values[0] != PROTOCOL_VERSION:
        raise ValueError("unsupported protocol version")
    return values[1], values[2], list(values[3:17])

