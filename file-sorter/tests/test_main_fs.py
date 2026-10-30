"""Поведенческие тесты main() на реальной ФС (tmp_path). Без моков."""

import pytest

import sys

from sort_downloads import main

CASES = [
    ("photo.jpg", "image"),
    ("report.pdf", "document"),
    ("backup.zip", "archive"),
    ("movie.mp4", "video"),
    ("song.mp3", "music"),
    ("tool.exe", "program"),
    ("app_setup.exe", "installer"),
]

class TestMainSorting:
    """Счастливый путь: файлы на месте, перемещение происходит, код 0."""

    def test_sorts_preserves_content(self, tmp_path):
        # given: один файл, который должен уехать в image/
        (tmp_path / "photo.jpg").write_text("data")

        # when
        rc = main(["--path", str(tmp_path)])

        # then: код 0, файл уехал, в корне его нет, содержимое цело
        assert rc == 0
        assert (tmp_path / "image" / "photo.jpg").read_text() == "data"
        assert not (tmp_path / "photo.jpg").exists()

    @pytest.mark.parametrize("name, category", CASES)
    def test_sorts_multiple(self, name, category, tmp_path):
        # по одному представителю в каждую непустую категорию

        (tmp_path / name).write_text(name)

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / category / name).read_text() == name
        assert not (tmp_path / name).exists()

    def test_creates_category_dirs_on_first_run(self, tmp_path, all_categories):
        # даже для одного файла main создаёт все категории - это контракт setup_dir
        (tmp_path / "photo.jpg").write_text("x")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        for category in all_categories:
            assert (tmp_path / category).is_dir(), category

    def test_sorts_uppercase_ext(self, tmp_path):
        # регистр расширения не должен мешать
        (tmp_path / "PHOTO.JPG").write_text("x")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / "image" / "PHOTO.JPG").exists()
        assert not (tmp_path / "PHOTO.JPG").exists()

    def test_idempotent_second_run(self, tmp_path):
        # повторный запуск по уже отсортированной папке тоже возвращает 0
        (tmp_path / "photo.jpg").write_text("x")
        assert main(["--path", str(tmp_path)]) == 0

        assert main(["--path", str(tmp_path)]) == 0
        # файл не «переехал второй раз» и не исчез
        assert (tmp_path / "image" / "photo.jpg").exists()


class TestMainIgnores:
    """Файлы и каталоги, которые main не трогает. Код 0, состояние не меняется."""

    def test_ignores_subdirectories(self, tmp_path):
        # подпапки main не должен трогать (это не файлы)
        sub = tmp_path / "my_subdir"
        sub.mkdir()
        (sub / "inner.jpg").write_text("x")  # внутри - не важно, в корне нет

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert sub.is_dir()
        assert (sub / "inner.jpg").exists()
        # в image/ ничего не появилось
        assert not list((tmp_path / "image").iterdir())

    def test_ignores_unknown_suffix(self, tmp_path, all_categories):
        # .xyz нет ни в одном наборе → файл остаётся на месте, код 0
        (tmp_path / "data.xyz").write_text("x")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / "data.xyz").exists()
        # ни в одну из категорий он не попал
        for category in all_categories:
            assert not (tmp_path / category / "data.xyz").exists()

    def test_ignores_no_suffix(self, tmp_path):
        (tmp_path / "README").write_text("x")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / "README").exists()

    def test_ignores_dotfile(self, tmp_path):
        # .gitignore суффикса не имеет → не двигается
        (tmp_path / ".gitignore").write_text("x")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / ".gitignore").exists()

    def test_ignores_empty_dir(self, tmp_path, all_categories):
        # пустая папка → main создаёт только категории, код 0
        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        # ровно 7 категорий, ни одного лишнего файла
        entries = {p.name for p in tmp_path.iterdir()}
        assert entries == set(all_categories)
        for category in all_categories:
            assert not list((tmp_path / category).iterdir())

    def test_files_in_category_dirs_untouched(self, tmp_path):
        # main смотрит только верхний уровень path; файлы внутри категорий не двигаются
        (tmp_path / "image").mkdir()
        (tmp_path / "image" / "old.jpg").write_text("old")
        # плюс свежий файл в корне для контроля, что main реально работал
        (tmp_path / "new.jpg").write_text("new")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / "image" / "old.jpg").read_text() == "old"
        assert (tmp_path / "image" / "new.jpg").read_text() == "new"
        assert not (tmp_path / "new.jpg").exists()

    def test_sort_file_with_space(self, tmp_path):
        (tmp_path/"my photo.jpg").write_text("123")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert (tmp_path / "image" / "my photo.jpg").exists()
        assert not ((tmp_path / "my photo.jpg").exists())

    def test_sort_unicode_name(self, tmp_path):
        (tmp_path / "мое фото.jpg").write_text("123")

        rc = main(["--path", str(tmp_path)])

        assert rc == 0
        assert not (tmp_path / "мое фото.jpg").exists()
        assert (tmp_path / "image" / "мое фото.jpg").exists()

