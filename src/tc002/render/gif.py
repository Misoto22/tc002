"""Minimal animated-GIF encoder (stdlib only).

The clock plays a pushed GIF in a loop by itself, so an animation costs one HTTP
request instead of a request per frame.
"""

import base64
import struct

# Progressively coarser channel masks; the last (3-3-2 bits) can never exceed 256 colors.
_MASKS = (0xFFFFFF, 0xF8F8F8, 0xF0F0F0, 0xE0E0C0)


def _quantize(frames):
    """Drop low color bits until the animation fits GIF's 256-color palette."""
    for mask in _MASKS:
        masked = [[p & mask for p in f] for f in frames]
        if len({p for f in masked for p in f}) <= 256:
            return masked
    raise AssertionError("unreachable: 3-3-2 masking yields at most 256 colors")


def _palette(frames):
    """Global palette of every color used."""
    colors = sorted({p for f in frames for p in f})
    size_bits = max(1, (len(colors) - 1).bit_length())
    return colors + [0] * ((1 << size_bits) - len(colors)), size_bits


def _lzw(indices, min_code_size):
    """GIF-flavoured LZW: variable-width codes, packed LSB first."""
    clear, end = 1 << min_code_size, (1 << min_code_size) + 1
    out, bits, nbits = bytearray(), 0, 0
    width = min_code_size + 1

    def emit(code):
        nonlocal bits, nbits
        bits |= code << nbits
        nbits += width
        while nbits >= 8:
            out.append(bits & 0xFF)
            bits >>= 8
            nbits -= 8

    # Entries are keyed by (code of the prefix string, next index): O(1) per pixel.
    table = {}
    next_code = end + 1
    emit(clear)
    run = indices[0]
    for idx in indices[1:]:
        code = table.get((run, idx))
        if code is not None:
            run = code
            continue
        emit(run)
        if next_code < 4096:
            table[(run, idx)] = next_code
            next_code += 1
            if next_code > (1 << width) and width < 12:
                width += 1
        else:  # table full: reset so the decoder stays in step
            emit(clear)
            table = {}
            next_code, width = end + 1, min_code_size + 1
        run = idx
    emit(run)
    emit(end)
    if nbits:
        out.append(bits & 0xFF)
    return bytes(out)


def encode(frames, width, height, delay_ms):
    """frames: lists of 0xRRGGBB ints (row-major). delay_ms: one value or one per frame."""
    delays = delay_ms if isinstance(delay_ms, list) else [delay_ms] * len(frames)
    frames = _quantize(frames)
    palette, size_bits = _palette(frames)
    index = {c: i for i, c in enumerate(palette)}
    min_code = max(2, size_bits)

    out = bytearray(b"GIF89a")
    out += struct.pack("<HHBBB", width, height, 0x80 | (size_bits - 1), 0, 0)
    out += b"".join(struct.pack(">I", c)[1:] for c in palette)
    out += b"\x21\xff\x0bNETSCAPE2.0\x03\x01\x00\x00\x00"  # loop forever
    for frame, delay in zip(frames, delays, strict=True):
        out += b"\x21\xf9\x04\x00" + struct.pack("<H", max(2, round(delay / 10))) + b"\x00\x00"
        out += b"\x2c" + struct.pack("<HHHHB", 0, 0, width, height, 0)
        data = _lzw([index[p] for p in frame], min_code)
        out.append(min_code)
        for i in range(0, len(data), 255):
            chunk = data[i : i + 255]
            out += bytes([len(chunk)]) + chunk
        out.append(0)
    out.append(0x3B)
    return bytes(out)


def data_uri(gif_bytes):
    return "data:image/gif;base64," + base64.b64encode(gif_bytes).decode()
