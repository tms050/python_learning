"""Тесты download_path. winreg мокается через sys.modules - работает на любой ОС."""

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from sort_downloads import DownloadPathError, download_path


# GUID папки «Загрузки» - магическая константа. Если её перепутать,
# download_path() молча вернёт другую папку (например, «Документы»).
DOWNLOADS_GUID = "{374DE290-123F-4565-9164-39C4925E467B}"
SHELL_FOLDERS = r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders"


class TestDownloadPathMocks:
    """download_path() с фейковым winreg. Без реального реестра."""

    def _install_fake_winreg(
        self,
        monkeypatch,
        *,
        value=("C:\\Users\\test\\Downloads", 1),
        open_key_side_effect=None,
        open_key_return=None,
    ):
        """Положить MagicMock в sys.modules['winreg'] и вернуть его.

        Почему sys.modules, а не patch():
        - `import winreg` в download_path() - локальный, на Linux падает;
        - patch('winreg.OpenKey') требует, чтобы winreg уже импортировался.
        sys.modules работает и на Linux, и на Windows одинаково.
        """
        fake = MagicMock()
        fake.HKEY_CURRENT_USER = "HKCU"

        if open_key_side_effect is not None:
            fake.OpenKey.side_effect = open_key_side_effect
        if open_key_return is not None:
            # OpenKey используется в `with ... as reg_key` → нужен __enter__
            fake.OpenKey.return_value.__enter__.return_value = open_key_return

        fake.QueryValueEx.return_value = value
        monkeypatch.setitem(sys.modules, "winreg", fake)
        return fake

    def test_returns_path(self, monkeypatch):
        fake = self._install_fake_winreg(monkeypatch)

        result = download_path()

        # Path(строка) == Path(та же строка): безразлично к ОС,
        # на которой гоняются тесты (PosixPath vs WindowsPath).
        assert result == Path("C:\\Users\\test\\Downloads")
        assert isinstance(result, Path)

    def test_oserror_wrapped(self, monkeypatch):
        # OpenKey падает - download_path должен завернуть в DownloadPathError
        original = OSError("no key")
        self._install_fake_winreg(monkeypatch, open_key_side_effect=original)

        with pytest.raises(DownloadPathError) as exc_info:
            download_path()

        # `raise ... from exc` сохраняет ту же самую причину (identity)
        assert exc_info.value.__cause__ is original

    def test_query_value_exception_wrapped(self, monkeypatch):
        # Симметрично: падает QueryValueEx (ключ есть, значения нет) - тоже OSError.
        # Если кто-то вынесет QueryValueEx из try - этот тест упадёт, а предыдущий нет.
        fake = self._install_fake_winreg(monkeypatch)
        fake.QueryValueEx.side_effect = OSError("value not found")

        with pytest.raises(DownloadPathError):
            download_path()

    def test_uses_correct_registry_key_and_guid(self, monkeypatch):
        # GUID и путь ключа - контракт. Опечатка в GUID не падает,
        # а молча возвращает «не ту» папку. Фиксируем явно.
        mock_key = MagicMock()
        fake = self._install_fake_winreg(monkeypatch, open_key_return=mock_key)

        download_path()

        fake.OpenKey.assert_called_once_with("HKCU", SHELL_FOLDERS)
        fake.QueryValueEx.assert_called_once_with(mock_key, DOWNLOADS_GUID)


@pytest.mark.integration
class TestDownloadPathIntegration:
    """Реальный реестр. Только Windows, только по явному запросу."""

    @pytest.mark.skipif(sys.platform != "win32", reason="реестр Windows")
    def test_real_registry(self):
        path = download_path()
        assert isinstance(path, Path)
        assert path.exists()
        assert path.is_dir()