class TestMainSkips:
    """Конфликт с уже существующим файлом в целевой папке. Код 3, stderr-сообщение."""

    def test_skip_existing(self, tmp_path, capsys):
        # given: целевой файл уже лежит в image/, в корне - одноимённый
        (tmp_path / "image").mkdir()
        (tmp_path / "image" / "photo.jpg").write_text("OLD")
        (tmp_path / "photo.jpg").write_text("NEW")

        # when
        rc = main(["--path", str(tmp_path)])

        # then: код 3, в stderr есть имя и «уже существует»,
        # источник НЕ исчез (иначе данные бы потерялись)
        out, err = capsys.readouterr()
        assert rc == 3
        assert "photo.jpg" in err
        assert "уже существует" in err
        assert (tmp_path / "photo.jpg").exists()

    def test_skip_does_not_overwrite(self, tmp_path, capsys):
        # отдельный контракт: содержимое целевого файла не перезаписано источником.
        # Важно само по себе - если бы кто-то заменил skip на «перезаписать»,
        # тест test_skip_existing ещё может пройти (файл на месте), а этот - упадёт.
        (tmp_path / "image").mkdir()
        existing = tmp_path / "image" / "photo.jpg"
        existing.write_text("KEEP-ME")
        (tmp_path / "photo.jpg").write_text("INTRUDER")

        rc = main(["--path", str(tmp_path)])

        assert rc == 3
        assert existing.read_text() == "KEEP-ME"

    def test_skip_and_move_mix(self, tmp_path, capsys):
        # один файл скипнут, другой перемещён → приоритет кода 3 (не 0, не 1)
        (tmp_path / "image").mkdir()
        (tmp_path / "image" / "photo.jpg").write_text("OLD")
        (tmp_path / "photo.jpg").write_text("NEW")
        (tmp_path / "song.mp3").write_text("data")

        rc = main(["--path", str(tmp_path)])

        _, err = capsys.readouterr()
        assert rc == 3
        assert "photo.jpg" in err and "уже существует" in err
        # skip: источник остался на месте, цель не тронута
        assert (tmp_path / "photo.jpg").exists()
        assert (tmp_path / "image" / "photo.jpg").read_text() == "OLD"
        # move: файл уехал
        assert (tmp_path / "music" / "song.mp3").read_text() == "data"
        assert not (tmp_path / "song.mp3").exists()


class TestMainValidation:
    """Валидация входного пути. Без моков; monkeypatch только для sys.platform."""

    def test_nonexistent_path(self, tmp_path, capsys):
        # path не создаём - main должен отказать до setup_dir
        ghost = tmp_path / "nope"

        rc = main(["--path", str(ghost)])

        _, err = capsys.readouterr()
        assert rc == 1
        assert "не существует" in err

    def test_path_is_file(self, tmp_path, capsys):
        # передали путь к файлу вместо каталога
        f = tmp_path / "not_a_dir.txt"
        f.write_text("x")

        rc = main(["--path", str(f)])

        _, err = capsys.readouterr()
        assert rc == 1
        assert "не является папкой" in err
        # main не должен был ничего создавать рядом: в tmp_path только исходный файл
        assert {p.name for p in tmp_path.iterdir()} == {"not_a_dir.txt"}
        assert f.read_text() == "x"

    def test_no_path_on_non_windows(self, monkeypatch, capsys):
        # без --path на не-Windows main просит --path и выходит с 1.
        # monkeypatch - чтобы тест был переносимым (на Windows без него
        # код попытался бы читать реестр, это другой тест из фазы 3).
        monkeypatch.setattr(sys, "platform", "linux")

        rc = main([])

        _, err = capsys.readouterr()
        assert rc == 1
        assert "--path" in err