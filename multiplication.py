#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Глобальные правила умножения мономов с кэшированием.
"""

from monom import Monom
from polynomial import Polynomial
from gf257 import GF1, GF0

# Глобальные кэши
_reduction_rules = {}
_monom_mul_cache = {}


def set_rules(rules):
    """Устанавливает правила редукции."""
    global _reduction_rules
    _reduction_rules = rules
    _monom_mul_cache.clear()


def get_rule(i, j):
    """Возвращает правило для пары (i,j) если i>j."""
    return _reduction_rules.get((i, j)) if i > j else None


def multiply_monoms(m1, m2, dim):
    """Умножение двух мономов с кэшированием."""
    if m1.dim != m2.dim:
        raise ValueError("Размерности не совпадают")

    key = (m1.exps, m2.exps)
    if key in _monom_mul_cache:
        return _monom_mul_cache[key]

    # Преобразуем мономы в списки переменных
    vars1 = []
    for i, exp in enumerate(m1.exps):
        vars1.extend([i] * exp)
    vars2 = []
    for i, exp in enumerate(m2.exps):
        vars2.extend([i] * exp)
    vars_list = vars1 + vars2

    result = _sort_vars(vars_list, dim)
    _monom_mul_cache[key] = result
    return result


def _sort_vars(vars_list, dim, depth=0):
    """
    Приводит список переменных к упорядоченному виду с применением правил.

    Алгоритм:
    1. Если список длины ≤ 1, преобразуем в моном
    2. Ищем инверсию (i > j) в соседних элементах
    3. Если есть правило, применяем его
    4. Если нет правила, просто меняем местами
    """
    if len(vars_list) <= 1:
        exps = [0] * dim
        for v in vars_list:
            exps[v] += 1
        return Polynomial({Monom(exps, dim): GF1}, dim)

    for idx in range(len(vars_list) - 1):
        i, j = vars_list[idx], vars_list[idx + 1]
        if i > j:
            rule = get_rule(i, j)
            if rule is None:
                # Простая перестановка
                new_list = vars_list[:idx] + [j, i] + vars_list[idx + 2:]
                return _sort_vars(new_list, dim, depth + 1)
            else:
                # Применяем правило
                res = Polynomial(dim=dim)
                for mon_exps, coeff in rule:
                    rule_vars = []
                    for k, exp in enumerate(mon_exps):
                        rule_vars.extend([k] * exp)
                    new_list = vars_list[:idx] + rule_vars + vars_list[idx + 2:]
                    term = _sort_vars(new_list, dim, depth + 1)
                    res = res + (term * coeff)
                return res

    # Нет инверсий - список уже упорядочен
    exps = [0] * dim
    for v in vars_list:
        exps[v] += 1
    return Polynomial({Monom(exps, dim): GF1}, dim)


def clear_caches():
    """Очищает все кэши."""
    global _monom_mul_cache
    _monom_mul_cache.clear()
