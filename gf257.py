#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Конечное поле GF(257) для криптосистемы на основе алгебр Ли.
"""


class GF257:
    """Элемент конечного поля GF(257)."""

    def __init__(self, val):
        self.val = val % 257

    def __add__(self, other):
        return GF257(self.val + other.val)

    def __sub__(self, other):
        return GF257(self.val - other.val)

    def __mul__(self, other):
        return GF257(self.val * other.val)

    def __truediv__(self, other):
        return self * other.inv()

    def inv(self):
        """Обратный элемент по модулю 257 (малая теорема Ферма)."""
        return GF257(pow(self.val, 255, 257))

    def __eq__(self, other):
        return self.val == other.val

    def __ne__(self, other):
        return not self.__eq__(other)

    def __neg__(self):
        return GF257(-self.val)

    def __repr__(self):
        return str(self.val)

    def __int__(self):
        return self.val

    def __hash__(self):
        return hash(self.val)

    def __lt__(self, other):
        return self.val < other.val


GF0 = GF257(0)
GF1 = GF257(1)
