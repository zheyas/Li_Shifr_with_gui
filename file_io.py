#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Сохранение и загрузка алгебры, ключа и шифротекста в JSON.
Ключ сохраняется в том же формате, что и шифротекст (base64).
"""

import json
import base64
from gf257 import GF257, GF1, GF0
from polynomial import Polynomial
from lie_algebra import RandomLieAlgebra
from serialization import polynomial_to_bytes, bytes_to_polynomial


# ---------- Алгебра Ли ----------
def save_algebra(lie, filename):
    """Сохраняет алгебру Ли в JSON-файл."""
    data = {
        "dim": lie.dim,
        "step": lie.step,
        "density": lie.density,
        "structure": lie.get_structure_list()
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_algebra(filename):
    """Загружает алгебру Ли из JSON-файла."""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    lie = RandomLieAlgebra.from_structure_list(data["structure"], data["dim"])
    lie.step = data.get("step", 0)
    lie.density = data.get("density", 0.0)
    return lie


# ---------- Ключ (бинарный формат) ----------
def save_key_binary(key, filename):
    """Сохраняет ключ в JSON-файл в виде base64 от бинарной сериализации."""
    data = {
        "dim": key.dim,
        "key": base64.b64encode(polynomial_to_bytes(key)).decode('ascii')
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_key_binary(filename):
    """Загружает ключ из JSON-файла (base64 → бинарный → полином)."""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    key_bytes = base64.b64decode(data["key"])
    return bytes_to_polynomial(key_bytes, data["dim"])


# ---------- Шифротекст ----------
def save_ciphertext(cipher_poly, filename):
    """Сохраняет шифротекст в JSON-файл."""
    data = {
        "dim": cipher_poly.dim,
        "ciphertext": base64.b64encode(polynomial_to_bytes(cipher_poly)).decode('ascii')
    }
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def load_ciphertext(filename):
    """Загружает шифротекст из JSON-файла."""
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    ct_bytes = base64.b64decode(data["ciphertext"])
    return bytes_to_polynomial(ct_bytes, data["dim"])
