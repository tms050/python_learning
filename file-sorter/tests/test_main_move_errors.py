"""Тесты поведения main() при ошибках перемещения. С моками Path.rename."""

from pathlib import Path
from unittest.mock import Mock

from sort_downloads import main


class TestMainMoveErrors:
    """main() корректно обрабатывает PermissionError/OSError от Path.rename."""

    def test_permission_error_returns_1(self, tmp_path, monkeypatch, capsys):
        # given: один файл, rename которого "падает" с PermissionError
        (tmp_path / "photo.jpg").write_text("x")
        mock_rename = Mock(side_effect=PermissionError("denied"))
        monkeypatch.setattr(Path, "rename", mock_rename)

        rc = main(["--path", str(tmp_path)])

        _, err = capsys.readouterr()
        assert rc == 1
        assert "Нет прав" in err
        # контракт сообщения: пользователь должен видеть, какой файл не переместился
        assert "photo.jpg" in err
        mock_rename.assert_called_once()

    def test_os_error_returns_1(self, tmp_path, monkeypatch, capsys):
        # "диск переполнен" - типичный OSError, не подкласс PermissionError;
        # попадает в ветку `except OSError`, а не `except PermissionError`
        (tmp_path / "photo.jpg").write_text("x")
        mock_rename = Mock(side_effect=OSError("disk full"))
        monkeypatch.setattr(Path, "rename", mock_rename)

        rc = main(["--path", str(tmp_path)])

        _, err = capsys.readouterr()
        assert rc == 1
        assert "[OSError]" in err
        assert "disk full" in err
        # имя файла тоже должно быть в сообщении - тот же контракт, что и выше
        assert "photo.jpg" in err
        mock_rename.assert_called_once()

    def test_continues_after_error(self, tmp_path, monkeypatch, capsys):
        # Контракт: ошибка на одном файле НЕ прерывает обработку остальных.
        #
        # side_effect=[PermissionError, None] не подходит: None - "вернуть None",
        # а не "выполнить оригинальный rename". Поэтому сохраняем оригинал
        # и делегируем ему со второго вызова.

        (tmp_path / "photo.jpg").write_text("A")  # уйдёт в image/
        (tmp_path / "song.mp3").write_text("B")   # уйдёт в music/

        original_rename = Path.rename
        calls = {"n": 0}

        def fake_rename(self, target):
            calls["n"] += 1
            if calls["n"] == 1:
                raise PermissionError("denied")
            return original_rename(self, target)

        monkeypatch.setattr(Path, "rename", fake_rename)

        rc = main(["--path", str(tmp_path)])

        _, err = capsys.readouterr()

        assert rc == 1
        # оба файла дошли до rename - иначе "continues" не проверен
        assert calls["n"] == 2
        # ровно одно сообщение об ошибке - на один упавший файл
        assert err.count("Нет прав") == 1

        # Инварианты без привязки к порядку iterdir():
        moved_names = {p.name for p in (tmp_path / "image").iterdir()} | {
            p.name for p in (tmp_path / "music").iterdir()
        }
        remaining_names = {p.name for p in tmp_path.iterdir() if p.is_file()}

        # ровно один перемещён, ровно один остался - ни потерь, ни дублей
        assert len(moved_names) == 1
        assert len(remaining_names) == 1
        assert moved_names | remaining_names == {"photo.jpg", "song.mp3"}
        assert moved_names.isdisjoint(remaining_names)

        # маршрутизация: не попали в чужую категорию
        assert not (tmp_path / "image" / "song.mp3").exists()
        assert not (tmp_path / "music" / "photo.jpg").exists()

    def test_error_beats_skip(self, tmp_path, monkeypatch, capsys):
        # Приоритет кодов возврата: had_errors(1) > had_skips(3) > 0.
        # Если кто-то поменяет порядок в main() -
        #     if had_skips: return 3
        #     elif had_errors: return 1
        # - все остальные тесты зелёные, а контракт сломан. Этот - упадёт.

        # skip-сценарий: целевой файл уже существует -> main пропустит его,
        # до rename photo.jpg даже не дойдёт
        (tmp_path / "image").mkdir()
        (tmp_path / "image" / "photo.jpg").write_text("OLD")
        (tmp_path / "photo.jpg").write_text("NEW")

        # error-сценарий: rename для song.mp3 упадёт
        (tmp_path / "song.mp3").write_text("x")
        mock_rename = Mock(side_effect=PermissionError("denied"))
        monkeypatch.setattr(Path, "rename", mock_rename)

        rc = main(["--path", str(tmp_path)])

        _, err = capsys.readouterr()

        # главное: 1, а не 3
        assert rc == 1
        # оба типа сообщений есть - значит, оба сценария реально произошли
        assert "уже существует" in err
        assert "Нет прав" in err
        # rename вызван ровно один раз - только song.mp3;
        # photo.jpg отсечён на target_file.exists() и до rename не дошёл
        mock_rename.assert_called_once()
        # skip не перезаписал цель
        assert (tmp_path / "image" / "photo.jpg").read_text() == "OLD"