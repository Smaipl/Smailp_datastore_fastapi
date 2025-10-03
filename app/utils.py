import hashlib
import os
from typing import Optional

"""
Модуль utils: Вспомогательные утилиты приложения
Функции:
  - hash_token: Хэширование токенов для безопасного хранения
  - fix_plus_sign: Корректирует строки с ведущим пробелом вместо +
"""

TOKEN_PEPPER = os.getenv("TOKEN_PEPPER", "please-change-me")


def hash_token(token: str) -> str:
    """
    Хэширует токен с использованием SHA-256 и дополнительной 'соли' (PEPPER)

    Args:
        token: Исходный токен для хэширования

    Returns:
        Хэш токена в виде шестнадцатеричной строки
    """
    return hashlib.sha256((token + TOKEN_PEPPER).encode("utf-8")).hexdigest()


def fix_plus_sign(value: str) -> str:
    """
    Корректирует строку, заменяя ведущий пробел на плюс.
    Используется для обработки параметров запроса, где + может быть заменен на пробел.

    Args:
        value: Входная строка

    Returns:
        Скорректированная строка
    """
    if value.startswith(" "):
        return "+" + value[1:]
    return value
