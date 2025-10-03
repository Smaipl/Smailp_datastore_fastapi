import hashlib

"""
Модуль utils: Вспомогательные утилиты приложения
Функции:
  - hash_token: Хэширование токенов для безопасного хранения
"""
import os

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
