"""Тесты parse_args - чистый argparse, без ФС и без моков."""

import sys
from pathlib import Path

import pytest

from sort_downloads import parse_args


class TestParseArgs:
    """Контракт парсера: имя опции, тип, поведение при --help и ошибках."""

    # --- Успешные пути ---------------------------------------------------

    def test_no_args_path_is_none(self):
        # явный [] (а не sys.argv) - так тест не зависит от того, как pytest был запущен;
        ns = parse_args([])
        assert ns.path is None

    def test_path_arg(self):
        ns = parse_args(["--path", "foo"])
        assert ns.path == Path("foo")

    def test_path_is_pathlib(self):
        # type=Path в argparse - без него main сравнивал бы str с Path
        ns = parse_args(["--path", "foo"])
        assert isinstance(ns.path, Path)

    def test_path_with_spaces(self):
        # пробелы в пути - частая реальная ловушка; парсер не должен их резать
        ns = parse_args(["--path", "/tmp/my downloads"])
        assert ns.path == Path("/tmp/my downloads")

    def test_path_leading_slash(self):
        ns = parse_args(["--path", "/tmp/x"])
        assert ns.path == Path("/tmp/x")

    def test_equals_syntax(self):
        # argparse поддерживает --path=foo наравне с --path foo - фиксируем
        ns = parse_args(["--path=foo"])
        assert ns.path == Path("foo")

    def test_last_path_wins(self):
        # повторный --path перезаписывает предыдущий
        ns = parse_args(["--path", "a", "--path", "b"])
        assert ns.path == Path("b")

    def test_uses_sys_argv_when_argv_none(self, monkeypatch):
        # контракт: argv=None означает "читай sys.argv[1:]" - это то, что main() вызывает в проде
        monkeypatch.setattr(sys, "argv", ["prog", "--path", "foo"])
        ns = parse_args()
        assert ns.path == Path("foo")

    def test_empty_arg(self):
        ns = parse_args(["--path", ""])
        assert str(ns.path) == "." 

    # --- Ошибки и --help -------------------------------------------------

    def test_unknown_arg_exits_2(self, capsys):
        with pytest.raises(SystemExit) as exc:
            parse_args(["--nope"])
        assert exc.value.code == 2
        _, err = capsys.readouterr()
        # argparse печатает имя неизвестного аргумента в stderr
        assert "--nope" in err

    def test_missing_value_exits_2(self, capsys):
        # --path без значения: "expected one argument" -> SystemExit(2)
        with pytest.raises(SystemExit) as exc:
            parse_args(["--path"])
        assert exc.value.code == 2
        _, err = capsys.readouterr()
        assert "--path" in err

    def test_help_exits_0(self, capsys):
        # --help - не ошибка: код 0, вывод в stdout
        with pytest.raises(SystemExit) as exc:
            parse_args(["--help"])
        assert exc.value.code == 0
        out, err = capsys.readouterr()
        assert out  # что-то напечатано в stdout
        assert "--path" in out  # опция перечислена
        assert err == ""  # именно не в stderr

    def test_short_h_alias(self, capsys):
        # -h - стандартный алиас argparse для --help
        with pytest.raises(SystemExit) as exc:
            parse_args(["-h"])
        assert exc.value.code == 0
        out, _ = capsys.readouterr()
        assert "usage:" in out.lower()

