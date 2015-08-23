
def int_to_bytes(val, num_bytes):  # int to byte

    byte_array = bytearray(num_bytes)

    for pos in range(num_bytes):
        byte_array[num_bytes - pos - 1] = (val & (0xff << pos * 8)) >> pos * 8

    return byte_array
