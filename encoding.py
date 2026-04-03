#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Кодирование текста в полином и обратно.
"""

import math
from monom import Monom
from polynomial import Polynomial
from gf257 import GF1, GF0


def calculate_required_dim(text_length):
    """
    Автоматически вычисляет необходимую размерность алгебры Ли.

    Args:
        text_length: длина текста в байтах

    Returns:
        int: оптимальная размерность
    """
    # Сколько бит нужно для кодирования позиции
    position_bits_needed = math.ceil(math.log2(text_length)) + 1

    # Минимальное количество переменных для позиции (по 4 бита на переменную)
    min_pos_vars = math.ceil(position_bits_needed / 4)

    # Добавляем 1 переменную для данных и запас прочности
    recommended_dim = min_pos_vars + 2

    return max(5, recommended_dim)


def text_to_polynomial(text, dim):
    """
    Преобразует текст в полином для шифрования.

    Схема кодирования:
    - Переменная x₀: значение байта (0-255)
    - Переменные x₁...x_{n-1}: позиция (по 4 бита на переменную)
    - Маркерный моном: длина данных в переменных позиции
    """
    data = text.encode('utf-8')
    poly = Polynomial(dim=dim)

    # Используем максимально возможное число переменных для позиции
    max_pos_vars = dim - 1
    pos_vars_count = max_pos_vars
    pos_vars = list(range(dim - pos_vars_count, dim))
    data_vars = list(range(dim - pos_vars_count))

    for i, byte in enumerate(data):
        exps = [0] * dim

        # Кодируем байт в первую переменную данных
        if data_vars:
            exps[data_vars[0]] = byte

        # Кодируем позицию
        pos = i
        for idx in pos_vars:
            exps[idx] = pos & 15
            pos >>= 4

        poly._add_term(Monom(exps, dim), GF1)

    # Маркер конца
    marker_exps = [0] * dim
    pos = len(data)
    for idx in pos_vars:
        marker_exps[idx] = pos & 15
        pos >>= 4
    poly._add_term(Monom(marker_exps, dim), GF1)

    return poly


def polynomial_to_bytes(poly, dim):
    """
    Восстанавливает сырые байты из полинома.

    Автоматически определяет, сколько переменных использовалось для позиции.
    """
    items = []

    # Определяем, сколько переменных использовалось для позиции
    max_possible_pos_vars = dim - 1

    # Пробуем различные варианты, начиная с максимального
    for pos_vars_count in range(max_possible_pos_vars, 0, -1):
        pos_vars = list(range(dim - pos_vars_count, dim))
        data_vars = list(range(dim - pos_vars_count))

        temp_items = []
        for mon, coeff in poly._terms:
            if coeff == GF0:  # noqa: F821
                continue

            # Восстанавливаем позицию
            pos = 0
            for i, idx in enumerate(pos_vars):
                pos |= (mon.exps[idx] << (4 * i))

            byte = mon.exps[data_vars[0]] if data_vars else 0
            byte = byte & 0xFF

            temp_items.append((pos, byte))

        temp_items.sort()
        if temp_items:
            max_pos = temp_items[-1][0]
            # Проверяем, что позиции в допустимом диапазоне
            if max_pos < 2 ** (pos_vars_count * 4):
                items = temp_items
                break
    else:
        # Если ничего не подошло, используем максимальное количество
        pos_vars = list(range(dim - max_possible_pos_vars, dim))
        data_vars = list(range(dim - max_possible_pos_vars))
        items = []
        for mon, coeff in poly._terms:
            if coeff == GF0:  # noqa: F821
                continue
            pos = 0
            for i, idx in enumerate(pos_vars):
                pos |= (mon.exps[idx] << (4 * i))
            byte = mon.exps[data_vars[0]] if data_vars else 0
            byte = byte & 0xFF
            items.append((pos, byte))
        items.sort()

    # Удаляем дубликаты (на случай ошибок)
    seen_positions = set()
    unique_items = []
    for pos, byte in items:
        if pos not in seen_positions:
            seen_positions.add(pos)
            unique_items.append((pos, byte))

    # Удаляем маркер конца (последняя позиция)
    if unique_items:
        unique_items = unique_items[:-1]

    bytes_list = [b for _, b in unique_items]
    return bytes(bytes_list)
