#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Нильпотентные алгебры Ли для криптосистемы.
"""

import random
from gf257 import GF257, GF1, GF0


class RandomLieAlgebra:
    """Генератор случайной нильпотентной алгебры Ли."""

    def __init__(self, dim, step, density=0.3):
        """
        Args:
            dim: размерность алгебры
            step: ступень нильпотентности
            density: плотность ненулевых структурных констант (0..1)
        """
        self.dim = dim
        self.step = step
        self.density = density
        self.structure = {}  # (i,j) -> список (k, coeff)
        self._generate()

    def _generate(self):
        """Генерирует случайные структурные константы."""
        for i in range(self.dim):
            for j in range(i + 1, self.dim):
                terms = []
                max_k = min(j + self.step, self.dim)
                for k in range(j + 1, max_k):
                    if random.random() < self.density:
                        coeff = GF257(random.randint(1, 256))
                        terms.append((k, coeff))

                if terms:
                    self.structure[(i, j)] = terms
                    anti_terms = [(k, -coeff) for (k, coeff) in terms]
                    self.structure[(j, i)] = anti_terms

    def print_info(self):
        """Выводит информацию об алгебре."""
        print(f"\nАлгебра Ли размерности {self.dim}, ступень {self.step}")
        nonzero_pairs = len([key for key in self.structure.keys() if key[0] < key[1]])
        total_pairs = self.dim * (self.dim - 1) // 2
        print(f"Ненулевых коммутаторов: {nonzero_pairs} из {total_pairs}")

    def get_reduction_rules(self):
        """
        Строит правила редукции для универсальной обёртывающей.

        Для каждой пары (i,j) с i>j строится правило:
        x_i x_j → x_j x_i + Σ c_{ij}^k x_k
        """
        rules = {}
        for (i, j), terms in self.structure.items():
            if i > j:
                rule_terms = []
                # Член e_j e_i (перестановка)
                mon_swap = [0] * self.dim
                mon_swap[j] = 1
                mon_swap[i] = 1
                rule_terms.append((tuple(mon_swap), GF1))

                # Члены от структурных констант
                for k, coeff in terms:
                    mon_comm = [0] * self.dim
                    mon_comm[k] = 1
                    rule_terms.append((tuple(mon_comm), coeff))

                rules[(i, j)] = rule_terms
        return rules

    def get_structure_list(self):
        """Возвращает структурные константы для сериализации."""
        struct_list = []
        for (i, j), terms in self.structure.items():
            if i < j:  # только верхнетреугольные
                for k, coeff in terms:
                    struct_list.append({
                        "i": i,
                        "j": j,
                        "k": k,
                        "coeff": int(coeff)
                    })
        return struct_list

    @classmethod
    def from_structure_list(cls, struct_list, dim):
        """Восстанавливает алгебру из списка структурных констант."""
        lie = cls.__new__(cls)
        lie.dim = dim
        lie.step = 0  # не восстанавливается, можно сохранить отдельно
        lie.density = 0.0
        lie.structure = {}

        for item in struct_list:
            i, j, k = item["i"], item["j"], item["k"]
            coeff = GF257(item["coeff"])

            key = (i, j)
            if key not in lie.structure:
                lie.structure[key] = []
            lie.structure[key].append((k, coeff))

            anti_key = (j, i)
            if anti_key not in lie.structure:
                lie.structure[anti_key] = []
            lie.structure[anti_key].append((k, -coeff))

        return lie

