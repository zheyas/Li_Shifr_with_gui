#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Мономы в универсальной обёртывающей алгебре Ли.
"""

from functools import total_ordering
from gf257 import GF0, GF1

@total_ordering
class Monom:
    """Моном в универсальной обёртывающей алгебре."""

    def __init__(self, exps, dim):
        """
        Args:
            exps: список показателей степени для каждой переменной
            dim: размерность алгебры Ли
        """
        self.exps = tuple(exps)
        self.dim = dim

    def __repr__(self):
        parts = [f"e{i + 1}^{self.exps[i]}" if self.exps[i] > 1 else f"e{i + 1}"
                 for i in range(self.dim) if self.exps[i] > 0]
        return '*'.join(parts) if parts else '1'

    def __eq__(self, other):
        return self.exps == other.exps

    def __hash__(self):
        return hash(self.exps)

    def __lt__(self, other):
        """Порядок: сначала по убыванию полной степени, затем лексикографически."""
        if sum(self.exps) != sum(other.exps):
            return sum(self.exps) > sum(other.exps)
        return self.exps > other.exps

    def total_degree(self):
        """Полная степень монома."""
        return sum(self.exps)

    def can_divide(self, other):
        """Проверяет, делится ли текущий моном на other (покомпонентно)."""
        return all(self.exps[i] >= other.exps[i] for i in range(self.dim))

    def div(self, other):
        """Деление монома на other (покомпонентное вычитание показателей)."""
        return Monom([self.exps[i] - other.exps[i] for i in range(self.dim)], self.dim)
