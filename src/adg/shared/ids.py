from secrets import randbits
from time import time_ns
from uuid import UUID


def uuidv7() -> str:
    unix_ts_ms = time_ns() // 1_000_000
    rand_a = randbits(12)
    rand_b = randbits(62)
    value = (
        (unix_ts_ms << 80)
        | (0x7 << 76)
        | (rand_a << 64)
        | (0b10 << 62)
        | rand_b
    )
    return str(UUID(int=value))
