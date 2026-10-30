"""Скрипт для сортировки файлов из папки загрузки или папки переданной как путь при вызове в набор катологов (создаются, если их нет)"""

# 1. Импорты
import argparse
import sys
from pathlib import Path
from collections.abc import Callable

# 2. Константы
IMAGE_SUFFIXES = frozenset({'.jpg', '.jpeg', '.png', '.gif'})
DOCUMENT_SUFFIXES = frozenset({'.pdf', '.docx', '.txt'})
ARCHIVE_SUFFIXES = frozenset({'.zip', '.rar'})
VIDEO_SUFFIXES = frozenset({'.mp4', '.avi'})
MUSIC_SUFFIXES = frozenset({'.mp3', '.wav'})
PROGRAM_SUFFIXES = frozenset({'.exe'})

# Правила определения категории файла. Функция сама приводит имя к нижнему регистру
CATEGORY_RULE: list[tuple[Callable[[str, str], bool], str]] = [
    (lambda name, suffix: suffix in IMAGE_SUFFIXES, "image"),
    (lambda name, suffix: suffix in DOCUMENT_SUFFIXES, "document"),
    (lambda name, suffix: suffix in ARCHIVE_SUFFIXES, "archive"),
    (lambda name, suffix: suffix in VIDEO_SUFFIXES, "video"),
    (lambda name, suffix: suffix in MUSIC_SUFFIXES, "music"),
    (lambda name, suffix: 'setup' in name and suffix in PROGRAM_SUFFIXES, "installer"),
    (lambda name, suffix: suffix in PROGRAM_SUFFIXES, "program"),
]

# 3. Вспомогательные функции
class SetupDirError(RuntimeError):
    """Не удалось подготовить целевые папки."""

class DownloadPathError(RuntimeError):
    """Не удалось получить путь до папки 'Загрузки'"""

def setup_dir(path: Path) -> None:
    for _, category in CATEGORY_RULE:
        target = path / category
        try:
            target.mkdir(exist_ok=True)
        except FileExistsError as exc:
            raise SetupDirError(
                f"Невозможно создать папку '{category}', так как в {path} содержится файл с таким именем"
            ) from exc
        except OSError as exc:
            raise SetupDirError(
                f"Не удалось создать папку '{category}': [{type(exc).__name__}] {exc}"
            ) from exc

def download_path() -> Path:
    """Функция получения пути до католога 'Загрузки', который выбирается для сортировки по умолчанию"""
    import winreg
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Explorer\Shell Folders") as reg_key:
            downloads_path = winreg.QueryValueEx(reg_key, "{374DE290-123F-4565-9164-39C4925E467B}")[0]
        path = Path(downloads_path)
    except OSError as exc:
        raise DownloadPathError(
            f"Не удалось получить путь до папки 'Загрузки': [{type(exc).__name__}] {exc}"
        ) from exc

    return path

def get_category(file_name: str) -> str | None:
    name = file_name.lower()
    suffix = Path(name).suffix

    for matches, category in CATEGORY_RULE:
        if matches(name, suffix): return category

    return None

# 4. Парсинг аргументов
def parse_args(argv=None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Сортирует файлы по каталогам в выбранной папке")

    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="путь к папке для сортировки (по умолчанию - стандартный путь)"
    )

    return parser.parse_args(argv)

# 5. Точка входа
def main(argv=None) -> int:
    """Return:
        0 - всё отсортировано
        1 - фатальная ошибка (неверный путь, не удалось создать папки, не удалось получить путь по умолчанию)
        3 - некоторые файлы пропущены (уже существуют в целевой папке)
    """

    args = parse_args(argv)
    
    if args.path is not None:
        path = args.path
    elif sys.platform == "win32":
        try:
            path = download_path()
        except DownloadPathError as exc:
            print(exc, file=sys.stderr)
            return 1
    else:
        print("укажите --path, автоопределение папки Загрузки доступно только на Windows", file=sys.stderr)
        return 1

    if not path.exists():
        print(f"{path} - не существует", file=sys.stderr)
        return 1
    elif not path.is_dir(): 
        print(f"{path} - переданный путь не является папкой", file=sys.stderr)
        return 1

    try:
        setup_dir(path)
    except SetupDirError as exc:
        print(exc, file=sys.stderr)
        return 1

    had_errors = False
    had_skips = False

    for file in list(path.iterdir()):

        if not file.is_file():
            continue 

        category = get_category(file.name)
        if category is None:
            continue
        
        target_dir = path / category
        target_file = target_dir / file.name

        if target_file.exists():
            print(f"{file.name} уже существует в {target_dir}", file=sys.stderr)
            had_skips = True
            continue

        try:
            file.rename(target_file)
        except PermissionError:
            print(f"Нет прав на перемещение {file.name} в {target_dir}", file=sys.stderr)
            had_errors = True
        except OSError as exc:
            print(f'Не удалось переместить {file.name} в {target_dir}: [{type(exc).__name__}] {exc}', file=sys.stderr)
            had_errors = True

    if had_errors:
        return 1
    elif had_skips:
        return 3

    return 0

if __name__ == "__main__":
    sys.exit(main())