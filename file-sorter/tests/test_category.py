"""Тесты для get_category (чистая функция, без ФС и без моков)."""

import pytest

from sort_downloads import get_category

MIXED_CASES = [
    ("SeTuP.TxT", "document"),
    ("SetUp.EXe.tXt", "document"),
    # archive
    ("backup.zIP", "archive"),
    ("bacKUP.RAr", "archive"),
    # video
    ("movIE.mP4", "video"),
    ("MOVie.AVI", "video"),
    # music
    ("song.Mp3", "music"),
    ("sONg.WaV", "music"),
    # program
    ("tOOl.eXE", "program"),
    #installer
    ("SeTUP.eXe", "installer"),
    ("mySETup.eXE", "installer"),
    #None
    ("ReAdMe", None),
    ("setup.Bz", None),
]

SUFFIX_CASES = [
    # image
    ("photo.jpg", "image"),
    ("photo.jpeg", "image"),
    ("photo.png", "image"),
    ("anim.gif", "image"),
    # document
    ("report.pdf", "document"),
    ("doc.docx", "document"),
    ("notes.txt", "document"),
    ("setup.txt", "document"),
    ("setup.exe.txt", "document"),
    # archive
    ("backup.zip", "archive"),
    ("backup.rar", "archive"),
    # video
    ("movie.mp4", "video"),
    ("movie.avi", "video"),
    # music
    ("song.mp3", "music"),
    ("song.wav", "music"),
    # program
    ("tool.exe", "program"),
    #installer
    ("setup.exe", "installer"),
    ("mySetup.exe", "installer"),
    #None
    ("README", None),
    ("setup.bz", None),
    ("", None),
    (".jpg", None),
    ("archive.txt.gz", None),
    
    # Кирилица
    ("фото.jpg", "image"),
    ("сетап.exe", "program"),
    ("мойsetup.exe", "installer"),
    ("видео.ехе.mp4", "video"),
    ("фейк.ехе", None),

    #Space
    ("проверка про белов.exe", "program"),
    ("vi de o.mp4", "video"),
    ("s r.e x e", None)
]

class TestGetCategory:
    """Определение категории файла по имени."""

    @pytest.mark.parametrize("file_name, expected", SUFFIX_CASES)
    def test_all_suffixes(self, file_name, expected):
        """Каждый суффикс из констант -> своя категория."""
        assert get_category(file_name) == expected

    @pytest.mark.parametrize("file_name, expected", SUFFIX_CASES)
    def test_uppercase(self, file_name, expected):
        assert get_category(file_name.upper()) == expected

    @pytest.mark.parametrize("file_name, expected", MIXED_CASES)
    def test_mixed_case(self, file_name, expected):
        assert get_category(file_name) == expected