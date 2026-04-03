#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сериализация полиномов в бинарный формат и base64.
"""

import struct
import base64
from monom import Monom
from polynomial import Polynomial
from gf257 import GF257, GF0, GF1

def polynomial_to_bytes(poly):
    """
    Сериализует полином в бинарный формат:
    - 4 байта: количество мономов (little-endian unsigned int)
    - для каждого монома:
        - dim * 4 байта: показатели (каждое как uint32)
        - 4 байта: коэффициент (int32)
    """
    data = bytearray()
    data.extend(struct.pack('<I', len(poly._terms)))

    for mon, coeff in poly._terms:
        for exp in mon.exps:
            data.extend(struct.pack('<I', exp))
        data.extend(struct.pack('<i', coeff.val))

    return bytes(data)


def bytes_to_polynomial(data, dim):
    """Восстанавливает полином из бинарных данных."""
    terms = {}
    offset = 0
    num_terms = struct.unpack('<I', data[offset:offset + 4])[0]
    offset += 4

    for _ in range(num_terms):
        exps = []
        for i in range(dim):
            exp = struct.unpack('<I', data[offset:offset + 4])[0]
            offset += 4
            exps.append(exp)

        coeff_val = struct.unpack('<i', data[offset:offset + 4])[0]
        offset += 4

        mon = Monom(exps, dim)
        terms[mon] = GF257(coeff_val)

    return Polynomial(terms, dim)


def polynomial_to_base64(poly):
    """Кодирует полином в base64."""
    return base64.b64encode(polynomial_to_bytes(poly)).decode('ascii')


def base64_to_polynomial(b64_str, dim):
    """Восстанавливает полином из base64."""
    data = base64.b64decode(b64_str)
    return bytes_to_polynomial(data, dim)
