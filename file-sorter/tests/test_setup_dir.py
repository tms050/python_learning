"""Тесты setup_dir — без моков, только реальная ФС в tmp_path."""

import pytest

from sort_downloads import SetupDirError, setup_dir


class TestSetupDir:
    """Создание целевых каталогов и его ошибки."""

    def test_creates_all_category_dirs(self, tmp_path, all_categories):
        setup_dir(tmp_path)
        for category in all_categories:
            assert (tmp_path / category).is_dir(), category

    def test_idempotent(self, tmp_path, all_categories):
        setup_dir(tmp_path)
        setup_dir(tmp_path)  # второй вызов не должен падать
        for category in all_categories:
            assert (tmp_path / category).is_dir(), category

    def test_existing_dirs_ok(self, tmp_path, all_categories):
        # все папки уже есть и содержат файл — setup_dir не должен их трогать
        for category in all_categories:
            d = tmp_path / category
            d.mkdir()
            (d / "keep.txt").write_text(category)

        setup_dir(tmp_path)

        for category in all_categories:
            assert (tmp_path / category / "keep.txt").read_text() == category

    def test_file_blocks_category(self, tmp_path):
        # путь категории занят файлом → FileExistsError → SetupDirError с именем категории
        # ("image" — первая в CATEGORY_RULE; отдельно это фиксирует следующий тест)
        (tmp_path / "image").write_text("I am a file, not a dir")

        with pytest.raises(SetupDirError) as exc_info:
            setup_dir(tmp_path)

        msg = str(exc_info.value)
        assert "image" in msg
        # raise ... from exc сохраняет исходный FileExistsError как __cause__
        assert isinstance(exc_info.value.__cause__, FileExistsError)

    def test_file_blocks_first_category_stops_iteration(self, tmp_path, all_categories):
        # ФИКСИРУЕМ ПОРЯДОК: setup_dir идёт по CATEGORY_RULE, "image" — первый.
        # mkdir упал на первом же элементе → остальные категории не создаются.
        (tmp_path / "image").write_text("blocker")

        with pytest.raises(SetupDirError):
            setup_dir(tmp_path)

        assert (tmp_path / "image").is_file()
        for category in all_categories:
            if category == "image":
                continue
            assert not (tmp_path / category).exists(), (
                f"{category} не должен был создаться: setup_dir упал на первом же image"
            )

    def test_file_blocks_middle_category(self, tmp_path, all_categories):
        # Блокируем категорию В СЕРЕДИНЕ: до неё — создаётся, она — блокирует,
        # после — не создаётся. Покрывает оба края за один тест:
        #   - "first" покрывает "после" (ничего не создано),
        #   - "middle" покрывает "до" (часть создана) + "после" (часть нет).
        # Хардкодить конкретное имя не хочу: CATEGORY_RULE — источник правды,
        # и позиция "середины" должна вычисляться динамически.
        assert len(all_categories) >= 3, "нужно ≥3 категорий, чтобы 'середина' имела смысл"
        blocking_idx = len(all_categories) // 2
        blocking = all_categories[blocking_idx]
        (tmp_path / blocking).write_text("blocker")

        with pytest.raises(SetupDirError):
            setup_dir(tmp_path)

        for i, category in enumerate(all_categories):
            if i < blocking_idx:
                assert (tmp_path / category).is_dir(), (
                    f"{category} (до {blocking}) должен был создаться"
                )
            elif i == blocking_idx:
                assert (tmp_path / category).is_file(), (
                    f"{blocking} — блокирующий файл, не должен превратиться в папку"
                )
            else:
                assert not (tmp_path / category).exists(), (
                    f"{category} (после {blocking}) не должен был создаться: итерация упала"
                )