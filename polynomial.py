#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Полиномы в универсальной обёртывающей алгебре Ли.
"""

import heapq
from gf257 import GF0, GF1
from monom import Monom


class Polynomial:
    """Полином в универсальной обёртывающей алгебре."""

    def __init__(self, terms=None, dim=6):
        """
        Args:
            terms: словарь {моном: коэффициент} или None
            dim: размерность алгебры Ли
        """
        self.dim = dim
        self._terms = []  # отсортированный список (monom, coeff)
        if terms:
            for mon, coeff in terms.items():
                if coeff != GF0:
                    m = mon if isinstance(mon, Monom) else Monom(mon, dim)
                    self._add_term(m, coeff)

    def _add_term(self, mon, coeff):
        """Добавляет член с бинарным поиском для поддержания сортировки."""
        if coeff == GF0:
            return

        lo, hi = 0, len(self._terms)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._terms[mid][0] == mon:
                new_coeff = self._terms[mid][1] + coeff
                if new_coeff == GF0:
                    self._terms.pop(mid)
                else:
                    self._terms[mid] = (mon, new_coeff)
                return
            elif self._terms[mid][0] < mon:
                lo = mid + 1
            else:
                hi = mid
        self._terms.insert(lo, (mon, coeff))

    def _remove_term(self, mon):
        """Удаляет член с заданным мономом."""
        lo, hi = 0, len(self._terms)
        while lo < hi:
            mid = (lo + hi) // 2
            if self._terms[mid][0] == mon:
                self._terms.pop(mid)
                return
            elif self._terms[mid][0] < mon:
                lo = mid + 1
            else:
                hi = mid

    def copy(self):
        """Создаёт копию полинома."""
        new = Polynomial(dim=self.dim)
        new._terms = self._terms.copy()
        return new

    def __len__(self):
        return len(self._terms)

    def is_zero(self):
        return len(self._terms) == 0

    def leading_term(self):
        """Возвращает ведущий член (моном, коэффициент)."""
        return self._terms[0] if self._terms else (None, GF0)

    def __add__(self, other):
        res = self.copy()
        for mon, coeff in other._terms:
            res._add_term(mon, coeff)
        return res

    def __sub__(self, other):
        return self + (-other)

    def __neg__(self):
        new = Polynomial(dim=self.dim)
        new._terms = [(mon, -coeff) for mon, coeff in self._terms]
        return new

    def __mul__(self, other):
        """Умножение полиномов с использованием глобальных правил."""
        if isinstance(other, (int, GF0.__class__)):
            new = Polynomial(dim=self.dim)
            for mon, coeff in self._terms:
                new._add_term(mon, coeff * other)
            return new

        # Импортируем здесь для избежания циклических импортов
        from multiplication import multiply_monoms

        res = Polynomial(dim=self.dim)
        for m1, c1 in self._terms:
            for m2, c2 in other._terms:
                prod = multiply_monoms(m1, m2, self.dim)
                for pm, pc in prod._terms:
                    res._add_term(pm, pc * c1 * c2)
        return res

    def reduce_full_fast(self, divisor):
        """
        Левое деление с остатком с использованием кучи.

        Returns:
            (quotient, remainder)
        """
        temp = self.copy()
        heap = []
        for i, (mon, coeff) in enumerate(temp._terms):
            heapq.heappush(heap, (i, mon, coeff))

        quotient = Polynomial(dim=self.dim)
        remainder = Polynomial(dim=self.dim)

        lead_div, coeff_div = divisor.leading_term()
        if lead_div is None:
            raise ValueError("Деление на нулевой полином")

        while heap and temp._terms:
            idx, lead_mon, lead_coeff = heapq.heappop(heap)
            if idx >= len(temp._terms) or temp._terms[idx][0] != lead_mon:
                continue

            if lead_mon.can_divide(lead_div):
                q_mon = lead_mon.div(lead_div)
                q_coeff = lead_coeff / coeff_div

                quotient._add_term(q_mon, q_coeff)

                q_poly = Polynomial({q_mon: q_coeff}, dim=self.dim)
                prod = q_poly * divisor
                for pm, pc in prod._terms:
                    temp._add_term(pm, -pc)

                # Перестраиваем кучу
                heap = []
                for i, (mon, coeff) in enumerate(temp._terms):
                    heapq.heappush(heap, (i, mon, coeff))
            else:
                remainder._add_term(lead_mon, lead_coeff)
                temp._remove_term(lead_mon)
                heap = []
                for i, (mon, coeff) in enumerate(temp._terms):
                    heapq.heappush(heap, (i, mon, coeff))

        return quotient, remainder

    def get_terms_list(self):
        """Возвращает список членов для сериализации."""
        terms_list = []
        for mon, coeff in self._terms:
            terms_list.append({
                "exponents": list(mon.exps),
                "coeff": int(coeff)
            })
        return terms_list

    @classmethod
    def from_terms_list(cls, terms_list, dim):
        """Восстанавливает полином из списка членов."""
        terms = {}
        for item in terms_list:
            exps = tuple(item["exponents"])
            coeff = GF257(item["coeff"])  # noqa: F821
            mon = Monom(exps, dim)
            terms[mon] = coeff
        return cls(terms, dim)
