from pathlib import Path
from typing import Iterable, Iterator, TypeVar

_T = TypeVar("_T")


def find_by_extension(extension: str, path: Path) -> Iterator[Path]:
    if path.is_dir():
        for child in path.iterdir():
            yield from find_by_extension(extension, child)
        return

    assert path.is_file()
    if path.name.endswith(extension):
        yield path


def expect_one(items: Iterable[_T]) -> _T | None:
    found = list(items)
    if len(found) != 1:
        return None
    (item,) = found
    return item


def convert_path(*, src_folder: Path, path: Path, dest_folder: Path) -> Path:
    assert src_folder.is_dir()
    return dest_folder / path.relative_to(src_folder)


def touch_file(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.touch()


def write_file(path: Path, content: str) -> None:
    touch_file(path)
    with open(path, "w") as f:
        f.write(content)
