#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Криптосистема на основе универсальной обёртывающей алгебры Ли.
Модуль шифрования с автоматическим определением размерности.
"""

import sys
import random
import base64
import json
import struct
import time
import heapq
import math
from bisect import insort
from functools import total_ordering

sys.setrecursionlimit(1000000)


# ============================================================================
# 1. Конечное поле GF(257)
# ============================================================================

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


# ============================================================================
# 2. Нильпотентная алгебра Ли
# ============================================================================

class RandomLieAlgebra:
    """Генератор случайной нильпотентной алгебры Ли."""

    def __init__(self, dim, step, density=0.3):
        self.dim = dim
        self.step = step
        self.density = density
        self.structure = {}
        self._generate()

    def _generate(self):
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
        print(f"\nАлгебра Ли размерности {self.dim}, ступень {self.step}")
        nonzero_pairs = len([key for key in self.structure.keys() if key[0] < key[1]])
        total_pairs = self.dim * (self.dim - 1) // 2
        print(f"Ненулевых коммутаторов: {nonzero_pairs} из {total_pairs}")

    def get_reduction_rules(self):
        rules = {}
        for (i, j), terms in self.structure.items():
            if i > j:
                rule_terms = []
                mon_swap = [0] * self.dim
                mon_swap[j] = 1
                mon_swap[i] = 1
                rule_terms.append((tuple(mon_swap), GF1))

                for k, coeff in terms:
                    mon_comm = [0] * self.dim
                    mon_comm[k] = 1
                    rule_terms.append((tuple(mon_comm), coeff))

                rules[(i, j)] = rule_terms

        return rules

    def get_structure_list(self):
        struct_list = []
        for (i, j), terms in self.structure.items():
            if i < j:
                for k, coeff in terms:
                    struct_list.append({
                        "i": i,
                        "j": j,
                        "k": k,
                        "coeff": int(coeff)
                    })
        return struct_list


# ============================================================================
# 3. Мономы с правильным порядком
# ============================================================================

@total_ordering
class Monom:
    """Моном в универсальной обёртывающей алгебре."""

    def __init__(self, exps, dim):
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
        if sum(self.exps) != sum(other.exps):
            return sum(self.exps) > sum(other.exps)
        return self.exps > other.exps

    def total_degree(self):
        return sum(self.exps)

    def can_divide(self, other):
        return all(self.exps[i] >= other.exps[i] for i in range(self.dim))

    def div(self, other):
        return Monom([self.exps[i] - other.exps[i] for i in range(self.dim)], self.dim)


# ============================================================================
# 4. Нормализованные полиномы
# ============================================================================

class Polynomial:
    """Полином в универсальной обёртывающей алгебре."""

    def __init__(self, terms=None, dim=6):
        self.dim = dim
        self._terms = []
        if terms:
            for mon, coeff in terms.items():
                if coeff != GF0:
                    m = mon if isinstance(mon, Monom) else Monom(mon, dim)
                    self._add_term(m, coeff)

    def _add_term(self, mon, coeff):
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
        new = Polynomial(dim=self.dim)
        new._terms = self._terms.copy()
        return new

    def __len__(self):
        return len(self._terms)

    def is_zero(self):
        return len(self._terms) == 0

    def leading_term(self):
        if not self._terms:
            return None, GF0
        return self._terms[0]

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
        if isinstance(other, (int, GF257)):
            new = Polynomial(dim=self.dim)
            for mon, coeff in self._terms:
                new._add_term(mon, coeff * other)
            return new

        res = Polynomial(dim=self.dim)
        for m1, c1 in self._terms:
            for m2, c2 in other._terms:
                prod = multiply_monoms(m1, m2, self.dim)
                for pm, pc in prod._terms:
                    res._add_term(pm, pc * c1 * c2)

        return res

    def reduce_full_fast(self, divisor):
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
        terms_list = []
        for mon, coeff in self._terms:
            terms_list.append({
                "exponents": list(mon.exps),
                "coeff": int(coeff)
            })
        return terms_list

    @classmethod
    def from_terms_list(cls, terms_list, dim):
        terms = {}
        for item in terms_list:
            exps = tuple(item["exponents"])
            coeff = GF257(item["coeff"])
            mon = Monom(exps, dim)
            terms[mon] = coeff
        return cls(terms, dim)


# ============================================================================
# 5. Глобальные правила умножения
# ============================================================================

_reduction_rules = {}
_monom_mul_cache = {}


def set_rules(rules):
    global _reduction_rules
    _reduction_rules = rules
    _monom_mul_cache.clear()


def get_rule(i, j):
    return _reduction_rules.get((i, j)) if i > j else None


def multiply_monoms(m1, m2, dim):
    if m1.dim != m2.dim:
        raise ValueError("Размерности не совпадают")

    key = (m1.exps, m2.exps)
    if key in _monom_mul_cache:
        return _monom_mul_cache[key]

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
                new_list = vars_list[:idx] + [j, i] + vars_list[idx + 2:]
                return _sort_vars(new_list, dim, depth + 1)
            else:
                res = Polynomial(dim=dim)
                for mon_exps, coeff in rule:
                    rule_vars = []
                    for k, exp in enumerate(mon_exps):
                        rule_vars.extend([k] * exp)
                    new_list = vars_list[:idx] + rule_vars + vars_list[idx + 2:]
                    term = _sort_vars(new_list, dim, depth + 1)
                    res = res + (term * coeff)
                return res

    exps = [0] * dim
    for v in vars_list:
        exps[v] += 1
    return Polynomial({Monom(exps, dim): GF1}, dim)


def clear_caches():
    _monom_mul_cache.clear()


# ============================================================================
# 6. Сериализация полиномов
# ============================================================================

def polynomial_to_bytes(poly):
    data = bytearray()
    data.extend(struct.pack('<I', len(poly._terms)))

    for mon, coeff in poly._terms:
        for exp in mon.exps:
            data.extend(struct.pack('<I', exp))
        data.extend(struct.pack('<i', coeff.val))

    return bytes(data)


def bytes_to_polynomial(data, dim):
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


# ============================================================================
# 7. Автоматическое определение размерности
# ============================================================================

def calculate_required_dim(text_length):
    """
    Автоматически вычисляет необходимую размерность алгебры Ли.

    Аргументы:
        text_length (int): Длина текста в байтах

    Возвращает:
        int: Оптимальная размерность для кодирования
    """
    # Сколько бит нужно для кодирования позиции
    position_bits_needed = math.ceil(math.log2(text_length)) + 1  # +1 для надёжности

    # Минимальное количество переменных для позиции (по 4 бита на переменную)
    min_pos_vars = math.ceil(position_bits_needed / 4)

    # Добавляем 1 переменную для данных
    # Итого: data_vars (1) + pos_vars (min_pos_vars)
    # Но позиционные переменные идут в конце, поэтому общая размерность:
    # dim = data_vars + pos_vars
    data_vars = 1
    pos_vars = min_pos_vars

    # Минимальная размерность
    min_dim = data_vars + pos_vars

    # Добавляем запас прочности (+1 к размерности) для надёжности
    recommended_dim = min_dim + 1

    # Но не меньше 5 (минимальная рабочая размерность)
    recommended_dim = max(5, recommended_dim)

    print(f"\n[INFO] Анализ длины текста:")
    print(f"  Длина текста: {text_length} байт")
    print(f"  Требуется бит для позиции: {position_bits_needed}")
    print(f"  Минимальное число переменных для позиции: {pos_vars}")
    print(f"  Рекомендуемая размерность: {recommended_dim}")

    return recommended_dim


# ============================================================================
# 8. Кодирование текста в полином (с переменным числом позиционных переменных)
# ============================================================================

def text_to_polynomial(text, dim):
    """
    Преобразует текст в полином для шифрования.

    Автоматически определяет, сколько переменных использовать для позиции,
    исходя из размерности dim.

    Аргументы:
        text (str): Исходный текст
        dim (int): Размерность алгебры

    Возвращает:
        Polynomial: Полином, представляющий байты текста
    """
    data = text.encode('utf-8')
    poly = Polynomial(dim=dim)

    if dim < 4:
        raise ValueError(f"Размерность должна быть не меньше 4, получено {dim}")

    # Динамическое определение количества переменных для позиции
    # Используем максимально возможное число, но оставляем хотя бы 1 для данных
    max_pos_vars = dim - 1  # оставляем минимум 1 переменную для данных
    pos_vars_count = max_pos_vars

    # Переменные для позиции (последние pos_vars_count переменных)
    pos_vars = list(range(dim - pos_vars_count, dim))
    # Переменные для данных (остальные)
    data_vars = list(range(dim - pos_vars_count))

    bits_for_position = pos_vars_count * 4
    max_position = 2 ** bits_for_position - 1

    print(f"\n[DEBUG] Схема кодирования:")
    print(f"  dim={dim}")
    print(f"  Переменные для данных: {data_vars}")
    print(f"  Переменные для позиции: {pos_vars} ({pos_vars_count} переменных × 4 бита = {bits_for_position} бит)")
    print(f"  Максимальная позиция: {max_position}")
    print(f"  Длина данных: {len(data)} байт")

    if len(data) - 1 > max_position:
        print(f"  [WARNING] Текст слишком длинный! Нужно увеличить размерность.")
        print(f"  Максимальная длина: {max_position} байт")
        print(f"  Текущая длина: {len(data)} байт")

    for i, byte in enumerate(data):
        exps = [0] * dim

        # Кодируем байт в первую переменную данных
        if data_vars:
            exps[data_vars[0]] = byte

        # Кодируем позицию во все доступные переменные для позиции
        pos = i
        for idx in pos_vars:
            exps[idx] = pos & 15
            pos >>= 4

        mon = Monom(exps, dim)
        poly._add_term(mon, GF1)

        if i < 5:
            print(f"\n[DEBUG] Байт {i}: {byte} (0x{byte:02x})")
            print(f"  Показатели: {exps}")

    # Маркер конца
    marker_exps = [0] * dim
    pos = len(data)
    for idx in pos_vars:
        marker_exps[idx] = pos & 15
        pos >>= 4
    poly._add_term(Monom(marker_exps, dim), GF1)

    print(f"\n[DEBUG] Всего мономов в M: {len(poly)}")
    return poly


# ============================================================================
# 9. Генерация ключа
# ============================================================================

def random_key(dim=6, num_terms=3, max_coeff=10, max_degree=3, seed=42):
    """Генерирует случайный полином-ключ."""
    if seed is not None:
        random.seed(seed)

    terms = {}
    for _ in range(num_terms):
        total_degree = random.randint(1, max_degree)
        exps = [0] * dim
        for _ in range(total_degree):
            idx = random.randint(0, dim - 1)
            exps[idx] += 1

        while sum(exps) == 0:
            idx = random.randint(0, dim - 1)
            exps[idx] += 1

        coeff = GF257(random.randint(1, max_coeff))
        mon = Monom(exps, dim)
        terms[mon] = coeff

    return Polynomial(terms, dim)


# ============================================================================
# 10. Основная программа
# ============================================================================

def main():
    print("=" * 60)
    print("ШИФРОВАНИЕ (автоматическое определение размерности)")
    print("=" * 60)

    # Параметры, которые можно настраивать
    step = 6  # Ступень нильпотентности
    density = 0.3  # Плотность структурных констант
    filename = "text.txt"
    output_json = "encrypted.min.json"

    # Чтение текста для определения необходимой размерности
    try:
        with open(filename, "r", encoding="utf-8") as f:
            text = f.read()
        print(f"\n[0] Анализ текста из файла {filename}...")
        print(f"   Прочитано {len(text)} символов")

        # Определяем размерность автоматически
        data_bytes = text.encode('utf-8')
        dim = calculate_required_dim(len(data_bytes))
        print(f"   Выбрана размерность: {dim}")

    except FileNotFoundError:
        print(f"Файл {filename} не найден! Использую тестовый текст.")
        text = "Мело, мело по всей земле\nВо все пределы.\nСвеча горела на столе,\nСвеча горела."
        data_bytes = text.encode('utf-8')
        dim = calculate_required_dim(len(data_bytes))
        print(f"   Выбрана размерность: {dim}")

    print(f"\nПараметры: dim={dim}, step={step}, density={density}")

    # Шаг 1: Генерация алгебры Ли
    print("\n[1] Генерация алгебры Ли...")
    lie = RandomLieAlgebra(dim=dim, step=step, density=density)
    lie.print_info()
    struct_list = lie.get_structure_list()
    print(f"   Сохранено структурных констант: {len(struct_list)}")

    # Шаг 2: Построение правил редукции
    print("\n[2] Построение правил редукции...")
    rules = lie.get_reduction_rules()
    set_rules(rules)
    print(f"Построено {len(rules)} правил")

    # Шаг 3: Генерация ключа
    print("\n[3] Генерация ключа...")
    max_key_degree = max(1, dim // 3)
    key = random_key(dim=lie.dim, num_terms=3, max_coeff=10,
                     max_degree=max_key_degree, seed=42)
    key_terms = key.get_terms_list()
    print(f"Ключ K содержит {len(key)} мономов, макс. степень {max_key_degree}")

    # Шаг 4: Кодирование текста в полином
    print("\n[4] Кодирование текста в полином M...")
    try:
        M = text_to_polynomial(text, dim=lie.dim)
        print(f"  M: {len(M)} мономов")
    except ValueError as e:
        print(f"  Ошибка: {e}")
        return

    # Шаг 5: Шифрование
    print("\n[5] Шифрование...")
    start = time.time()
    C = M * key
    enc_time = time.time() - start
    print(f"  C: {len(C)} мономов, время: {enc_time:.3f} сек")

    # Шаг 6: Сериализация
    C_bytes = polynomial_to_bytes(C)
    C_b64 = base64.b64encode(C_bytes).decode('ascii')
    print(f"\n[6] Размер шифротекста: {len(C_bytes)} байт, base64: {len(C_b64)} символов")
    print(f"text: {text[:60]}...")

    # Шаг 7: Сохранение в JSON
    exchange_data = {
        "version": 4,  # Увеличили версию
        "dim": dim,
        "step": step,
        "density": density,
        "ciphertext": C_b64,
        "key": key_terms,
        "structure": struct_list
    }
    with open(output_json, "w", encoding="utf-8") as f:
        json.dump(exchange_data, f, ensure_ascii=False, indent=2)
    print(f"\n[7] Данные сохранены в {output_json}")

    print("\n✅ Шифрование завершено!")


if __name__ == "__main__":
    clear_caches()
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрограмма прервана пользователем")
        sys.exit(0)