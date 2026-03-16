import re
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
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def replace_block_comments(structured_text: str) -> str:
    def handle_block_comment(match: re.Match[str]) -> str:
        code, comment = match.groups()
        lines = "\n".join(f"// {line.strip()}" for line in comment.split("\n"))
        return f"{lines}\n{code}"

    return re.sub(
        r"^(.*?)\(\*(.*?)\*\)",
        handle_block_comment,
        structured_text,
        flags=re.MULTILINE,
    )


def shift_line_comments(structured_text: str) -> str:
    def handle_line_comment(match: re.Match[str]) -> str:
        code, comment = match.groups()
        return f"{comment}\n{code}"

    return re.sub(
        r"^([^\n]*?\S.*?)(//.*)",
        handle_line_comment,
        structured_text,
        flags=re.MULTILINE,
    )


def strip_extra_newlines(structured_text: str) -> str:
    return re.sub("\n(\\s*)\n", "\n\n", structured_text)


def clean_structured_text(structured_text: str) -> str:
    structured_text = replace_block_comments(structured_text)
    structured_text = shift_line_comments(structured_text)
    structured_text = strip_extra_newlines(structured_text)
    return structured_text
