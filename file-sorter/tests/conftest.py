"""Общие фикстуры для тестов проекта."""

import pytest

from sort_downloads import CATEGORY_RULE


@pytest.fixture(scope="session")
def all_categories():
    """Уникальные категории в порядке CATEGORY_RULE.

    dict.fromkeys - дедупликация с сохранением порядка: сейчас дублей нет,
    но если кто-то добавит вторую "image" по ошибке - тесты на порядок
    не будут путаться между «одна и та же» и «две разные» категории.

    session scope - данные read-only, берутся из константы модуля;
    пересчитывать на каждый тест незачем.
    """
    return tuple(dict.fromkeys(category for _, category in CATEGORY_RULE))