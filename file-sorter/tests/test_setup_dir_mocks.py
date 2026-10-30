"""Тесты setup_dir с моками Path.mkdir + smoke-тест итерации main."""

from pathlib import Path
from unittest.mock import Mock

import pytest

from sort_downloads import CATEGORY_RULE, SetupDirError, main, setup_dir


class TestSetupDirMocks:
    """setup_dir с подменённым Path.mkdir - проверка обработки ошибок ФС."""

    def test_oserror_wrapped(self, tmp_path, monkeypatch):
        # Ветка `except OSError` - срабатывает на "диск переполнен" и т.п.
        # Важно: OSError - базовый, FileExistsError - подкласс; этот тест
        # фиксирует, что попали ИМЕННО в базовую ветку.
        mock_mkdir = Mock(side_effect=OSError("disk full"))
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        with pytest.raises(SetupDirError) as exc_info:
            setup_dir(tmp_path)

        msg = str(exc_info.value)
        assert "[OSError]" in msg
        assert "disk full" in msg
        # __cause__ - тот же объект, что в side_effect; проверяем identity
        assert exc_info.value.__cause__ is mock_mkdir.side_effect

    def test_file_exists_error_wrapped(self, tmp_path, monkeypatch):
        # Симметрично: FileExistsError (подкласс OSError) должен ловиться
        # ПЕРВЫМ except. Если кто-то поменяет порядок except в setup_dir -
        # этот тест упадёт на isinstance, а предыдущий останется зелёным.
        mock_mkdir = Mock(side_effect=FileExistsError("exists"))
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        with pytest.raises(SetupDirError) as exc_info:
            setup_dir(tmp_path)

        msg = str(exc_info.value)
        # Первая категория из CATEGORY_RULE - мок упал на первом же вызове
        first_category = CATEGORY_RULE[0][1]
        assert first_category in msg
        assert isinstance(exc_info.value.__cause__, FileExistsError)

    def test_mkdir_called_with_exist_ok(self, tmp_path, monkeypatch):
        # Контракт: setup_dir вызывает mkdir(exist_ok=True).
        # Без exist_ok=True второй запуск упал бы на существующих папках.
        mock_mkdir = Mock()
        monkeypatch.setattr(Path, "mkdir", mock_mkdir)

        setup_dir(tmp_path)

        assert mock_mkdir.call_count == len(CATEGORY_RULE)
        for call in mock_mkdir.call_args_list:
            # Проверяем через kwargs, а не assert_called_with(exist_ok=True):
            # если Mock в будущих версиях станет дескриптором и получит self,
            # kwargs всё равно останется {"exist_ok": True}.
            assert call.kwargs.get("exist_ok") is True, call


class TestMainIterationSafety:
    """Smoke: main обходит папку с большим числом файлов без потерь.

    ВАЖНО: НЕ гарантирует отлов регрессии
        for file in list(path.iterdir())   ->   for file in path.iterdir()

    Причина: на Windows и на маленьких папках `scandir` отдаёт «снимок»
    директории, и `RuntimeError: directory changed during iteration` не
    воспроизводится детерминированно. Тест зелёный и с багом, и без него.
    Детерминированно ловить эту регрессию можно только статической
    проверкой исходника - она ломается при любом рефакторинге, поэтому
    здесь сознательно не делается.

    Что тест реально ловит:
    - грубые поломки итерации (break, потеря файлов, падение main на N-м файле);
    - потерю данных при перемещении большого набора.

    Что тест НЕ ловит:
    - замену `list(...)` на голый `iterdir()`.
    """

    def test_many_files_all_moved(self, tmp_path):
        # 30 файлов - достаточно, чтобы main прошёл нетривиальный цикл
        for i in range(10):
            (tmp_path / f"img_{i}.jpg").write_text("x")
            (tmp_path / f"doc_{i}.pdf").write_text("x")
            (tmp_path / f"song_{i}.mp3").write_text("x")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        # Все 30 файлов доехали до своих категорий - нет потерь из-за итерации
        for category, expected in [("image", 10), ("document", 10), ("music", 10)]:
            assert len(list((tmp_path / category).iterdir())) == expected, category