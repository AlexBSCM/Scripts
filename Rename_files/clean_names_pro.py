#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
clean_names_pro.py — очистка имён файлов и папок

Функции:
- Удаление спецсимволов (с сохранением букв, цифр и дефиса)
- Замена #, @ → пробел
- Удаление стоп-слов (shorts, reels и др.)
- Удаление дубликатов слов (с сохранением порядка)
- Нормализация пробелов
- "YouTube-стиль" (первая буква заглавная)
- Ограничение длины имени (важно для Windows)
- Безопасное переименование (с обработкой конфликтов)
- Подробный лог (всегда на рабочем столе)

Использование:
    python clean_names_pro.py "D:\Folder"
    python clean_names_pro.py "D:\Folder" --dry-run
    python clean_names_pro.py "D:\Folder" --once
"""

import os
import sys
import unicodedata
import argparse
import logging
import time
from datetime import datetime

try:
    import regex as re
except ImportError:
    print("Ошибка: требуется пакет 'regex'. Установите: pip install regex")
    sys.exit(1)


# ==========================
# НАСТРОЙКИ
# ==========================

DEFAULT_DIRECTORIES = [
    r"D:\Multimedia\Video\4K Video Downloader+",
]

DEFAULT_INTERVAL = 120

STOP_WORDS = {
    "shorts", "reels", "tiktok", "viral",
    "fyp", "foryou", "foryoupage"
}


# ==========================
# ЛОГГЕР (НА РАБОЧИЙ СТОЛ)
# ==========================

def get_desktop_path():
    """Возвращает путь к рабочему столу."""
    return os.path.join(os.path.expanduser("~"), "Desktop")


def setup_logger():
    logger = logging.getLogger("cleaner")
    logger.setLevel(logging.DEBUG)

    # Очищаем старые обработчики
    logger.handlers.clear()

    # Консоль
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
    logger.addHandler(ch)

    # Файл (рабочий стол)
    desktop = get_desktop_path()
    log_file = os.path.join(
        desktop,
        f"clean_names_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
    )

    fh = logging.FileHandler(log_file, encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(
        "[%(asctime)s] %(levelname)s: %(message)s",
        "%Y-%m-%d %H:%M:%S"
    ))
    logger.addHandler(fh)

    logger.info(f"Лог файл: {log_file}")

    return logger


# ==========================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ==========================

def remove_duplicate_words(text: str) -> str:
    """Удаляет повторяющиеся слова, сохраняя порядок."""
    seen = set()
    result = []

    for word in text.split():
        key = word.lower()
        if key not in seen:
            seen.add(key)
            result.append(word)

    return " ".join(result)


def clean_name(name: str, max_length: int = 180) -> str:
    """Очистка имени."""

    name = unicodedata.normalize("NFC", name)

    # Удаление стоп-слов
    if STOP_WORDS:
        pattern = r'\b(' + "|".join(STOP_WORDS) + r')\b'
        name = re.sub(pattern, '', name, flags=re.IGNORECASE)

    # #, @ → пробел
    name = re.sub(r"[#@]+", " ", name)

    # Спецсимволы → пробел (сохраняем буквы, цифры, дефис)
    name = re.sub(r"[^\p{L}\p{N}\-]+", " ", name)

    # Пробелы
    name = re.sub(r"\s+", " ", name).strip()

    # Удаление дублей слов
    name = remove_duplicate_words(name)

    # Первая буква заглавная
    if name:
        name = name[0].upper() + name[1:]

    # Windows-safe
    name = name.rstrip(" .")

    # Ограничение длины
    if len(name) > max_length:
        name = name[:max_length].rstrip()

    return name or "unnamed"


def get_unique_path(path: str) -> str:
    """Добавляет _1, _2 при конфликте."""
    if not os.path.exists(path):
        return path

    base, ext = os.path.splitext(path)
    counter = 1

    while True:
        new_path = f"{base}_{counter}{ext}"
        if not os.path.exists(new_path):
            return new_path
        counter += 1


# ==========================
# ОСНОВНАЯ ЛОГИКА
# ==========================

def process_directory(directory: str, dry_run: bool, logger):
    files_count = 0
    dirs_count = 0
    errors = 0
    skipped = 0

    for root, dirs, files in os.walk(directory, topdown=False):

        # --- ФАЙЛЫ ---
        for file_name in files:
            old_path = os.path.join(root, file_name)

            try:
                base, ext = os.path.splitext(file_name)
                new_base = clean_name(base)
                new_name = new_base + ext

                # Нормализованное сравнение
                if unicodedata.normalize("NFC", new_name) == unicodedata.normalize("NFC", file_name):
                    logger.debug(f"SKIP (без изменений): {file_name}")
                    skipped += 1
                    continue

                new_path = os.path.join(root, new_name)
                new_path = get_unique_path(new_path)

                logger.info(f"Файл: {file_name} → {os.path.basename(new_path)}")

                if not dry_run:
                    os.rename(old_path, new_path)

                files_count += 1

            except Exception as e:
                logger.error(f"Ошибка файла '{file_name}': {e}")
                errors += 1

        # --- ПАПКИ ---
        for dir_name in dirs:
            old_path = os.path.join(root, dir_name)

            try:
                new_name = clean_name(dir_name)

                if unicodedata.normalize("NFC", new_name) == unicodedata.normalize("NFC", dir_name):
                    logger.debug(f"SKIP (папка без изменений): {dir_name}")
                    skipped += 1
                    continue

                new_path = os.path.join(root, new_name)
                new_path = get_unique_path(new_path)

                logger.info(f"Папка: {dir_name} → {os.path.basename(new_path)}")

                if not dry_run:
                    os.rename(old_path, new_path)

                dirs_count += 1

            except Exception as e:
                logger.error(f"Ошибка папки '{dir_name}': {e}")
                errors += 1

    return files_count, dirs_count, errors, skipped


def run(directories, dry_run, interval, once, logger):
    while True:
        total_f = total_d = total_e = total_s = 0

        logger.info("=== НАЧАЛО ===")

        for directory in directories:
            if not os.path.isdir(directory):
                logger.warning(f"Пропуск: {directory}")
                continue

            f, d, e, s = process_directory(directory, dry_run, logger)
            total_f += f
            total_d += d
            total_e += e
            total_s += s

        logger.info(f"ИТОГО: файлы={total_f}, папки={total_d}, ошибки={total_e}, пропущено={total_s}")
        logger.info("=== КОНЕЦ ===\n")

        if once or dry_run:
            break

        time.sleep(interval)


# ==========================
# CLI
# ==========================

def main():
    parser = argparse.ArgumentParser(description="Очистка имён файлов")
    parser.add_argument("dirs", nargs="*", help="Папки для обработки")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--once", action="store_true")
    parser.add_argument("--interval", type=int, default=DEFAULT_INTERVAL)

    args = parser.parse_args()

    directories = args.dirs if args.dirs else DEFAULT_DIRECTORIES

    logger = setup_logger()

    if args.dry_run:
        logger.info("DRY-RUN режим (без изменений)")

    try:
        run(directories, args.dry_run, args.interval, args.once, logger)
    except KeyboardInterrupt:
        logger.info("Остановлено пользователем")


if __name__ == "__main__":
    main()
input("Нажми Enter для выхода...")
