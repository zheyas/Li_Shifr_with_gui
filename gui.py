#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Криптосистема на основе универсальной обёртывающей алгебры Ли.
Графический интерфейс с простым управлением ключами.
Ключ - просто текстовая строка (пароль).
"""

import os
import sys
import time
import random
import string
import hashlib
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext

# Импорт модулей криптосистемы
from gf257 import GF257, GF0, GF1
from monom import Monom
from polynomial import Polynomial
from lie_algebra import RandomLieAlgebra
from multiplication import set_rules
from encoding import text_to_polynomial, polynomial_to_bytes, calculate_required_dim
from file_io import (
    save_algebra, load_algebra,
    save_key_binary, load_key_binary,
    save_ciphertext, load_ciphertext
)


def key_from_password(password, dim, num_terms=3, max_degree=2):
    """
    Генерирует полином-ключ из текстового пароля.
    Пароль может быть любой строкой, даже очень длинной.
    """
    # Используем SHA-256 для получения детерминированной последовательности
    hash_bytes = hashlib.sha256(password.encode('utf-8')).digest()

    # Создаём псевдослучайный генератор на основе хеша
    seed = int.from_bytes(hash_bytes[:4], 'big')
    random.seed(seed)

    terms = {}
    for i in range(num_terms):
        total_degree = random.randint(1, max_degree)
        exps = [0] * dim

        for _ in range(total_degree):
            idx = random.randint(0, dim - 1)
            exps[idx] += 1

        coeff_val = (int.from_bytes(hash_bytes[i * 2:(i * 2 + 2)], 'big') % 10) + 1
        coeff = GF257(coeff_val)

        mon = Monom(exps, dim)
        terms[mon] = coeff

    random.seed()
    return Polynomial(terms, dim)


def generate_random_password(length=32):
    """Генерирует случайный пароль заданной длины."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(random.choice(chars) for _ in range(length))


