"""Development TFM loading with TeX's first matching lig/kern instruction.

fontTools currently overwrites earlier kerns when a shared program tail repeats
a next-character code. TeX stops at the first match (including a ligature).
Outlines and all other fontTools metrics remain unchanged.
"""
import struct
from pathlib import Path
from fontTools.tfmLib import TFM


def tex_kerning(raw):
    lf, lh, bc, ec, nw, nh, nd, ni, nl, nk, ne, np = struct.unpack('>12H', raw[:24])
    count = max(0, ec - bc + 1)
    if len(raw) < lf * 4 or lf != 6 + lh + count + nw + nh + nd + ni + nl + nk + ne + np:
        raise ValueError('Invalid TFM sizes')
    chars = 4 * (6 + lh)
    program = chars + 4 * (count + nw + nh + nd + ni)
    kerns = program + 4 * nl
    result = {}
    for char in range(bc, ec + 1):
        info = raw[chars + 4 * (char - bc):chars + 4 * (char - bc + 1)]
        if not info[0] or info[2] % 4 != 1:
            continue
        at = info[3]
        if at >= nl:
            raise ValueError('Invalid TFM program')
        skip, nxt, op, rem = raw[program + 4 * at:program + 4 * at + 4]
        if skip > 128:
            at = 256 * op + rem
        seen = set()
        while at < nl:
            skip, nxt, op, rem = raw[program + 4 * at:program + 4 * at + 4]
            if skip <= 128 and nxt not in seen:
                seen.add(nxt)
                if op >= 128:
                    index = 256 * (op - 128) + rem
                    if index >= nk:
                        raise ValueError('Invalid TFM kern')
                    value = struct.unpack_from('>i', raw, kerns + 4 * index)[0] / 2**20
                    result.setdefault(char, {})[nxt] = value
            if skip >= 128:
                break
            at += skip + 1
    return result


def load_tex_tfm(path):
    font = TFM(path)
    font.kerning = tex_kerning(Path(path).read_bytes())
    return font
