from functools import reduce
from time import time


status_map = {
    b'\x01': "IDLE",
    b'\x02': "ACTIVE",
    b'\x03': "RECHARGE",
}


def get_ms_time():
    return int(round(time() * 1000))


def byte_message_xor(message):
    if type(message) not in [bytes, bytearray]:
        return None
    return bytes([reduce((lambda x, y: x ^ y), message, 0)])


if __name__ == "__main__":
    b1 = bytes([0x07, 0xFF, 0x07, 0x33])
    b2 = bytearray([0x07, 0xFF, 0x07, 0x32])
    print(byte_message_xor(b1))
    print(byte_message_xor(b2))