class CryptoApp:
    def __init__(self, root):
        self.root = root
        self.root.title("LieAlgebra Crypto (пост-квантовая криптосистема)")
        self.root.geometry("800x750")

        # Текущие объекты
        self.algebra = None
        self.key = None
        self.key_poly = None  # полином-ключ
        self.current_text = None
        self.current_text_bytes = 0
        self.required_dim = 0
        self.text_selected = False
        self.text_file = None

        # Имена файлов (фиксированные)
        self.ALGEBRA_FILE = "algebra.json"
        self.KEY_FILE = "key.json"
        self.CIPHER_FILE = "cipher.json"

        # Ссылки на виджеты для дешифрования
        self.decrypt_key_entry = None
        self.decrypt_key_visible = False
        self.decrypt_key_poly = None
        self.decrypt_key_from_file = False

        # Создаем меню
        self.setup_menu()

        # Основной контейнер с вкладками
        self.notebook = ttk.Notebook(root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # Вкладка "Шифрование"
        self.encrypt_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.encrypt_frame, text="Шифрование")
        self.setup_encrypt_tab()

        # Вкладка "Алгебра"
        self.algebra_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.algebra_frame, text="Алгебра Ли")
        self.setup_algebra_tab()

        # Вкладка "Ключ"
        self.key_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.key_frame, text="Ключ")
        self.setup_key_tab()

        # Вкладка "Дешифрование"
        self.decrypt_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.decrypt_frame, text="Дешифрование")
        self.setup_decrypt_tab()

        # Вкладка "Лог"
        self.log_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.log_frame, text="Лог")
        self.setup_log_tab()

        # Вкладка "О программе"
        self.about_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.about_frame, text="О программе")
        self.setup_about_tab()

        # Приветственное сообщение
        self.log("Добро пожаловать в LieAlgebra Crypto!")
        self.log("Сначала выберите текст для шифрования, затем сгенерируйте алгебру и ключ.")

    def setup_menu(self):
        """Настройка меню приложения."""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # Меню "Файл"
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Файл", menu=file_menu)
        file_menu.add_command(label="Выход", command=self.root.quit)

        # Меню "Справка"
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Справка", menu=help_menu)
        help_menu.add_command(label="О программе", command=self.show_about_window)
        help_menu.add_command(label="Руководство", command=self.show_manual_window)

    def show_about_window(self):
        """Показывает отдельное окно с информацией о программе."""
        about_window = tk.Toplevel(self.root)
        about_window.title("О программе")
        about_window.geometry("600x500")

        about_text = scrolledtext.ScrolledText(about_window, wrap=tk.WORD, font=("Times New Roman", 11))
        about_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Загружаем содержимое README.md
        self.load_readme_content(about_text)
        about_text.config(state=tk.DISABLED)

        # Кнопка закрытия
        tk.Button(about_window, text="Закрыть", command=about_window.destroy).pack(pady=5)

    def show_manual_window(self):
        """Показывает отдельное окно с руководством пользователя."""
        manual_window = tk.Toplevel(self.root)
        manual_window.title("Руководство пользователя")
        manual_window.geometry("550x450")

        manual_text = scrolledtext.ScrolledText(manual_window, wrap=tk.WORD, font=("Times New Roman", 11))
        manual_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        manual_content = """КРАТКОЕ РУКОВОДСТВО ПОЛЬЗОВАТЕЛЯ
================================

1. ШИФРОВАНИЕ
   • Вкладка «Шифрование» → «Выбрать и анализировать» 
     (выберите текстовый файл для шифрования)
   • Вкладка «Алгебра Ли» → установите параметры (можно использовать 
     рекомендуемую размерность) → «Сгенерировать»
   • Вкладка «Ключ» → введите пароль или нажмите 
     «Сгенерировать случайный ключ»
   • Вкладка «Шифрование» → «Выполнить шифрование»

2. ДЕШИФРОВАНИЕ
   • Вкладка «Дешифрование» → выберите файлы алгебры (.json), 
     шифротекста (.json) и укажите выходной файл (.txt)
   • Введите тот же пароль, что использовался при шифровании, 
     или загрузите ключ из файла
   • «Выполнить дешифрование»

3. УПРАВЛЕНИЕ КЛЮЧАМИ
   • Ключ сохраняется в key.json (бинарный формат)
   • При генерации случайного ключа пароль показывается один раз
   • Для дешифрования можно загрузить key.json вместо ввода пароля

4. ФОРМАТЫ ФАЙЛОВ
   • algebra.json — параметры и структурные константы алгебры Ли
   • key.json — полином-ключ в base64
   • cipher.json — зашифрованное сообщение в base64

5. ПРИМЕЧАНИЯ
   • Размерность алгебры должна быть ≥ требуемой для текста
   • Остаток при делении должен быть нулевым для успешного дешифрования
   • При неверном пароле остаток будет ненулевым
"""

        manual_text.insert(tk.END, manual_content)
        manual_text.config(state=tk.DISABLED)

        # Кнопка закрытия
        tk.Button(manual_window, text="Закрыть", command=manual_window.destroy).pack(pady=5)

    def load_readme_content(self, text_widget):
        """Загружает содержимое README.md в текстовый виджет."""
        # Пытаемся найти README.md в разных местах
        readme_paths = ["README.md", "../README.md", "./README.md", "docs/README.md"]
        content = None

        for path in readme_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        content = f.read()
                    break
                except Exception:
                    continue

        if content:
            text_widget.insert(tk.END, content)
        else:
            # Встроенное содержимое на случай отсутствия файла
            text_widget.insert(tk.END, "LieAlgebra Crypto\n")
            text_widget.insert(tk.END, "=" * 50 + "\n\n")
            text_widget.insert(tk.END,
                               "Пост-квантовая криптосистема на основе универсальной обёртывающей алгебры Ли\n\n")
            text_widget.insert(tk.END, "Версия 1.0\n")
            text_widget.insert(tk.END, "© 2026 Все права защищены\n\n")
            text_widget.insert(tk.END, "ОПИСАНИЕ\n")
            text_widget.insert(tk.END, "Данная программа реализует симметричную криптосистему,\n")
            text_widget.insert(tk.END, "основанную на умножении полиномов в универсальной\n")
            text_widget.insert(tk.END, "обёртывающей алгебре нильпотентной алгебры Ли над полем GF(257).\n\n")
            text_widget.insert(tk.END, "КЛЮЧЕВЫЕ ОСОБЕННОСТИ\n")
            text_widget.insert(tk.END, "• Автоматический выбор размерности алгебры\n")
            text_widget.insert(tk.END, "• Текстовый ключ (парольная фраза)\n")
            text_widget.insert(tk.END, "• Сохранение компонентов в JSON-файлы\n")
            text_widget.insert(tk.END, "• Потенциальная устойчивость к квантовым атакам\n\n")
            text_widget.insert(tk.END, "ТЕОРЕТИЧЕСКАЯ ОСНОВА\n")
            text_widget.insert(tk.END, "• Алгебры Ли и нильпотентность\n")
            text_widget.insert(tk.END, "• Универсальная обёртывающая алгебра U(L)\n")
            text_widget.insert(tk.END, "• Теорема Пуанкаре–Биркгофа–Витта (PBW)\n")
            text_widget.insert(tk.END, "• Базисы Грёбнера–Ширшова\n")
            text_widget.insert(tk.END, "• Конечное поле GF(257)\n")

    # ---------- Вкладка "О программе" ----------
    def setup_about_tab(self):
        """Создает вкладку с информацией о программе."""
        frame = self.about_frame

        # Заголовок
        tk.Label(frame, text="О программе", font=("Arial", 16, "bold")).pack(pady=10)

        # Текстовая область с прокруткой для README
        self.about_text = scrolledtext.ScrolledText(frame, wrap=tk.WORD, font=("Times New Roman", 11))
        self.about_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Загружаем содержимое README.md
        self.load_readme_content(self.about_text)
        self.about_text.config(state=tk.DISABLED)

        # Кнопка обновления (перезагрузки README)
        refresh_btn = tk.Button(frame, text="Обновить", command=self.refresh_about_tab)
        refresh_btn.pack(pady=5)

    def refresh_about_tab(self):
        """Обновляет содержимое вкладки 'О программе'."""
        self.about_text.config(state=tk.NORMAL)
        self.about_text.delete(1.0, tk.END)
        self.load_readme_content(self.about_text)
        self.about_text.config(state=tk.DISABLED)
        self.log("Содержимое вкладки 'О программе' обновлено")

    def log(self, msg):
        """Добавляет сообщение в лог."""
        self.log_text.insert(tk.END, msg + "\n")
        self.log_text.see(tk.END)
        self.root.update()

    # ---------- Вкладка "Шифрование" ----------
    def setup_encrypt_tab(self):
        frame = self.encrypt_frame
        tk.Label(frame, text="Шифрование текстового файла", font=("Arial", 14)).pack(pady=5)

        # Выбор входного файла
        in_frame = tk.Frame(frame)
        in_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(in_frame, text="Входной файл (текст):").pack(side=tk.LEFT)
        self.encrypt_input_label = tk.Label(in_frame, text="не выбран", fg="red", width=30)
        self.encrypt_input_label.pack(side=tk.LEFT, padx=5)
        tk.Button(in_frame, text="Выбрать и анализировать",
                  command=self.select_and_analyze).pack(side=tk.LEFT, padx=5)
        tk.Button(in_frame, text="Очистить",
                  command=self.clear_encrypt_selection).pack(side=tk.LEFT, padx=5)

        # Информация о тексте
        info_frame = tk.LabelFrame(frame, text="Информация о тексте")
        info_frame.pack(fill=tk.X, padx=10, pady=5)

        self.text_info = tk.Label(info_frame, text="Текст не выбран", anchor=tk.W, justify=tk.LEFT)
        self.text_info.pack(fill=tk.X, padx=5, pady=5)

        # Статус готовности
        self.readiness_label = tk.Label(frame, text="", fg="red", font=("Arial", 10))
        self.readiness_label.pack(pady=5)

        # Кнопка шифрования
        self.encrypt_button = tk.Button(frame, text="Выполнить шифрование",
                                        command=self.do_encrypt,
                                        bg="lightblue", font=("Arial", 12),
                                        width=20, state=tk.DISABLED)
        self.encrypt_button.pack(pady=10)

        # Результат (очищается перед каждым шифрованием)
        self.encrypt_result = tk.Text(frame, height=8, state=tk.NORMAL)
        self.encrypt_result.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.encrypt_result.delete(1.0, tk.END)
        self.encrypt_result.config(state=tk.DISABLED)

        # Кнопка очистки результата
        clear_frame = tk.Frame(frame)
        clear_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Button(clear_frame, text="Очистить результат",
                  command=self.clear_encrypt_result).pack(side=tk.RIGHT)

    def clear_encrypt_result(self):
        """Очищает поле результата шифрования."""
        self.encrypt_result.config(state=tk.NORMAL)
        self.encrypt_result.delete(1.0, tk.END)
        self.encrypt_result.config(state=tk.DISABLED)
        self.log("Результат шифрования очищен")

    def clear_encrypt_selection(self):
        """Очищает выбор текстового файла."""
        self.current_text = None
        self.text_file = None
        self.text_selected = False
        self.encrypt_input_label.config(text="не выбран", fg="red")
        self.text_info.config(text="Текст не выбран")
        self.check_readiness()
        self.log("Выбор текста очищен")

    def select_and_analyze(self):
        """Выбирает файл и анализирует его размер."""
        fname = filedialog.askopenfilename(
            title="Выберите текстовый файл для шифрования",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if not fname:
            return

        try:
            with open(fname, "r", encoding="utf-8") as f:
                self.current_text = f.read()

            self.text_file = fname
            self.encrypt_input_label.config(text=os.path.basename(fname), fg="green")

            # Анализируем текст
            data_bytes = self.current_text.encode('utf-8')
            self.current_text_bytes = len(data_bytes)
            self.required_dim = calculate_required_dim(self.current_text_bytes)
            self.text_selected = True

            # Отображаем информацию
            info = f"Файл: {os.path.basename(fname)}\n"
            info += f"Размер: {self.current_text_bytes} байт\n"
            info += f"Требуемая размерность алгебры: {self.required_dim}\n\n"

            self.text_info.config(text=info)
            self.log(f"Выбран файл {fname}, требуется размерность {self.required_dim}")

            # Обновляем рекомендуемую размерность на вкладке алгебры
            if hasattr(self, 'rec_dim_label'):
                self.rec_dim_label.config(text=str(self.required_dim))

            # Проверяем готовность к шифрованию
            self.check_readiness()

        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось прочитать файл: {e}")

    def check_readiness(self):
        """Проверяет, всё ли готово для шифрования."""
        if not self.text_selected:
            self.readiness_label.config(text="✗ Сначала выберите текст", fg="red")
            self.encrypt_button.config(state=tk.DISABLED)
            return

        if self.algebra is None:
            self.readiness_label.config(text="✗ Требуется алгебра", fg="red")
            self.encrypt_button.config(state=tk.DISABLED)
            return

        if self.key_poly is None:
            self.readiness_label.config(text="✗ Требуется ключ", fg="red")
            self.encrypt_button.config(state=tk.DISABLED)
            return

        if self.algebra.dim < self.required_dim:
            self.readiness_label.config(text=f"✗ Алгебра слишком мала (dim={self.algebra.dim} < {self.required_dim})",
                                        fg="red")
            self.encrypt_button.config(state=tk.DISABLED)
            return

        self.readiness_label.config(text="✓ Всё готово к шифрованию", fg="green")
        self.encrypt_button.config(state=tk.NORMAL)

    # ---------- Вкладка "Алгебра" ----------
    def setup_algebra_tab(self):
        frame = self.algebra_frame

        tk.Label(frame, text="Управление алгеброй Ли", font=("Arial", 14)).pack(pady=5)

        # Рекомендуемая размерность
        rec_frame = tk.Frame(frame)
        rec_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(rec_frame, text="Рекомендуемая размерность:").pack(side=tk.LEFT)
        self.rec_dim_label = tk.Label(rec_frame, text="—", fg="blue", font=("Arial", 11, "bold"))
        self.rec_dim_label.pack(side=tk.LEFT, padx=5)

        # Параметры генерации
        param_frame = tk.LabelFrame(frame, text="Параметры новой алгебры")
        param_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(param_frame, text="Размерность (dim):").grid(row=0, column=0, sticky=tk.W, padx=5)
        self.dim_var = tk.IntVar(value=5)
        dim_entry = tk.Entry(param_frame, textvariable=self.dim_var, width=5)
        dim_entry.grid(row=0, column=1, padx=5)

        tk.Label(param_frame, text="Ступень (step):").grid(row=1, column=0, sticky=tk.W, padx=5)
        self.step_var = tk.IntVar(value=6)
        tk.Entry(param_frame, textvariable=self.step_var, width=5).grid(row=1, column=1, padx=5)

        tk.Label(param_frame, text="Плотность:").grid(row=2, column=0, sticky=tk.W, padx=5)
        self.density_var = tk.DoubleVar(value=0.3)
        tk.Entry(param_frame, textvariable=self.density_var, width=5).grid(row=2, column=1, padx=5)

        # Кнопка "Использовать рекомендуемую"
        tk.Button(param_frame, text="Использовать рекомендуемую",
                  command=self.use_recommended_dim).grid(row=0, column=2, padx=10)

        # Кнопки управления
        btn_frame = tk.Frame(param_frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=5)

        self.gen_algebra_btn = tk.Button(btn_frame, text="Сгенерировать",
                                         command=self.generate_algebra)
        self.gen_algebra_btn.pack(side=tk.LEFT, padx=5)

        self.save_algebra_btn = tk.Button(btn_frame, text="Сохранить",
                                          command=self.save_algebra)
        self.save_algebra_btn.pack(side=tk.LEFT, padx=5)

        self.load_algebra_btn = tk.Button(btn_frame, text="Загрузить",
                                          command=self.load_algebra)
        self.load_algebra_btn.pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Очистить",
                  command=self.clear_algebra).pack(side=tk.LEFT, padx=5)

        # Статус
        self.algebra_status = tk.Label(frame, text="Алгебра не загружена", fg="red")
        self.algebra_status.pack(pady=5)

        # Информация о текущей алгебре
        info_frame = tk.LabelFrame(frame, text="Текущая алгебра")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.algebra_info = tk.Text(info_frame, height=8, state=tk.DISABLED)
        self.algebra_info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

    def clear_algebra(self):
        """Очищает текущую алгебру."""
        self.algebra = None
        self.algebra_status.config(text="Алгебра не загружена", fg="red")
        self.algebra_info.config(state=tk.NORMAL)
        self.algebra_info.delete(1.0, tk.END)
        self.algebra_info.config(state=tk.DISABLED)
        self.log("Алгебра очищена")
        self.check_readiness()

    def use_recommended_dim(self):
        """Устанавливает рекомендуемую размерность в поле ввода."""
        if self.required_dim > 0:
            self.dim_var.set(self.required_dim)
            self.log(f"Установлена рекомендуемая размерность {self.required_dim}")
        else:
            messagebox.showinfo("Информация", "Сначала выберите текст для шифрования")
            self.notebook.select(self.encrypt_frame)

    def generate_algebra(self):
        dim = self.dim_var.get()
        step = self.step_var.get()
        density = self.density_var.get()

        self.algebra = RandomLieAlgebra(dim, step, density)
        self.update_algebra_info()
        self.algebra_status.config(text=f"Алгебра сгенерирована (dim={dim})", fg="green")
        self.log(f"Сгенерирована новая алгебра: dim={dim}, step={step}, density={density}")

        # Проверяем готовность к шифрованию
        self.check_readiness()

    def save_algebra(self):
        if self.algebra is None:
            messagebox.showerror("Ошибка", "Нет алгебры для сохранения")
            return
        save_algebra(self.algebra, self.ALGEBRA_FILE)
        self.algebra_status.config(text=f"Сохранено в {self.ALGEBRA_FILE}", fg="blue")
        self.log(f"Алгебра сохранена в {self.ALGEBRA_FILE}")

    def load_algebra(self):
        if os.path.exists(self.ALGEBRA_FILE):
            self.algebra = load_algebra(self.ALGEBRA_FILE)
            self.update_algebra_info()
            self.algebra_status.config(text=f"Загружено из {self.ALGEBRA_FILE}", fg="green")
            self.log(f"Алгебра загружена из {self.ALGEBRA_FILE}")

            # Обновляем рекомендуемую размерность
            if hasattr(self, 'rec_dim_label') and self.required_dim > 0:
                self.rec_dim_label.config(text=str(self.required_dim))

            # Проверяем готовность к шифрованию
            self.check_readiness()
        else:
            messagebox.showerror("Ошибка", f"Файл {self.ALGEBRA_FILE} не найден")

    def update_algebra_info(self):
        if self.algebra is None:
            return
        info = f"Размерность: {self.algebra.dim}\n"
        info += f"Ступень: {self.algebra.step}\n"
        info += f"Плотность: {self.algebra.density}\n"
        nonzero = len([key for key in self.algebra.structure.keys() if key[0] < key[1]])
        total = self.algebra.dim * (self.algebra.dim - 1) // 2
        info += f"Ненулевых коммутаторов: {nonzero} из {total}\n"
        info += "Структурные константы:\n"
        for (i, j), terms in self.algebra.structure.items():
            if i < j:
                info += f"  [{i},{j}] = "
                for k, coeff in terms:
                    info += f"{coeff}*e{k} "
                info += "\n"
        self.algebra_info.config(state=tk.NORMAL)
        self.algebra_info.delete(1.0, tk.END)
        self.algebra_info.insert(1.0, info)
        self.algebra_info.config(state=tk.DISABLED)

        # Обновляем рекомендуемую размерность на вкладке алгебры
        if self.required_dim > 0:
            self.rec_dim_label.config(text=str(self.required_dim))
        else:
            self.rec_dim_label.config(text="—")

    # ---------- Вкладка "Ключ" ----------
    def setup_key_tab(self):
        frame = self.key_frame
        tk.Label(frame, text="Управление ключом", font=("Arial", 14)).pack(pady=5)

        # Поле для ввода ключа
        input_frame = tk.LabelFrame(frame, text="Введите ключ (любая текстовая строка)")
        input_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(input_frame, text="Ключ:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.key_var = tk.StringVar()
        self.key_entry = tk.Entry(input_frame, textvariable=self.key_var,
                                  width=50, show="*")
        self.key_entry.grid(row=0, column=1, padx=5, pady=5)

        # Кнопки для работы с ключом
        btn_frame = tk.Frame(input_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)

        tk.Button(btn_frame, text="Показать ключ",
                  command=self.toggle_key_visibility).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Сгенерировать случайный ключ",
                  command=self.generate_random_key).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Очистить поле",
                  command=self.clear_key_field).pack(side=tk.LEFT, padx=5)

        # Кнопки для работы с файлами
        file_frame = tk.LabelFrame(frame, text="Файловые операции")
        file_frame.pack(fill=tk.X, padx=10, pady=5)

        btn_file_frame = tk.Frame(file_frame)
        btn_file_frame.pack(pady=5)

        tk.Button(btn_file_frame, text="Сохранить ключ в файл",
                  command=self.save_key_to_file).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_file_frame, text="Загрузить ключ из файла",
                  command=self.load_key_from_file).pack(side=tk.LEFT, padx=5)

        # Статус
        self.key_status = tk.Label(frame, text="Ключ не задан", fg="red")
        self.key_status.pack(pady=5)

        # Информация о сгенерированном полиноме-ключе
        info_frame = tk.LabelFrame(frame, text="Сгенерированный полином-ключ (для информации)")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.key_info = tk.Text(info_frame, height=8, state=tk.DISABLED)
        self.key_info.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        self.key_visible = False

        # Привязываем событие изменения текста к автоматической установке ключа
        self.key_var.trace_add("write", self.on_key_changed)

    def clear_key_field(self):
        """Очищает поле ввода ключа и сбрасывает ключ."""
        self.key_var.set("")
        self.key_poly = None
        self.key = None
        self.key_status.config(text="Ключ не задан", fg="red")
        self.key_info.config(state=tk.NORMAL)
        self.key_info.delete(1.0, tk.END)
        self.key_info.config(state=tk.DISABLED)
        self.log("Поле ключа очищено")
        self.check_readiness()

    def on_key_changed(self, *args):
        """Автоматически устанавливает ключ при изменении текста."""
        if self.algebra is not None:
            key_str = self.key_var.get().strip()
            if key_str:
                self.set_key_from_string(key_str)
            else:
                self.key_poly = None
                self.key = None
                self.key_status.config(text="Ключ не задан", fg="red")
                self.key_info.config(state=tk.NORMAL)
                self.key_info.delete(1.0, tk.END)
                self.key_info.config(state=tk.DISABLED)
                self.check_readiness()

    def toggle_key_visibility(self):
        """Переключает видимость ключа в поле ввода."""
        self.key_visible = not self.key_visible
        show = "" if self.key_visible else "*"
        self.key_entry.config(show=show)

    def generate_random_key(self):
        """Генерирует случайный ключ (длинную строку)."""
        # Генерируем действительно длинный случайный ключ
        length = random.randint(40, 60)
        password = generate_random_password(length)
        self.key_var.set(password)
        self.log(f"Сгенерирован случайный ключ длиной {length} символов")
        # Ключ установится автоматически через on_key_changed

    def set_key_from_string(self, key_str):
        """Устанавливает ключ из строки и генерирует полином."""
        if self.algebra is None:
            return

        # Сохраняем ключ как строку
        self.key = key_str

        # Генерируем полином из ключа (фиксированные параметры)
        # Используем параметры, зависящие от размерности алгебры
        dim = self.algebra.dim
        if dim <= 5:
            num_terms, max_degree = 3, 2
        elif dim <= 8:
            num_terms, max_degree = 4, 2
        else:
            num_terms, max_degree = 5, 3

        self.key_poly = key_from_password(key_str, dim, num_terms, max_degree)

        self.update_key_info()
        self.key_status.config(
            text=f"✓ Ключ установлен (длина: {len(key_str)} символов, мономов: {len(self.key_poly)})", fg="green")
        self.log(f"Ключ установлен, сгенерирован полином с {len(self.key_poly)} мономами")

        # Проверяем готовность к шифрованию
        self.check_readiness()

    def save_key_to_file(self):
        """Сохраняет ключ в файл key.json."""
        if self.key_poly is None:
            messagebox.showerror("Ошибка", "Нет ключа для сохранения")
            return
        save_key_binary(self.key_poly, self.KEY_FILE)
        self.key_status.config(text=f"✓ Ключ сохранён в {self.KEY_FILE}", fg="blue")
        self.log(f"Ключ сохранён в {self.KEY_FILE}")

    def load_key_from_file(self):
        """Загружает ключ из файла key.json."""
        if not os.path.exists(self.KEY_FILE):
            messagebox.showerror("Ошибка", f"Файл {self.KEY_FILE} не найден")
            return
        try:
            self.key_poly = load_key_binary(self.KEY_FILE)

            # Проверяем размерность
            if self.algebra and self.key_poly.dim != self.algebra.dim:
                messagebox.showwarning("Предупреждение",
                                       f"Размерность ключа ({self.key_poly.dim}) не совпадает с размерностью алгебры ({self.algebra.dim}).")

            # Не можем восстановить исходную строку, поэтому показываем, что ключ загружен
            self.key = "<ключ загружен из файла>"
            self.key_var.set(self.key)

            self.update_key_info()
            self.key_status.config(text=f"✓ Ключ загружен из {self.KEY_FILE} (мономов: {len(self.key_poly)})",
                                   fg="green")
            self.log(f"Ключ загружен из {self.KEY_FILE}")
            self.check_readiness()
        except Exception as e:
            messagebox.showerror("Ошибка", f"Не удалось загрузить ключ: {e}")

    def update_key_info(self):
        """Отображает информацию о текущем полиноме-ключе."""
        if self.key_poly is None:
            return
        info = f"Число мономов в полиноме: {len(self.key_poly)}\n"
        info += "Мономы (показатели, коэффициент):\n"
        for mon, coeff in self.key_poly._terms:
            info += f"  {mon.exps}  {coeff}\n"
        self.key_info.config(state=tk.NORMAL)
        self.key_info.delete(1.0, tk.END)
        self.key_info.insert(1.0, info)
        self.key_info.config(state=tk.DISABLED)

    # ---------- Шифрование ----------
    def do_encrypt(self):
        if not self.text_selected or self.current_text is None:
            messagebox.showerror("Ошибка", "Сначала выберите текст для шифрования")
            self.notebook.select(self.encrypt_frame)
            return

        if self.algebra is None:
            messagebox.showerror("Ошибка", "Нет алгебры (сгенерируйте или загрузите)")
            self.notebook.select(self.algebra_frame)
            return

        if self.key_poly is None:
            messagebox.showerror("Ошибка", "Нет ключа (введите или сгенерируйте ключ)")
            self.notebook.select(self.key_frame)
            return

        if self.algebra.dim < self.required_dim:
            messagebox.showerror("Ошибка",
                                 f"Размерность алгебры ({self.algebra.dim}) меньше требуемой ({self.required_dim})")
            self.notebook.select(self.algebra_frame)
            return

        try:
            # Устанавливаем правила редукции
            set_rules(self.algebra.get_reduction_rules())

            # Кодируем текст
            M = text_to_polynomial(self.current_text, self.algebra.dim)
            self.log(f"Полином сообщения содержит {len(M)} мономов")

            # Шифруем
            start = time.time()
            C = M * self.key_poly
            enc_time = time.time() - start
            self.log(f"Шифротекст содержит {len(C)} мономов, время {enc_time:.3f} с")

            # Сохраняем шифротекст
            save_ciphertext(C, self.CIPHER_FILE)
            self.log(f"Шифротекст сохранён в {self.CIPHER_FILE}")

            # Очищаем предыдущий результат и показываем новый
            self.encrypt_result.config(state=tk.NORMAL)
            self.encrypt_result.delete(1.0, tk.END)
            self.encrypt_result.insert(1.0,
                                       f"✓ Шифрование успешно!\n\n"
                                       f"Входной файл: {self.text_file}\n"
                                       f"Размер входных данных: {self.current_text_bytes} байт\n"
                                       f"Размерность алгебры: {self.algebra.dim}\n"
                                       f"Число мономов в M: {len(M)}\n"
                                       f"Число мономов в C: {len(C)}\n"
                                       f"Время шифрования: {enc_time:.3f} с\n"
                                       f"Шифротекст сохранён в: {self.CIPHER_FILE}")
            self.encrypt_result.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Ошибка", str(e))
            self.log(f"Ошибка шифрования: {e}")

    # ---------- Вкладка "Дешифрование" ----------
    def setup_decrypt_tab(self):
        frame = self.decrypt_frame
        tk.Label(frame, text="Дешифрование", font=("Arial", 14)).pack(pady=5)

        # Выбор файлов
        files_frame = tk.LabelFrame(frame, text="Выберите файлы")
        files_frame.pack(fill=tk.X, padx=10, pady=5)

        # Алгебра
        alg_frame = tk.Frame(files_frame)
        alg_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(alg_frame, text="Алгебра:", width=10).pack(side=tk.LEFT)
        self.decrypt_alg_label = tk.Label(alg_frame, text="не выбран", fg="red", width=40, anchor=tk.W)
        self.decrypt_alg_label.pack(side=tk.LEFT, padx=5)
        tk.Button(alg_frame, text="Выбрать", command=self.select_decrypt_alg).pack(side=tk.LEFT, padx=5)
        tk.Button(alg_frame, text="Очистить", command=self.clear_decrypt_alg).pack(side=tk.LEFT, padx=5)

        # Шифротекст
        ct_frame = tk.Frame(files_frame)
        ct_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(ct_frame, text="Шифротекст:", width=10).pack(side=tk.LEFT)
        self.decrypt_ct_label = tk.Label(ct_frame, text="не выбран", fg="red", width=40, anchor=tk.W)
        self.decrypt_ct_label.pack(side=tk.LEFT, padx=5)
        tk.Button(ct_frame, text="Выбрать", command=self.select_decrypt_ct).pack(side=tk.LEFT, padx=5)
        tk.Button(ct_frame, text="Очистить", command=self.clear_decrypt_ct).pack(side=tk.LEFT, padx=5)

        # Ключ (файл)
        key_file_frame = tk.Frame(files_frame)
        key_file_frame.pack(fill=tk.X, padx=5, pady=2)
        tk.Label(key_file_frame, text="Ключ (файл):", width=10).pack(side=tk.LEFT)
        self.decrypt_key_file_label = tk.Label(key_file_frame, text="не выбран", fg="red", width=40, anchor=tk.W)
        self.decrypt_key_file_label.pack(side=tk.LEFT, padx=5)
        tk.Button(key_file_frame, text="Выбрать", command=self.select_decrypt_key_file).pack(side=tk.LEFT, padx=5)
        tk.Button(key_file_frame, text="Очистить", command=self.clear_decrypt_key_file).pack(side=tk.LEFT, padx=5)

        # Разделитель
        ttk.Separator(frame, orient='horizontal').pack(fill=tk.X, padx=10, pady=10)

        # Или ввод ключа вручную
        key_frame = tk.LabelFrame(frame, text="Или введите ключ вручную")
        key_frame.pack(fill=tk.X, padx=10, pady=5)

        tk.Label(key_frame, text="Ключ:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.decrypt_key_var = tk.StringVar()
        self.decrypt_key_entry = tk.Entry(key_frame, textvariable=self.decrypt_key_var,
                                          width=50, show="*")
        self.decrypt_key_entry.grid(row=0, column=1, padx=5, pady=5)

        btn_frame = tk.Frame(key_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=5)

        tk.Button(btn_frame, text="Показать ключ",
                  command=self.toggle_decrypt_key_visibility).pack(side=tk.LEFT, padx=5)

        tk.Button(btn_frame, text="Очистить поле",
                  command=self.clear_decrypt_key_field).pack(side=tk.LEFT, padx=5)

        # Выходной файл
        out_frame = tk.Frame(frame)
        out_frame.pack(fill=tk.X, padx=10, pady=5)
        tk.Label(out_frame, text="Выходной файл (текст):").pack(side=tk.LEFT)
        self.decrypt_out_label = tk.Label(out_frame, text="не выбран", fg="red", width=30)
        self.decrypt_out_label.pack(side=tk.LEFT, padx=5)
        tk.Button(out_frame, text="Выбрать", command=self.select_decrypt_output).pack(side=tk.LEFT, padx=5)
        tk.Button(out_frame, text="Очистить", command=self.clear_decrypt_output).pack(side=tk.LEFT, padx=5)

        # Кнопка дешифрования
        self.decrypt_button = tk.Button(frame, text="Выполнить дешифрование",
                                        command=self.do_decrypt,
                                        bg="lightgreen", font=("Arial", 12),
                                        width=20, state=tk.DISABLED)
        self.decrypt_button.pack(pady=10)

        # Результат
        self.decrypt_result = tk.Text(frame, height=8, state=tk.NORMAL)
        self.decrypt_result.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        self.decrypt_result.delete(1.0, tk.END)
        self.decrypt_result.config(state=tk.DISABLED)

        # Кнопка очистки результата дешифрования
        clear_frame = tk.Frame(frame)
        clear_frame.pack(fill=tk.X, padx=10, pady=2)
        tk.Button(clear_frame, text="Очистить результат",
                  command=self.clear_decrypt_result).pack(side=tk.RIGHT)

        # Переменные для хранения выбранных файлов
        self.decrypt_alg_file = None
        self.decrypt_ct_file = None
        self.decrypt_key_file = None
        self.decrypt_key_poly = None
        self.decrypt_key_from_file = False
        self.decrypt_key_visible = False

        # Привязываем событие изменения текста к проверке готовности
        self.decrypt_key_var.trace_add("write", lambda *args: self.check_decrypt_readiness())

    def clear_decrypt_result(self):
        """Очищает поле результата дешифрования."""
        self.decrypt_result.config(state=tk.NORMAL)
        self.decrypt_result.delete(1.0, tk.END)
        self.decrypt_result.config(state=tk.DISABLED)
        self.log("Результат дешифрования очищен")

    def clear_decrypt_alg(self):
        """Очищает выбор файла алгебры."""
        self.decrypt_alg_file = None
        self.decrypt_alg_label.config(text="не выбран", fg="red")
        self.check_decrypt_readiness()
        self.log("Выбор файла алгебры очищен")

    def clear_decrypt_ct(self):
        """Очищает выбор файла шифротекста."""
        self.decrypt_ct_file = None
        self.decrypt_ct_label.config(text="не выбран", fg="red")
        self.check_decrypt_readiness()
        self.log("Выбор файла шифротекста очищен")

    def clear_decrypt_key_file(self):
        """Очищает выбор файла ключа."""
        self.decrypt_key_file = None
        self.decrypt_key_poly = None
        self.decrypt_key_from_file = False
        self.decrypt_key_file_label.config(text="не выбран", fg="red")
        self.check_decrypt_readiness()
        self.log("Выбор файла ключа очищен")

    def clear_decrypt_key_field(self):
        """Очищает поле ввода ключа."""
        self.decrypt_key_var.set("")
        self.check_decrypt_readiness()
        self.log("Поле ввода ключа очищено")

    def clear_decrypt_output(self):
        """Очищает выбор выходного файла."""
        if hasattr(self, 'decrypt_out_file'):
            delattr(self, 'decrypt_out_file')
        self.decrypt_out_label.config(text="не выбран", fg="red")
        self.check_decrypt_readiness()
        self.log("Выбор выходного файла очищен")

    def select_decrypt_alg(self):
        fname = filedialog.askopenfilename(
            title="Выберите файл алгебры",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if fname:
            self.decrypt_alg_file = fname
            self.decrypt_alg_label.config(text=os.path.basename(fname), fg="green")
            self.check_decrypt_readiness()

    def select_decrypt_ct(self):
        fname = filedialog.askopenfilename(
            title="Выберите файл шифротекста",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if fname:
            self.decrypt_ct_file = fname
            self.decrypt_ct_label.config(text=os.path.basename(fname), fg="green")
            self.check_decrypt_readiness()

    def select_decrypt_key_file(self):
        fname = filedialog.askopenfilename(
            title="Выберите файл ключа",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        if fname:
            self.decrypt_key_file = fname
            self.decrypt_key_file_label.config(text=os.path.basename(fname), fg="green")
            try:
                self.decrypt_key_poly = load_key_binary(fname)
                self.decrypt_key_from_file = True
                self.log(f"Ключ для дешифрования загружен из {fname}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить ключ: {e}")
                self.decrypt_key_poly = None
                self.decrypt_key_from_file = False
            self.check_decrypt_readiness()

    def toggle_decrypt_key_visibility(self):
        """Переключает видимость ключа в поле ввода."""
        self.decrypt_key_visible = not self.decrypt_key_visible
        show = "" if self.decrypt_key_visible else "*"
        if self.decrypt_key_entry:
            self.decrypt_key_entry.config(show=show)

    def select_decrypt_output(self):
        fname = filedialog.asksaveasfilename(
            title="Сохранить расшифрованный файл как",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if fname:
            self.decrypt_out_file = fname
            self.decrypt_out_label.config(text=os.path.basename(fname), fg="green")
            self.check_decrypt_readiness()

    def check_decrypt_readiness(self):
        """Проверяет, всё ли готово для дешифрования."""
        ready = True
        reasons = []

        if not hasattr(self, 'decrypt_out_file') or not self.decrypt_out_file:
            ready = False
            reasons.append("не выбран выходной файл")

        if not self.decrypt_alg_file:
            ready = False
            reasons.append("не выбрана алгебра")

        if not self.decrypt_ct_file:
            ready = False
            reasons.append("не выбран шифротекст")

        # Проверяем, есть ли ключ (строка или файл)
        key_str = self.decrypt_key_var.get().strip()
        if not key_str and not self.decrypt_key_poly:
            ready = False
            reasons.append("нет ключа")

        self.decrypt_button.config(state=tk.NORMAL if ready else tk.DISABLED)
        if ready:
            self.log("✓ Всё готово для дешифрования")

    def do_decrypt(self):
        # Проверяем наличие всех необходимых файлов
        if not self.decrypt_alg_file:
            messagebox.showerror("Ошибка", "Не выбрана алгебра")
            return

        if not self.decrypt_ct_file:
            messagebox.showerror("Ошибка", "Не выбран шифротекст")
            return

        if not hasattr(self, 'decrypt_out_file') or not self.decrypt_out_file:
            messagebox.showerror("Ошибка", "Не выбран выходной файл")
            return

        try:
            # Загружаем алгебру из файла
            alg = load_algebra(self.decrypt_alg_file)
            set_rules(alg.get_reduction_rules())
            self.log(f"✓ Алгебра загружена из {self.decrypt_alg_file} (dim={alg.dim})")

            # Загружаем шифротекст из файла
            C = load_ciphertext(self.decrypt_ct_file)
            self.log(f"✓ Шифротекст загружен из {self.decrypt_ct_file} (мономов: {len(C)})")

            # Получаем ключ-полином
            key_poly = None
            key_str = self.decrypt_key_var.get().strip()

            if key_str:
                # Генерируем полином из строки
                dim = alg.dim
                if dim <= 5:
                    num_terms, max_degree = 3, 2
                elif dim <= 8:
                    num_terms, max_degree = 4, 2
                else:
                    num_terms, max_degree = 5, 3
                key_poly = key_from_password(key_str, dim, num_terms, max_degree)
                self.log(f"✓ Ключ сгенерирован из введённой строки (мономов: {len(key_poly)})")
            elif self.decrypt_key_poly is not None:
                key_poly = self.decrypt_key_poly
                self.log(f"✓ Используется ключ, загруженный из файла (мономов: {len(key_poly)})")
            else:
                messagebox.showerror("Ошибка", "Нет ключа для дешифрования")
                return

            # Дешифрование
            self.log("🔄 Выполняется дешифрование...")
            start = time.time()
            q, r = C.reduce_full_fast(key_poly)
            dec_time = time.time() - start
            self.log(f"✓ Дешифрование выполнено за {dec_time:.3f} с")

            if not r.is_zero():
                self.log("⚠️ Внимание: остаток не нулевой! Возможно, неверный ключ.")
                messagebox.showwarning("Предупреждение",
                                       "Остаток при делении не нулевой! Возможно, неверный ключ.")
            else:
                self.log("✓ Остаток равен нулю - ключ верный")

            # Восстановление байтов
            recovered = polynomial_to_bytes(q, alg.dim)
            self.log(f"✓ Восстановлено {len(recovered)} байт")

            # Сохранение
            with open(self.decrypt_out_file, "wb") as f:
                f.write(recovered)
            self.log(f"✓ Результат сохранён в {self.decrypt_out_file}")

            # Попытка декодировать как UTF-8
            try:
                text = recovered.decode('utf-8')
                preview = text[:200] + ("..." if len(text) > 200 else "")
                is_text = True
            except UnicodeDecodeError:
                preview = "<бинарные данные>"
                is_text = False

            # Очищаем предыдущий результат и показываем новый
            self.decrypt_result.config(state=tk.NORMAL)
            self.decrypt_result.delete(1.0, tk.END)
            result_text = (
                f"✓ Дешифрование успешно!\n\n"
                f"Частное содержит {len(q)} мономов\n"
                f"Остаток: {'0' if r.is_zero() else 'ненулевой'}\n"
                f"Время: {dec_time:.3f} с\n"
                f"Выходной файл: {self.decrypt_out_file}\n"
                f"Размер: {len(recovered)} байт\n\n"
            )
            if is_text:
                result_text += f"Первые 200 символов:\n{preview}"
            else:
                result_text += "Содержимое: бинарные данные"

            self.decrypt_result.insert(1.0, result_text)
            self.decrypt_result.config(state=tk.DISABLED)

        except Exception as e:
            messagebox.showerror("Ошибка", f"Ошибка дешифрования: {str(e)}")
            self.log(f"❌ Ошибка дешифрования: {e}")

    # ---------- Вкладка "Лог" ----------
    def setup_log_tab(self):
        frame = self.log_frame
        self.log_text = scrolledtext.ScrolledText(frame, height=30)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        btn_frame = tk.Frame(frame)
        btn_frame.pack(pady=2)
        tk.Button(btn_frame, text="Очистить лог", command=self.clear_log).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Копировать лог", command=self.copy_log).pack(side=tk.LEFT, padx=5)

    def clear_log(self):
        self.log_text.delete(1.0, tk.END)

    def copy_log(self):
        """Копирует содержимое лога в буфер обмена."""
        log_content = self.log_text.get(1.0, tk.END)
        self.root.clipboard_clear()
        self.root.clipboard_append(log_content)
        self.log("✓ Лог скопирован в буфер обмена")


# ============================================================================
# Запуск приложения
# ============================================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = CryptoApp(root)
    root.mainloop()